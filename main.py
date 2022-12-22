import hashlib
def gravatar(email, size=200):
    return f"https://www.gravatar.com/avatar/{hashlib.md5(email.lower().encode('utf-8')).hexdigest()}?s={size}"
def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


import pyotp
import time


from flask import Flask, request, g
from datetime import datetime

app = Flask(__name__)

import sqlite3
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


startTime = datetime.now()
@app.route('/')
def index():
    return f"Server running for {datetime.now() - startTime}"

@app.route('/signup', methods=['POST'])
def signup():
    cur = get_db()
    user = {
        'username': request.form['username'],
        'email': request.form['email'],
        'phone': request.form['phone'],
        'password': hash_password(request.form['password']),
    }
    cur.cursor().execute('INSERT INTO logins (username, email, phone, password) VALUES (?, ?, ?, ?)', (user['username'], user['email'], user['phone'], user['password']))
    cur.commit()
    return 'Signed up successfully', 200

@app.route('/login', methods=['POST'])
def login():
    invalid = False
    cur = get_db().cursor()
    #check if hashed password matches the saved password for user
    cur.execute('SELECT password FROM logins WHERE username = ?', (request.form['username'],))
    password = cur.fetchone()
    print(password)
    if password[0] is None:
        invalid = True
    if password[0] != hash_password(request.form['password']):
        invalid = True
    if invalid:
        return 'Invalid username or password', 401
    else:
        return 'Logged in successfully', 200



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=81)