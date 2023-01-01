from pprint import pprint
from compressor import compress_image

# password hashing and gravatar url generation
import hashlib
def gravatar(email, size=200):
    return f"https://www.gravatar.com/avatar/{hashlib.md5(email.lower().encode('utf-8')).hexdigest()}?s={size}"
def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


# 2FA
import pyotp
import time

#UUIDs
from uuid import uuid4
def generate_session_id():
    return str(uuid4())


# Flask
from flask import Flask, request, g, make_response, jsonify
from datetime import datetime

app = Flask(__name__)

ApplicationName = 'Toast'


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


#################### DATABASE MANAGEMENT ####################


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
    if password is None:
        invalid = True
    password = password.fetchone()[0]
    if password != hash_password(request.form['password']):
        invalid = True
    if invalid:
        return jsonify({'status': 'error','message': 'Invalid username or password'}), 401
    else:
        #create session, and add to sessions table
        session_id = generate_session_id()
        #check if user has 2FA enabled
        twoFA = cur.cursor().execute('SELECT TotpKey FROM logins WHERE Username = ?', (request.form['username'],)).fetchone()[0]
        if twoFA is None:
            #if not, create session and return
            cur.cursor().execute('INSERT INTO sessions (SessionKey, UserID, CreationTime) VALUES (?, (SELECT UserID FROM logins WHERE Username = ?), datetime("now"))', (session_id, request.form['username'], ))
            cur.commit()
            response = make_response(f'"session_id":{session_id}, "message": "Logged in"', 200)
            response.set_cookie('session_id', session_id)
            return response
        else:
            #if so, create session and return
            cur.cursor().execute('INSERT INTO sessions (SessionKey, UserID, CreationTime, "2FA" ) VALUES (?, (SELECT UserID FROM logins WHERE Username = ?), datetime("now"), 0)', (session_id, request.form['username']))
            cur.commit()
            response = make_response(f'"session_id":{session_id}, "message": "Verify 2FA code at /2faVerify"', 200)
            response.set_cookie('session_id', session_id)
            return response

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    #get session from cookies or if not in cookies, get from request body
    session_id = request.cookies.get('session_id') if request.cookies.get('session_id') is not None else request.form['session_id']
    if session_id is None:
        return 'No session found', 400
    cur = get_db()
    cur.cursor().execute('DELETE FROM sessions WHERE SessionKey = ?', (session_id,))
    cur.commit()
    return 'Logged out', 200

@app.route('/check', methods=['GET', 'POST'])
def check():
    #check if session exists and if 2fa has been verified if 2fa is enabled
    # get session from cookies or if not in cookies, get from request body
    session_id = request.cookies.get('session_id') if request.cookies.get('session_id') is not None else request.form['session_id']
    session = get_db().cursor().execute('SELECT * FROM sessions WHERE SessionKey = ?', (session_id,)).fetchone()
    if session is None:
        return "Session does not exist"
    if session[3] == 0:
        return "2FA not verified"
    return "Session valid"

def verifySession(request, db):
    #check if session exists and if 2fa has been verified if 2fa is enabled
    # get session from cookies or if not in cookies, get from request body
    print("Verifying session")
    session_id = request.cookies.get('session_id') if request.cookies.get('session_id') is not None else request.form['session_id']
    session = db.cursor().execute('SELECT * FROM sessions WHERE SessionKey = ?', (session_id,)).fetchone()
    if session is None:
        return "Session does not exist"
    if session[3] == 0:
        return "2FA not verified"
    print("Session valid")
    return False

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
    session_id = request.cookies.get('session_id') if request.cookies.get('session_id') is not None else request.form['session_id']
    session = cur.cursor().execute('SELECT * FROM sessions WHERE SessionKey = ?', (session_id,)).fetchone()
    if session is None:
        return jsonify({'status': 'error','message': 'Session does not exist'}), 401
    #check if 2FA is enabled
    twoFA = cur.cursor().execute('SELECT TotpKey FROM logins WHERE UserID = ?', (session[1],)).fetchone()[0]
    if twoFA is not None:
        return jsonify({'status': 'error','message': '2FA already enabled'}), 401
    if request.form['step'] == '0':
        #check if login is valid
        password = cur.cursor().execute('SELECT password FROM logins WHERE UserID = ?', (session[1],)).fetchone()[0]
        if password != hash_password(request.form['password']):
            return jsonify({'status': 'error','message': 'Invalid password'}), 401
        #if so, return 2FA url
        key = pyotp.random_base32()
        totp = pyotp.TOTP(key)
        # use table Temp2FAKeys("UserID", "Key", "CreationTime")
        cur.cursor().execute('INSERT INTO Temp2FAKeys (UserID, Key, CreationTime) VALUES (?, ?, datetime("now"))', (session[1], key))
        # get username from UserID
        username = cur.execute('SELECT Username FROM users WHERE UserID = ?', (session[1],)).fetchone()[0]
        cur.commit()
        totpurl = totp.provisioning_uri(f"{username}@{ApplicationName}", issuer_name=ApplicationName)
        return jsonify({'status': 'success','message': 'proceed to step 1', 'url': totpurl}), 200
    elif request.form['step'] == '1':
        #check if 2FA code is correct
        key = cur.cursor().execute('SELECT Key FROM Temp2FAKeys WHERE UserID = ?', (session[1],)).fetchone()[0]
        if not pyotp.TOTP(key).verify(request.form['code']):
            return jsonify({'status': 'error','message': 'Invalid 2FA code, try again'}), 401
        #if so, update session and return
        cur.cursor().execute('UPDATE logins SET TotpKey = ? WHERE UserID = ?', (key, session[1]))
        cur.cursor().execute('DELETE FROM Temp2FAKeys WHERE UserID = ?', (session[1],))
        cur.commit()
        return jsonify({'status': 'success','message': '2FA enabled successfully'}), 200


@app.route('/2faVerify', methods=['POST'])
def twoFA():
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
    #check if session exists
    cur = get_db()
    session_id = request.cookies.get('session_id') if request.cookies.get('session_id') is not None else request.form['session_id']
    session = cur.execute('SELECT * FROM sessions WHERE SessionKey = ?', (session_id,)).fetchone()
    if session is None:
        return 'Session does not exist', 401
    #check if 2FA is enabled
    twoFA = cur.cursor().execute('SELECT TotpKey FROM logins WHERE UserID = ?', (session[1],)).fetchone()[0]
    if twoFA is None:
        return jsonify({'status': 'error','message': '2FA is not enabled'}), 401
    #check if 2FA code is correct
    if not pyotp.TOTP(twoFA).verify(request.form['code']):
        return jsonify({'status': 'error','message': 'Invalid 2FA code, try again'}), 401
    #if so, update session and return
    cur.cursor().execute('UPDATE sessions SET "2FA" = 1 WHERE SessionKey = ?', (session_id,))
    cur.commit()
    return jsonify({'status': 'success','message': '2FA verified successfully'}), 200

#################### UPLOAD ####################
# 0 = Only Me
# 1 = Only Friends
# 2 = Everyone
@app.route('/upload', methods=['POST'])
def upload():
    print("upload")
    db = get_db()
    # verify session
    sessionError = verifySession(request, db)
    if sessionError:
        return sessionError, 401
    print("session verified")
    # get session from cookies or if not in cookies, get from request body
    session_id = request.cookies.get('session_id') if request.cookies.get('session_id') is not None else request.form.get("session_id")
    print("session_id: " + session_id)
    """
    request object:
    {
        session_id: {{ session_id }}, # optional, if not in cookies
        noOfImages: {{ number }}, # 0-5
        image1Visiblity: {{ image1Visibility }}, # 0-2
        image2Visiblity: {{ image2Visibility }}, # 0-2
        image3Visiblity: {{ image3Visibility }}, # 0-2
        image4Visiblity: {{ image4Visibility }}, # 0-2
        image5Visiblity: {{ image5Visibility }}, # 0-2
        image1: {{ image1 }},
        image2: {{ image2 }},
        image3: {{ image3 }},
        image4: {{ image4 }},
        image5: {{ image5 }},
        caption0: {{ caption0 }}, # optional
        caption1: {{ caption1 }}, # optional
        caption2: {{ caption2 }} # optional
    }
    """
    # check if user already has a post today, if so, return post id
    today = db.cursor().execute('SELECT * FROM archive WHERE UserID = (SELECT UserID FROM sessions WHERE SessionKey = ?) AND Date LIKE ?', (session_id, datetime.now().strftime("%Y-%m-%d") + "%")).fetchone()
    if today is not None:
        return make_response(
            jsonify(
                {
                    "status": "not uploaded", 
                    "message": "You already have a post today",
                    "postID": today[0]
                }
            ), 429
        )
    # check if there are any images, if not, just save the caption
    # save to table archive("PostID", "UserID", "Date", "Image1", "Image2", "Image3", "Image4", "Image5", "Caption")
    # PostID is a random uuid
    # UserID is the UserID of the user who uploaded the post
    # Date is the current date using datetime("now")
    # Images is the number 
    # Caption is the caption of the post
    # save to table images("UserID", "ImageURI", "PostID", "UploadDate")

    postID = str(uuid4())
    UserID = db.cursor().execute('SELECT UserID FROM sessions WHERE SessionKey = ?', (session_id,)).fetchone()[0] 
    print("UserID:", UserID)
    post = {
        'PostID': postID,
        'UserID': UserID, 
        'caption': ""
    }
    pprint(request.form['caption0'])
    if request.form['caption0']:
        post['caption'] = post['caption']+f"Only visible for you: {request.form['caption0']}\n"
    if request.form['caption1']:
        post['caption'] = post['caption']+f"Only visible for your friends: {request.form['caption1']}\n"
    if request.form['caption2']:
        post['caption'] = post['caption']+f"Visible for everyone: {request.form['caption2']}"
    pprint(post)
    
    OFImages = []
    EImages = []
    for x in range(0, int(request.form['noOfImages'])):
        #compress and save image, then save the name of the image to the database
        image = request.files[f'image{x+1}']
        name = str(uuid4())
        if int(request.form[f'image{x+1}Visibility']) == 1:
            OFImages.append(name)
        elif int(request.form[f'image{x+1}Visibility']) == 2:
            EImages.append(name)
        post[f'image{x+1}'] = name
        compressedImage = compress_image(image)
        with open(f"content/images/{name}.jpg", 'wb') as f:
            f.write(compressedImage.getvalue())
        db.cursor().execute('INSERT INTO images (UserID, ImageURI, PostID, UploadDate) VALUES (?, ?, ?, datetime("now"))', (UserID, name, postID))

    #live_posts("PostID", "UserID", "Visibility", "Image1", "Image2", "Image3", "Image4", "Image5", "Caption", "UploadTime")
    #visiblity: 1 = Only Friends, 2 = Everyone
    # if applicable, make a post visible for friends
    OF = True if len(OFImages) > 0 or request.form['caption1'] else False
    # if applicable, make a post visible for everyone
    E = True if len(EImages) > 0 or request.form['caption2'] else False
    if OF:
        stringToExecute = 'INSERT INTO live_posts (PostID, UserID, Visibility, '
        for x in range(0, int(request.form['noOfImages'])):
            stringToExecute += f'Image{x+1}, ' if request.form[f'image{x+1}Visibility'] == '1' else ''
        stringToExecute += 'Caption, UploadTime) VALUES (?, ?, 1, '
        for x in range(0, int(request.form['noOfImages'])):
            stringToExecute += '?, ' if request.form[f'image{x+1}Visibility'] == '1' else ''
        stringToExecute += '?, datetime("now"))\n'
        print(stringToExecute)
        db.cursor().execute(stringToExecute, (generate_session_id(), UserID, *OFImages, request.form['caption1']))
    E = True if 2 in [int(request.form[f'image{x+1}Visibility']) for x in range(0, int(request.form['noOfImages']))] or request.form['caption2'] else False
    if E:
        stringToExecute = 'INSERT INTO live_posts (PostID, UserID, Visibility, '
        for x in range(0, int(request.form['noOfImages'])):
            stringToExecute += f'Image{x+1}, ' if request.form[f'image{x+1}Visibility'] == '2' else ''
        stringToExecute += 'Caption, UploadTime) VALUES (?, ?, 2, '
        for x in range(0, int(request.form['noOfImages'])):
            stringToExecute += '?, ' if request.form[f'image{x+1}Visibility'] == '2' else ''
        stringToExecute += '?, datetime("now"))'
        print(stringToExecute)
        db.cursor().execute(stringToExecute, (generate_session_id(), UserID, *EImages, request.form['caption2']))
    
    

    #make a database entry inserting each key from the post dictionary
    stringToExecute = 'INSERT INTO archive (Date, '
    for key in post:
        stringToExecute += f'{key}, '
    stringToExecute = stringToExecute[:-2] + ') VALUES (datetime("now"), '
    for key in post:
        stringToExecute += '?, '
    stringToExecute = stringToExecute[:-2] + ')'
    print(stringToExecute)
    db.cursor().execute(stringToExecute, tuple(post.values()))
    db.commit()
    print("post saved")
    return make_response(
        jsonify(
            {
                "status": "uploaded",
                "message": "Post uploaded successfully",
                "postID": postID
            }
        )
    )

#################### FOLLOWERS ####################
#user needs to be able to follow, unfollow, see who they follow, see who follows them
#use routes /follow, /unfollow, /following, /followers

@app.route('/follow', methods=['POST'])
def follow():
    """
    request object should contain:
    {
        "session_id": {{ session_id }}, #optional, or use cookie
        "userToFollow": {{ username }},
        "level": {{ level }} #1 = follow, 2 = friend
    }
    if user chooses to follow add as a follower
    if user chooses to friend add as a follower and send a friend request
    """
    db = get_db()
    #table followers in format: followers(follower, followee, type)
    session_id = request.cookies.get('session_id') if not request.form.get('session_id') else request.form.get('session_id')
    if not session_id:
        return make_response(jsonify({"status": "error","message": "Invalid or missing sessionID"}), 401)
    userToFollow = request.form['userToFollow']
    level = request.form['level']
    if level == "2":
        #not implemented yet
        return make_response(jsonify({"status": "error","message": "Friend requests not implemented yet"}), 501)
    #get the UserID of the user who is following
    UserID = db.cursor().execute('SELECT UserID FROM sessions WHERE SessionKey = ?', (session_id,)).fetchone()[0]
    #chec if user exists and get the UserID of the user who is being followed
    userToFollowID = db.cursor().execute('SELECT UserID FROM users WHERE Username = ?', (userToFollow,)).fetchone()
    if not userToFollowID:
        return make_response(
            jsonify(
                {
                    "message": "User does not exist",
                    "status": "error"
                }
            ), 404
        )
    userToFollowID = userToFollowID[0]
    #check if the user is already following the user
    if db.cursor().execute('SELECT * FROM followers WHERE follower = ? AND followee = ?', (UserID, userToFollowID)).fetchone():
        return make_response(
            jsonify(
                {
                    "status": "error",
                    "message": "You are already following this user"
                }
            )
        )
    #add the user to the followers table
    db.cursor().execute('INSERT INTO followers (follower, followee, type) VALUES (?, ?, ?)', (UserID, userToFollowID, level))
    db.commit()
    return make_response(
        jsonify(
            {
                "status": "success",
                "message": f"You are now following {userToFollow}"
            }
        )
    )

@app.route('/unfollow', methods=['POST'])
def unfollow():
    """
    request object should contain:
    {
        "session_id": {{ session_id }}, #optional, or use cookie
        "userToUnfollow": {{ username }}
    }
    """
    db = get_db()
    #table followers in format: followers(follower, followee, type)
    session_id = request.cookies.get('session_id') if not request.form.get('session_id') else request.form.get('session_id')
    if not session_id:
        return make_response(jsonify({"status": "error","message": "Invalid or missing sessionID"}), 401)
    userToUnfollow = request.form['userToUnfollow']
    #get the UserID of the user who is following
    UserID = db.cursor().execute('SELECT UserID FROM sessions WHERE SessionKey = ?', (session_id,)).fetchone()[0]
    # #get the UserID of the user who is being followed
    # userToUnfollowID = db.cursor().execute('SELECT UserID FROM users WHERE Username = ?', (userToUnfollow,)).fetchone()[0]
    #check if the user is already following the user
    if not db.cursor().execute('SELECT * FROM followers WHERE follower = ? AND followee = (SELECT UserID FROM users WHERE Username = ?)', (UserID, userToUnfollow)).fetchone():
        return make_response(
            jsonify(
                {
                    "status": "error",
                    "message": f"You are not following {userToUnfollow}"
                }
            )
        )
    #remove the user from the followers table
    db.cursor().execute('DELETE FROM followers WHERE follower = ? AND followee = (SELECT UserID FROM users WHERE Username = ?)', (UserID, userToUnfollow))
    db.commit()
    return make_response(
        jsonify(
            {
                "status": "success",
                "message": f"You are no longer following {userToUnfollow}"
            }
        )
    )

@app.route('/following', methods=['GET', 'POST'])
def following():
    """
    request object should contain if post request:
    {
        "session_id": {{ session_id }}, #optional, or use cookie
    }
    response object should contain:
    {
        "status": "success",
        "message": "you are following {{number of users}} users",
        "number": {{number of users}},
        "users": [
            {
                "username": {{ username }},
                "level": {{ level }} #1 = follow, 2 = friend
            },
            ...
        ]
    }

    """
    db = get_db()
    #table followers in format: followers(follower, followee, type)
    if request.method == 'POST':
        session_id = request.cookies.get('session_id') if not request.form.get('session_id') else request.form.get('session_id')
    else:
        session_id = request.cookies.get('session_id')
    if not session_id:
        return make_response(jsonify({"status": "error","message": "Invalid or missing sessionID"}), 401)
    following = db.cursor().execute('SELECT * FROM followers WHERE follower = (SELECT UserID FROM sessions WHERE SessionKey = ?)', (session_id,)).fetchall()
    if not following:
        return make_response(jsonify({"status": "success","message": "You are not following anyone","number": 0,"users": []}))
    users = []
    for user in following:
        users.append(
            {
                "username": db.cursor().execute('SELECT Username FROM users WHERE UserID = ?', (user[1],)).fetchone()[0],
                "level": user[2]
            }
        )
    return make_response(
        jsonify(
            {
                "status": "success",
                "message": f"You are following {len(users)} users",
                "number": len(users),
                "users": users
            }
        )
    )

@app.route('/followers', methods=['GET', 'POST'])
def followers():
    """
    if post request request object should contain:
    {
        "session_id": {{ session_id }}, #optional, or use cookie
    }
    response object should contain:
    {
        "status": "success",
        "message": "{{username}} is followed by {{number of users}} users",
        "number": {{number of users}},
        "users": [
            {
                "username": {{ username }},
                "level": {{ level }} #1 = follow, 2 = friend
            },
            ...
        ]
    }
    """
    db = get_db()
    #table followers in format: followers(follower, followee, type)
    if request.method == 'POST':
        session_id = request.cookies.get('session_id') if not request.form.get('session_id') else request.form.get('session_id')
        if not session_id:
            return make_response(jsonify({"status": "error","message": "Invalid or missing sessionID"}), 401)
    else:
        session_id = request.cookies.get('session_id')
    followers = db.cursor().execute('SELECT * FROM followers WHERE followee = (SELECT UserID FROM sessions WHERE SessionKey = ?)', (session_id,)).fetchall()
    if not followers:
        return make_response(jsonify({"status": "success","message": "You have no followers","number": 0,"users": []}))
    users = []
    for user in followers:
        users.append(
            {
                "username": db.cursor().execute('SELECT Username FROM users WHERE UserID = ?', (user[0],)).fetchone()[0],
                "level": user[2]
            }
        )
    return make_response(
        jsonify(
            {
                "status": "success",
                "message": f"You have {len(users)} followers",
                "number": len(users),
                "users": users
            }
        )
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=81)