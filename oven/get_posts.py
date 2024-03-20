from .models import Post, getPostById
from .cache import cache

from flask import Blueprint, g, jsonify
import re

bp = Blueprint("get_posts", __name__, url_prefix="/get_posts")

POST_ID_FORMAT = re.compile(
    "^[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}\\Z",
    re.I,
)


# 0 = Only Me
# 1 = Only Friends
# 2 = Everyone


@bp.route("/get_post/<post_id>")
@cache(60 * 5)
def get_post(post_id):
    error = None

    # check string matches regex
    global POST_ID_FORMAT
    if not POST_ID_FORMAT.match(post_id):
        return jsonify({"status": "error", "message": "Invalid post ID"}), 400

    post = getPostById(post_id)

    if not post:
        return jsonify({"status": "error", "message": "Post not found"}), 400

    if post.visibility == 2:
        return jsonify(post.getDict())
    else:
        if not g.logged_in:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Not logged in",
                        "errorCode": "loginRequired",
                    }
                ),
                400,
            )
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


@bp.route("/home")
def home():
    if not g.logged_in:
        # get 10 most recent public posts
        posts = g.db.execute(
            "SELECT lp.*, u.Username, u.GravatarURL FROM live_posts lp JOIN Users u ON lp.UserID = u.UserID WHERE lp.Visibility = 2 ORDER BY lp.UploadTime DESC LIMIT 10"
        ).fetchall()
    else:
        # find all people g.User follows (following type=1 or (type=2 and accepted=true))
        following = g.db.execute(
            "SELECT Followee FROM followers WHERE Follower = ? AND Type = 1",
            (g.UserID,),
        ).fetchall()

        following = [x[0] for x in following] if following else [None]

        friends = g.db.execute(
            "SELECT Followee FROM followers WHERE Follower = ? AND Type = 2 AND Accepted = 1",
            (g.UserID,),
        ).fetchall()
        friends = [x[0] for x in friends] if friends else [None]
        print(friends)

        # get 10 most recent posts from:
        # people g.User follows - only public posts
        # people g.User is friends with - public and friends only posts
        # posts by g.User - all posts
        command = f"SELECT lp.*, u.Username, u.GravatarURL FROM live_posts lp JOIN Users u ON lp.UserID = u.UserID WHERE (lp.Visibility = 2 AND lp.UserID IN ({','.join('?'*len(following))})) OR (lp.Visibility >= 1 AND lp.UserID IN ({','.join('?'*len(friends))})) OR lp.UserID = ? ORDER BY lp.UploadTime DESC LIMIT 10".format()
        posts = g.db.execute(
            command,
            (*following,
            *friends,
            g.UserID,)
        ).fetchall()

        if len(posts) < 10:
            posts = posts + g.db.execute(
            "SELECT lp.*, u.Username, u.GravatarURL FROM live_posts lp JOIN Users u ON lp.UserID = u.UserID WHERE lp.Visibility = 2 ORDER BY lp.UploadTime DESC LIMIT ?", (10-len(posts),)
        ).fetchall()

    # convert posts to Post objects
    postsDict = {"posts": []}
    for post in posts:
        print(len(post))
        postsDict["posts"].append(
            Post(
                post[0],
                post[1],
                post[11],
                post[12],
                post[2],
                post[3],
                post[4],
                post[5],
                post[6],
                post[7],
                post[8],
                post[9],
                post[10],
            ).getDict()
        )

    return jsonify(postsDict)
