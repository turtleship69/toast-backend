from turtle import pos
from .hanko import login_required
from .tools import get_db, get_image_url

from flask import Blueprint, g
from flask import jsonify
import re

bp = Blueprint("get_posts", __name__, url_prefix="/get_posts")

POST_ID_FORMAT = re.compile(
        "^[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}\Z",
        re.I,
    )

@bp.route("/get_post/<post_id>")
@login_required
def get_post(post_id):
    db = get_db()
    error = None
    post_dict = {}

    # check string matches regex ^[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12}$
    global POST_ID_FORMAT
    if not POST_ID_FORMAT.match(
        post_id,
    ):
        print("flag 1")
        return jsonify({"status": "error", "message": "Invalid post ID"}), 400

    # get post from database
    post = db.execute(
        "SELECT lp.*, u.Username, u.GravatarURL FROM live_posts lp JOIN Users u ON lp.UserID = u.UserID WHERE lp.PostID = ?",
        (post_id,),
    ).fetchone()
    if not post:
        return jsonify({"status": "error", "message": "Post not found"}), 400
    
    

    # check if post is public
    if post[5] == 1 and not g.UserID == post[1]:
        # check if the current user has access to the post, they are either the OP or friend
        friendship = db.execute(
            "SELECT Type FROM friendships WHERE Follower = ? AND Followee = ?",
            (g.UserID, post[1]),
        ).fetchone()

        if not friendship:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "You do not have access to this post",
                    }
                ),
                400,
            )

    if error:
        return jsonify({"status": "error", "message": error}), 400

    if post[3]:
        post_dict["Body"] = post[3]

    for image in range(5, 10):
        if post[image]:
            print(post[image])
            post_dict[f"Image{image - 4}"] = get_image_url(post[image])


    post_dict["PostID"] = post[0]
    post_dict["Username"] = post[11]
    post_dict["Title"] = post[2]
    post_dict["Visibility"] = post[4]
    post_dict["UploadTime"] = post[10]
    post_dict["Gravatar"] = post[12]


    # post_dict = {
    #     "PostID": post[0],
    #     "Username": post[9], 
    #     "Title": post[2],
    #     "Visibility": post[4],
    #     "UploadTime": post[10],
    # }

    return jsonify(post_dict)
