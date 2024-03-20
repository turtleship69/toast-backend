#this file shows people their notifications
from flask import Blueprint, g, request

from .hanko import login_required
from flask import jsonify

bp = Blueprint('notifications', __name__, url_prefix='/notifications')

"""type:details
    NewFollower:UserID
    FollowRequest:UserID"""

@bp.route('/')
@login_required
def index():
    #get users notifications from the db
    notifs = g.db.execute(
        """SELECT notifications.*, 
(SELECT Username FROM users WHERE UserID = notifications.details) AS Username 
FROM notifications WHERE UserID = ?""", (g.UserID,)
        ).fetchall()
    
    notifDict = []
    
    for notif in notifs:
        notifDict.append(
            {
                "user_id": notif[0],
                # "id": notif[1],
                "type": notif[2],
                "details": notif[3],
                "time": notif[4],
                "username": notif[5]
            }
        )
    
    return jsonify(notifDict)

@bp.route('/dismiss/<id>')
@login_required
def dismiss(id):
    notif = g.db.execute(
        'SELECT * FROM notifications WHERE id = ?', (id,)
        ).fetchone()
    if notif is None:
        return jsonify({"status": "error", "message": "No such notification"})
    g.db.execute(
        'DELETE FROM notifications WHERE id = ?', (id,)
        )
    return jsonify({"status": "success", "message": "Notification dismissed"})

@bp.route('/accept_request', methods=['POST'])
@login_required
def accept_request():
    follower = request.form.get("UserID")
    #accept a follow request
    notif = g.db.execute(
        'SELECT * FROM notifications WHERE UserID = ? AND Type = ? AND Details', (g.UserID, "FollowRequest", follower)
        ).fetchone()
    
    if notif is None:
        return jsonify({"status": "error", "message": "No such notification"})
    
    #update follow type to accepted, remove old follow and remove notif
    commands = [
        ("UPDATE followers set Accepted = 1 WHERE Follower = ? AND Followee = ?", (g.UserID, follower)),
        ("DELETE FROM notifications WHERE UserID = ? AND Type = ? AND Details = ?", (g.UserID, "FollowRequest", follower)),
        ("DELETE FROM followers WHERE Follower = ? AND Followee = ? AND Type = ?", (follower, g.UserID, 1))
    ]
    g.db.executemany(*commands)

    return jsonify({"status": "success", "message": "Request accepted"})
    