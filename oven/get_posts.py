from .models import getPostById

from flask import Blueprint, g
from flask import jsonify
import re

bp = Blueprint("get_posts", __name__, url_prefix="/get_posts")

POST_ID_FORMAT = re.compile(
        "^[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}\Z",
        re.I,
    )


# 0 = Only Me
# 1 = Only Friends
# 2 = Everyone

@bp.route("/get_post/<post_id>")
# @login_required
def get_post(post_id):
    error = None

    # check string matches regex ^[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12}$
    global POST_ID_FORMAT
    if not POST_ID_FORMAT.match(post_id):
        return jsonify({"status": "error", "message": "Invalid post ID"}), 400

    # get post from database
    # post = db.execute(
    #     "SELECT lp.*, u.Username, u.GravatarURL FROM live_posts lp JOIN Users u ON lp.UserID = u.UserID WHERE lp.PostID = ?",
    #     (post_id,),
    # ).fetchone()
    post = getPostById(post_id, g.db)

    if not post:
        return jsonify({"status": "error", "message": "Post not found"}), 400
    
    if post.visibility == 2:
        return jsonify(post.getDict())
    else: 
        if not g.logged_in:
            return jsonify({"status": "error", "message": "Not logged in", "errorCode": "loginRequired"}), 400
    print(g.User.username)
    
    
    if post.visibility == 0: 
        if g.UserID == post.poster_id:
            return jsonify(post.getDict())
        else: 
            return jsonify({"status": "error", "message": "Post not found"}), 400

    # check if post is public
    if post.visibility == 1 and not g.UserID == post.poster_id:
        # check if the current user has access to the post, they are either the OP or friend
        friendship = g.db.execute(
            "SELECT Type FROM followers WHERE Follower = ? AND Followee = ?",
            (g.UserID, post.poster_id),
        ).fetchone()

        if not friendship and friendship == 2:
            return jsonify({"status": "error", "message": "Post not found"}), 400

    if error:
        return jsonify({"status": "error", "message": error}), 400

    post_dict = post.getDict()

    return jsonify(post_dict)