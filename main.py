from pprint import pprint

# password hashing and gravatar url generation
import hashlib
def gravatar(email, size=200):
    return f"https://www.gravatar.com/avatar/{hashlib.md5(email.lower().encode('utf-8')).hexdigest()}?s={size}"
def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


# 2FA
import pyotp
import time

# Flask
from flask import Flask, request, g, make_response
from datetime import datetime
from uuid import uuid4

app = Flask(__name__)

ApplicationName = 'Toast'

def generate_session_id():
    return str(uuid4())

# Database
import sqlite3
# functions to get and close the database connection for each request
DATABASE = 'content/database.db'
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


# main page and server uptime
startTime = datetime.now()
@app.route('/')
def index():
    return f"Server running for {datetime.now() - startTime}"


#################### SIGNUP AND LOGIN ####################

@app.route('/signup', methods=['POST'])
def signup():
    cur = get_db()
    user = {
        'username': request.form['username'],
        'email': request.form['email'],
        'phone': request.form['phone'],
        'password': hash_password(request.form['password']),
        'gravitar': gravatar(request.form['email'])
    }
    pprint(user)
    response = make_response('Signed up successfully', 200)
    stop = False
    #check that username, email, and phone are unique
    if cur.cursor().execute('SELECT Username FROM logins WHERE Username = ?', (user['username'],)).fetchone() is not None:
        response = make_response('Username already taken', 409)
        stop = True
    if cur.cursor().execute('SELECT Email FROM logins WHERE Email = ?', (user['email'],)).fetchone() is not None:
        response = make_response('Email already taken', 409)
        stop = True
    if cur.cursor().execute('SELECT Phone FROM logins WHERE Phone = ?', (user['phone'],)).fetchone() is not None:
        response = make_response('Phone already taken', 409)
        stop = True
    if not stop:
        #add user to table users("UserID", "Username", "GravatarURL")
        cur.cursor().execute('INSERT INTO users (Username, GravatarURL) VALUES (?, ?)', (user['username'], user['gravitar']))
        #get the UserID of the user
        #UserID = cur.cursor().execute('SELECT UserID FROM users WHERE Username = ?', (user['username'],)).fetchone()[0]
        cur.cursor().execute('INSERT INTO logins (UserID, Username, Email, Phone, Password) VALUES ((SELECT UserID FROM users WHERE Username = ?), ?, ?, ?, ?)', (user['username'], user['username'], user['email'], user['phone'], user['password']))
        cur.commit()
    return response

@app.route('/login', methods=['POST'])
def login():
    #2FA: None=No 2FA, 0=2FA not checked, 1=2FA checked
    invalid = False
    cur = get_db()
    #check if hashed password matches the saved password for user
    password = cur.cursor().execute('SELECT password FROM logins WHERE Username = ?', (request.form['username'],))
    password = password.fetchone()[0]
    if password is None:
        invalid = True
    if password != hash_password(request.form['password']):
        invalid = True
    if invalid:
        return 'Invalid username or password', 401
    else:
        #create session, and add to sessions table
        session_id = generate_session_id()
        #check if user has 2FA enabled
        twoFA = cur.cursor().execute('SELECT TotpKey FROM logins WHERE Username = ?', (request.form['username'],)).fetchone()[0]
        if twoFA is None:
            #if not, create session and return
            cur.cursor().execute('INSERT INTO sessions (SessionKey, UserID, CreationTime) VALUES (?, (SELECT UserID FROM logins WHERE Username = ?), ?)', (session_id, request.form['username'], int(time.time())))
            cur.commit()
            response = make_response(f'"session_id":{session_id}, "message": "Logged in"', 200)
            response.set_cookie('session_id', session_id)
            return response
        else:
            #if so, create session and return
            cur.cursor().execute('INSERT INTO sessions (SessionKey, UserID, CreationTime, TwoFA) VALUES (?, (SELECT UserID FROM logins WHERE Username = ?), ?, 0)', (session_id, request.form['username'], time.time()))
            cur.commit()
            response = make_response(f'"session_id":{session_id}, "message": "Verify 2FA code at /2faVerify"', 200)
            response.set_cookie('session_id', session_id)
            return response


#################### 2FA ####################
@app.route('/2faEnable', methods=['POST'])
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
    #check if session exists
    cur = get_db()
    session = cur.cursor().execute('SELECT * FROM sessions WHERE SessionKey = ?', (request.cookies.get('session_id'),)).fetchone()
    if session is None:
        return 'Session does not exist', 401
    #check if 2FA is enabled
    twoFA = cur.cursor().execute('SELECT TotpKey FROM logins WHERE UserID = ?', (session[1],)).fetchone()[0]
    if twoFA is not None:
        return '2FA is already enabled', 401
    if request.form['step'] == '0':
        #check if login is valid
        password = cur.cursor().execute('SELECT password FROM logins WHERE UserID = ?', (session[1],)).fetchone()[0]
        if password != hash_password(request.form['password']):
            return 'Invalid password', 401
        #if so, return 2FA url
        key = pyotp.random_base32()
        totp = pyotp.TOTP(key)
        # use table Temp2FAKeys("UserID", "Key", "CreationTime")
        cur.cursor().execute('INSERT INTO Temp2FAKeys (UserID, Key, CreationTime) VALUES (?, ?, ?)', (session[1], key, time.time()))
        # get username from UserID
        username = cur.execute('SELECT Username FROM users WHERE UserID = ?', (session[1],)).fetchone()[0]
        cur.commit()
        return totp.provisioning_uri(f"{username}@{ApplicationName}", issuer_name=ApplicationName)
    elif request.form['step'] == '1':
        #check if 2FA code is correct
        key = cur.cursor().execute('SELECT Key FROM Temp2FAKeys WHERE UserID = ?', (session[1],)).fetchone()[0]
        if not pyotp.TOTP(key).verify(request.form['code']):
            return 'Invalid 2FA code, try again', 401
        #if so, update session and return
        cur.cursor().execute('UPDATE logins SET TotpKey = ? WHERE UserID = ?', (key, session[1]))
        cur.cursor().execute('DELETE FROM Temp2FAKeys WHERE UserID = ?', (session[1],))
        cur.commit()
        return '2FA enabled successfully', 200


@app.route('/2faVerify', methods=['POST'])
def twoFA():
    #check if session exists
    cur = get_db()
    session = cur.execute('SELECT * FROM sessions WHERE SessionKey = ?', (request.cookies.get('session_id'),)).fetchone()
    if session is None:
        return 'Session does not exist', 401
    #check if 2FA is enabled
    twoFA = cur.cursor().execute('SELECT TotpKey FROM logins WHERE UserID = ?', (session[1],)).fetchone()[0]
    if twoFA is None:
        return '2FA is not enabled', 401
    #check if 2FA code is correct
    if not pyotp.TOTP(twoFA).verify(request.form['code']):
        return 'Invalid 2FA code', 401
    #if so, update session and return
    cur.cursor().execute('UPDATE sessions SET "2FA" = 1 WHERE SessionKey = ?', (request.cookies.get('session_id'),))
    cur.commit()
    return '2FA verified successfully', 200



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=81)