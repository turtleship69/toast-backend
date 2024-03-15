from cgitb import reset
from pprint import pprint
from uuid import uuid4
import time
# from urllib import response
from flask import Blueprint, g, jsonify, make_response, request

from .models import getUserByUsername
from .hanko import login_required

bp = Blueprint("post", __name__, url_prefix="/friendships")


@bp.route("/user/<username>")
def user_info(username):
    # return gravatar, following and follower stats, bio and posts of user from their username
    """response = {
        "following": int #no of following
        "followers": int #no of followers
        "bio": str #bio
    }"""
    # get UserID from username
    user = getUserByUsername(username, g.db)

    if not user:
        return make_response(
            jsonify({"status": "error", "message": "User does not exist"}), 404
        )

    user_info = user.getDict(g.db)
    user_info["status"] = "success"

    pprint(user_info)
    return jsonify(user_info)


@bp.route("/follow/<username>/<int:level>")
@login_required
def follow(username, level):
    #1 = follow, 2 = friend
    # table followers in format: followers(follower, followee, type, accepted)

    if level == 1:
        accepted = 1
        notif = "NewFollower"
    elif level == 2:
        accepted = 0
        notif = "FriendRequest"
    else:
        return jsonify({"status": "error", "message": "Invalid level"}), 400
    

    # check if user exists and get the UserID of the user who is being followed
    userToFollowID = g.db.execute(
        "SELECT UserID FROM users WHERE Username = ? LIMIT 1", (username,)
    ).fetchone()
    if not userToFollowID:
        return make_response(
            jsonify({"message": "User does not exist", "status": "error", "errorCode": "user_not_found"}), 404
        )
    userToFollowID = userToFollowID[0]
    # check if the user is already following the user
    following = g.db.execute(
        "SELECT * FROM followers WHERE follower = ? AND followee = ?",
        (g.UserID, userToFollowID),
    ).fetchone()
    print(following)
    if following and following[0] == level:
        return (
            jsonify(
                {"status": "error", "message": "You are already following this user", "errorCode": "already_following"}
            ),
            409,
        )
    # add the user to the followers table
    g.db.cursor().execute(
        "INSERT INTO followers (follower, followee, type, accepted) VALUES (?, ?, ?, ?)",
        (g.UserID, userToFollowID, level, accepted),
    )
    # add a notification to the notifications table

    g.db.cursor().execute(
        "INSERT INTO notifications (UserID, NotifID, Type, Details, Time) VALUES (?, ?, ?, ?, ?)",
        (userToFollowID, str(uuid4()), notif, g.UserID, int(time.time())),
    )
    return make_response(
        jsonify({"status": "success", "message": f"You are now following {username}"})
    )

@bp.route("/accept/<notif_id>")
@login_required
def accept(notif_id): #change the follow to accepted and delete the notification
    #check if the notification exists
    notif = g.db.execute(
        "SELECT * FROM notifications WHERE NotifID = ? AND UserID = ?",
        (notif_id, g.UserID),
    ).fetchone()
    if not notif:
        return make_response(
            jsonify({"status": "error", "message": "No such notification"}), 404
        )
    #update follow type to accepted, remove old follow and remove notif
    commands = [
        ("UPDATE followers set Accepted = 1 WHERE Follower = ? AND Followee = ? AND Type = 2", (g.UserID, notif["Details"])),
        ("DELETE FROM notifications WHERE UserID = ? AND Type = ? AND Details = ?", (g.UserID, "FollowRequest", notif["Details"])),
        ("DELETE FROM followers WHERE Follower = ? AND Followee = ? AND Type = ?", (notif["Details"], g.UserID, 1))
    ]
    g.db.executemany(*commands)

    return jsonify({"status": "success", "message": "Request accepted"})

@bp.route("/unfollow/<username>")
@login_required
def unfollow(username):
    # #get the UserID of the user who is being followed
    # userToUnfollowID = db.cursor().execute('SELECT UserID FROM users WHERE Username = ?', (userToUnfollow,)).fetchone()[0]
    # check if the user is already following the user
    if (
        not g.db
        .execute(
            "SELECT * FROM followers WHERE follower = ? AND followee = (SELECT UserID FROM users WHERE Username = ?) LIMIT 1",
            (g.UserID, username),
        )
        .fetchone()
    ):
        return make_response(
            jsonify(
                {
                    "status": "error",
                    "message": f"You are not following {username}",
                    "errorCode": "not_following",
                }
            )
        )
    # remove the user from the followers table
    g.db.execute(
        "DELETE FROM followers WHERE follower = ? AND followee = (SELECT UserID FROM users WHERE Username = ?)",
        (g.UserID, username),
    )
    return make_response(
        jsonify(
            {
                "status": "success",
                "message": f"You are no longer following {username}",
            }
        )
    )


@bp.route("/following", methods=["GET", "POST"])
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
    # table followers in format: followers(follower, followee, type)
    if request.method == "POST":
        session_id = (
            request.cookies.get("session_id")
            if not request.form.get("session_id")
            else request.form.get("session_id")
        )
    else:
        session_id = request.cookies.get("session_id")
    if not session_id:
        return make_response(
            jsonify({"status": "error", "message": "Invalid or missing sessionID"}), 401
        )
    following = (
        g.db.cursor()
        .execute(
            "SELECT * FROM followers WHERE follower = (SELECT UserID FROM sessions WHERE SessionKey = ?)",
            (session_id,),
        )
        .fetchall()
    )
    if not following:
        return make_response(
            jsonify(
                {
                    "status": "success",
                    "message": "You are not following anyone",
                    "number": 0,
                    "users": [],
                }
            )
        )
    users = []
    for user in following:
        users.append(
            {
                "username": g.db.cursor()
                .execute("SELECT Username FROM users WHERE UserID = ?", (user[1],))
                .fetchone()[0],
                "level": user[2],
            }
        )
    return make_response(
        jsonify(
            {
                "status": "success",
                "message": f"You are following {len(users)} users",
                "number": len(users),
                "users": users,
            }
        )
    )


@bp.route("/followers", methods=["GET", "POST"])
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
    # table followers in format: followers(follower, followee, type)
    if request.method == "POST":
        session_id = (
            request.cookies.get("session_id")
            if not request.form.get("session_id")
            else request.form.get("session_id")
        )
        if not session_id:
            return make_response(
                jsonify({"status": "error", "message": "Invalid or missing sessionID"}),
                401,
            )
    else:
        session_id = request.cookies.get("session_id")
    followers = (
        g.db.cursor()
        .execute(
            "SELECT * FROM followers WHERE followee = (SELECT UserID FROM sessions WHERE SessionKey = ?)",
            (session_id,),
        )
        .fetchall()
    )
    if not followers:
        return make_response(
            jsonify(
                {
                    "status": "success",
                    "message": "You have no followers",
                    "number": 0,
                    "users": [],
                }
            )
        )
    users = []
    for user in followers:
        users.append(
            {
                "username": g.db.cursor()
                .execute("SELECT Username FROM users WHERE UserID = ?", (user[0],))
                .fetchone()[0],
                "level": user[2],
            }
        )
    return make_response(
        jsonify(
            {
                "status": "success",
                "message": f"You have {len(users)} followers",
                "number": len(users),
                "users": users,
            }
        )
    )
