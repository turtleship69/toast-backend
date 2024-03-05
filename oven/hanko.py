import functools
from flask import (
    Blueprint,
    g,
    jsonify,
    redirect,
    request,
    session,
)
from .tools import generate_session_id, get_db, User, getGravatarFromHankoJwt
import time
import jwt  # upm package(pyjwt)
from pprint import pprint
from . import config as cfg


# Status: 0: valid, 1: signing up
# Onboarding status: 0: not done, 1: done
bp = Blueprint("hanko", __name__, url_prefix="/hanko")

safe_username_chars = [
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
    'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
    'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
    '_', '-', '.']


@bp.before_app_request
def load_logged_in_user():
    print(f"session keys: {session.keys()}")

    get_db()

    session_id = session.get("session_id")
    g.session_id = session_id
    if session_id is None:
        g.session = None
        g.UserID = None
    else:
        session_data = (
            g.db.cursor()
            .execute("SELECT * FROM sessions WHERE SessionKey = ?", (session_id,))
            .fetchone()
        )
        print(f"session_data: {session_data}")
        g.session = session_data
        g.UserID = session_data[1]

        user_data = (
            g.db.cursor()
            .execute("SELECT * FROM users WHERE UserID = ?", (g.UserID,))
            .fetchone()
        )
        g.user = user_data
        g.User = User(
            user_data[0], user_data[1], user_data[2], user_data[3], user_data[4]
        )


@bp.after_app_request
def close_database(response):
    g.db.commit()
    g.db.close()
    # print("bye")
    response.headers.add("Access-Control-Allow-Origin", f"https://{cfg.AUDIENCE}")
    return response


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.session is None:
            response = {"status": "error", "message": "Invalid session"}
            return jsonify(response), 401
        if g.User.Onboarded == 0:
            response = {
                "status": "error",
                "message": "User needs to finish signing up at /onboarding",
            }
            return jsonify(response), 401
        return view(**kwargs)

    return wrapped_view


@bp.route("/login")  # , methods=["POST"]
def login():
    redirect_url = request.args.get("redirect_url", "")
    redirect_url_parameter = f"?redirect_url={redirect_url}"

    # print(g.session)
    if g.session:
        print(f"session id to be deleted: {len(g.session_id)}")
        g.db.cursor().execute(
            "DELETE FROM sessions WHERE SessionKey = ?", (g.session_id,)
        )
        g.db.commit()

    session_id = generate_session_id()
    # Retrieve the JWT from the cookie
    jwt_cookie = request.cookies.get("hanko")
    # print(jwt_cookie)
    if not jwt_cookie:  # check that the cookie exists
        return redirect("/")
    try:
        kid = jwt.get_unverified_header(jwt_cookie)["kid"]
        payload = jwt.decode(
            str(jwt_cookie),
            cfg.public_keys[kid],
            algorithms=["RS256"],
            audience=cfg.AUDIENCE,
        )
        pprint(payload)
    except Exception as e:
        # The JWT is invalid
        print(e)
        return jsonify({"message": "unknown account"})

    UserID = payload["sub"]
    user = (
        g.db.cursor()
        .execute("SELECT * FROM users WHERE UserID = ?", (UserID,))
        .fetchone()
    )
    if not user:
        g.db.cursor().execute(
            "INSERT INTO sessions (SessionKey, UserID, CreationTime, Status) VALUES (?, ?, ?, 1)",
            (
                session_id,
                UserID,
                int(time.time()),
            ),
        )

        g.db.cursor().execute(
            "INSERT INTO users (UserID, Username, GravatarURL, Onboarded) VALUES (?, ?, ?, 0)",
            (UserID, UserID, getGravatarFromHankoJwt(jwt_cookie)),
        )

        g.db.commit()

        response = {
            "message": "signed up successfully",
            "status": "success",
            "redirect_url": "/onboarding" + redirect_url_parameter,
            "session_id": session_id,
        }

        session["session_id"] = session_id
        return jsonify(response)

    g.db.cursor().execute(
        "INSERT INTO sessions (SessionKey, UserID, CreationTime, Status) VALUES (?, ?, ?, 0)",
        (session_id, UserID, int(time.time())),
    )

    if user[3] == 0:
        response = {
            "message": "user not onboarded yet",
            "status": "success",
            "redirect_url": "/onboarding" + redirect_url_parameter,
            "session_id": session_id,
        }

        session["session_id"] = session_id
        return jsonify(response)

    status = 0 if user[3] else 1

    g.db.commit()

    response = {
        "message": "logged in successfully",
        "status": "success",
        "redirect_url": "/" if not redirect_url else redirect_url,
        "session_id": session_id,
    }

    session["session_id"] = session_id
    return jsonify(response)


@bp.route("/onboarding", methods=["POST"])
def onboarding():
    """
    request object:
    {
        "username": "username the user wants"
        "redirect_url": optional value, if present redirect to this url instead
        "bio": "bio"
    }
    """
    username = request.form.get("username")
    bio = request.form.get("bio")

    redirect_url = request.form.get("redirect_url")
    if not redirect_url:
        redirect_url = f"/user?u={username}"
    # print(dict(request.form))
        
    if not username:
        response = {"status": "error", "message": "username not provided"}
        return jsonify(response), 403

    user = (
        g.db.cursor()
        .execute("SELECT * FROM users WHERE UserID = ?", (g.UserID,))
        .fetchone()
    )

    if user[3] == 1:
        response = {"status": "error", "message": "user already signed up"}
        return jsonify(response), 403

    print("a")

    taken_username = g.db.execute(
        "SELECT Username FROM users WHERE Username = ? LIMIT 1", (username,)
    ).fetchone()
    if taken_username:
        response = {"status": "error", "message": "username already taken"}
        return jsonify(response), 403

    print("b")

    g.db.cursor().execute(
        "UPDATE sessions SET Status = 0 WHERE UserID = ?", (g.UserID,)
    )
    g.db.cursor().execute(
        "UPDATE users SET Onboarded = 1, Username = ?, Bio = ? WHERE UserID = ?",
        (
            username,
            bio,
            g.UserID,
        ),
    )

    response = {
        "message": "onboarding completed",
        "status": "success",
        "redirect_url": redirect_url,
    }
    print("c")
    return jsonify(response)


# @app.route("/find")
# def find():


@bp.route("/check", methods=["GET", "POST"])
@login_required
def check():
    response = {"status": "success", "message": "Session Valid"}
    return jsonify(response)
