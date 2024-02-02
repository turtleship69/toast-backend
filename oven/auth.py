import functools
import json

import pyotp
from flask import (Blueprint, Flask, flash, g, jsonify, make_response,
                   redirect, render_template, request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from .tools import generate_session_id, get_db, gravatar

#2FA: None=No 2FA, 0=2FA not checked, 1=2FA checked

bp = Blueprint('auth', __name__, url_prefix='/auth')


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        print("flag b")
        if g.user is None:
            response = {
                'status': 'error',
                'message': 'Invalid session'
            }
            return jsonify(response), 401
        if g.user[3] == 0:
            response = {
                'status': 'error',
                'message': '2FA not verified'
            }
            return jsonify(response), 401
        return view(**kwargs)
    return wrapped_view

@bp.before_app_request
def load_logged_in_user():
    g.db = get_db()
    session_id = request.form.get('session_id') if request.form.get('session_id') else request.cookies.get('session_id')
    if session_id is None:
        g.user = None
    else:
        g.session_id = session_id
        user = g.db.cursor().execute(
            'SELECT * FROM sessions WHERE SessionKey = ?', (session_id,)
        ).fetchone()
        if user is None:
            g.user = None
        else:
            g.user = user


@bp.route('/signup', methods=['POST'])
def signup():
    cur = get_db()
    user = {
        'username': request.form['username'],
        'email': request.form['email'],
        'password': generate_password_hash(request.form['password']),
        'gravitar': gravatar(request.form['email'])
    }
    session_id = generate_session_id()
    response = {'status': 'success',
        'message': 'Signed up successfully',
        'session_id': session_id}
    status = 201
    #make_response('Signed up successfully', 200)
    stop = False
    #check that username, email, and phone are unique
    if cur.cursor().execute('SELECT Username FROM users WHERE Username = ?', (user['username'],)).fetchone() is not None:
        response = {'status': 'error',
                    'message': 'Username already taken'}
        stop = True
        status = 409
    if cur.cursor().execute('SELECT Email FROM users WHERE Email = ?', (user['email'],)).fetchone() is not None:
        response = {'status': 'error',
                    'message': 'Email already taken'}
        stop = True
        status = 409
    if not stop:
        #add user to table "users" ("UserID", "Email", "Username", "Password", "TotpKey", "GravatarURL")
        passwordHash = generate_password_hash(user['password'])
        cur.cursor().execute('INSERT INTO users (Email, Username, Password, GravatarURL) VALUES (?, ?, ?, ?)', (user['email'], user['username'], passwordHash, user['gravitar']))
        cur.commit()
    json_response = json.dumps(response)
    flask_response = make_response(json_response, status)
    flask_response.set_cookie('session_id', session_id)
    return response

@bp.route('/login', methods=['POST'])
def login():
    invalid = False
    if request.form['username'] is None or request.form['password'] is None:
        invalid = "Invalid username or password"
        print('missing username or password')
    cur = get_db()
    #check if hashed password matches the saved password for user
    user = cur.cursor().execute('SELECT * FROM users WHERE Username = ?', (request.form['username'],)).fetchone()
    #table "users" ("UserID", "Email", "Username", "Password", "TotpKey", "GravatarURL")
    password = user[3]
    #if no user found, return invalid
    if user is None:
        invalid = True
        print('user not found')
    if not check_password_hash(password, request.form['password']):
        invalid = True
        print(user[0])
        print(password)
        print(request.form['password'])
    
    if invalid:
        response = make_response(json.dumps({
            'status': 'error',
            'message': "Invalid username or password"
        }), 401)
        return response
    else:
        #create session, and add to sessions table
        session_id = generate_session_id()
        #check if user has 2FA enabled
        TFA = user[4]
        if TFA is None:
            #if not, create session and return
            cur.cursor().execute('INSERT INTO sessions (SessionKey, UserID, CreationTime, 2FA) VALUES (?, (SELECT UserID FROM users WHERE Username = ?), datetime("now"), 1)', (session_id, request.form['username'], ))
            cur.commit()
            response = {
                'status': 'success',
                'message': 'Logged in',
                'session_id': session_id

            }            
            response = make_response(json.dumps(response), 200)
            response.set_cookie('session_id', session_id)
            return response
        else:
            #if so, create session and return
            cur.cursor().execute('INSERT INTO sessions (SessionKey, UserID, CreationTime, "2FA" ) VALUES (?, (SELECT UserID FROM logins WHERE Username = ?), datetime("now"), 0)', (session_id, request.form['username']))
            cur.commit()
            response = {
                'status': 'success',
                'message': f'Verify 2FA code at {url_for("auth.tfaVerify")}',
                'session_id': session_id
            }
            response = make_response(json.dumps(response), 200)
            response.set_cookie('session_id', session_id)
            return response 
        
@bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    #get session from cookies or if not in cookies, get from request body
    cur = get_db()
    cur.cursor().execute('DELETE FROM sessions WHERE SessionKey = ?', (g.session_id,))
    cur.commit()
    response = {
        'status': 'success',
        'message': 'Logged out'
    }
    response = make_response(json.dumps(response), 200)
    return response

@bp.route('/check', methods=['GET', 'POST'])
@login_required
def check():
    #check if session exists and if 2fa has been verified if 2fa is enabled
    # get session from cookies or if not in cookies, get from request body
    response = {
        'status': 'success',
        'message': 'Session Valid'
    }
    status = 200
    response = make_response(json.dumps(response), status)
    return response

@bp.route('/2faVerify', methods=['POST'])
def tfaVerify():
    """
    request object:
    {
        "session_id": {{ session_id }}, #if not in cookies
        "code": {{ code from 2fa app }}
    }
    response object if success:
    {
        "status": "success",
        "message": "2FA verified successfully"
    }
    response object if error:
    {
        "status": "error",
        "message": "Invalid 2FA code, try again" or "2FA is not enabled"
    }
    """
    error = None
    #check if session exists
    cur = get_db()
    session_id = g.session_id
    session = g.user
    if session is None:
        error = 'Invalid session'
    #check if 2FA is enabled
    twoFAKey = cur.cursor().execute('SELECT TotpKey FROM logins WHERE UserID = ?', (session[1],)).fetchone()[0]
    if twoFAKey is None:
        error = '2FA is not enabled'
    #check if 2FA code is correct
    if not pyotp.TOTP(twoFAKey).verify(request.form['code']):
        error = 'Invalid 2FA code, try again'
    #if so, update session and return
    cur.cursor().execute('UPDATE sessions SET "2FA" = 1 WHERE SessionKey = ?', (session_id,))
    cur.commit()
    if not error:
        response = {
            'status': 'success',
            'message': '2FA verified successfully'
        }
        status = 200
    else:
        response = {
            'status': 'error',
            'message': error
        }
        status = 401
    response = make_response(json.dumps(response), status)
    return response

@bp.route('/2faEnable', methods=['POST'])
@login_required
def twoFAEnable():
    """
    request object:
    {
        step: 0,
        session_id: {{ session_id }},
        password: {{ password }}
    }
    check login, if valid return 2fa url
    request object:
    {
        step: 1, 
        session_id: {{ session_id }},
        code: {{ code from 2fa app }}
    }
    return success
    """
    error = None
    #check if session exists
    session_id = g.session_id
    session = g.user
    if session_id is None or session is None:
        error = 'Invalid session'
    cur = get_db()
    #check if 2FA is enabled
    twoFA = cur.cursor().execute('SELECT TotpKey FROM logins WHERE UserID = ?', (session[1],)).fetchone()[0]
    if twoFA is not None:
        error = '2FA is already enabled'
    if request.form['step'] == '0':
        #check if login is valid
        password = cur.cursor().execute('SELECT password FROM logins WHERE UserID = ?', (session[1],)).fetchone()[0]
        if not check_password_hash(password, request.form['password']):
            error = 'Invalid password'
        #if so, return 2FA url
        if error:
            response = {
                'status': 'error',
                'message': error
            }
            status = 401
            return make_response(json.dumps(response), status)
        key = pyotp.random_base32()
        totp = pyotp.TOTP(key)
        # use table Temp2FAKeys("UserID", "Key", "CreationTime")
        cur.cursor().execute('INSERT INTO Temp2FAKeys (UserID, Key, CreationTime) VALUES (?, ?, datetime("now"))', (session[1], key))
        # get username from UserID
        username = cur.execute('SELECT Username FROM users WHERE UserID = ?', (session[1],)).fetchone()[0]
        cur.commit()
        totpurl = totp.provisioning_uri(f"{username}", issuer_name="Toasty")
        response = {
            'status': 'success',
            'message': "proceed to step 1",
            'url': totpurl
        }
        status = 200
        return make_response(json.dumps(response), status)
    elif request.form['step'] == '1':
        #check if 2FA code is correct
        key = cur.cursor().execute('SELECT Key FROM Temp2FAKeys WHERE UserID = ?', (session[1],)).fetchone()[0]
        if not pyotp.TOTP(key).verify(request.form['code']):
            error = 'Invalid 2FA code, try again'
        if error:
            response = {
                'status': 'error',
                'message': error
            }
            status = 401
            return make_response(json.dumps(response), status)
        #if so, update session and return
        cur.cursor().execute('UPDATE logins SET TotpKey = ? WHERE UserID = ?', (key, session[1]))
        cur.cursor().execute('DELETE FROM Temp2FAKeys WHERE UserID = ?', (session[1],))
        cur.commit()
        response = {
            'status': 'success',
            'message': '2FA enabled successfully'
        }
        status = 200
        return make_response(json.dumps(response), status)
    else:
        response = {
            'status': 'error',
            'message': 'Invalid step'
        }
        status = 400
        return make_response(json.dumps(response), status)