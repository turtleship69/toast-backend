# this file defines classes of items to be retrieved from the database
from oven.tools import get_image_url
from flask import g

class Post:
    def __init__(
        self,
        postId: str,
        posterId: str,
        username: str,
        gravatar: str,
        title: str,
        body: str,
        visibility: int,
        UploadTime: int,
        Image1=None,
        Image2=None,
        Image3=None,
        Image4=None,
        Image5=None,
    ):
        self.postId = postId
        self.poster_id = posterId
        self.username = username
        self.gravatar = gravatar
        self.title = title
        self.body = body
        self.visibility = visibility
        self.UploadTime = UploadTime
        self.Image1 = Image1
        self.Image2 = Image2
        self.Image3 = Image3
        self.Image4 = Image4
        self.Image5 = Image5

    def getDict(self) -> dict:
        post = {
            "PostID": self.postId,
            "Username": self.username,
            "Gravatar": self.gravatar,
            "Title": self.title,
            "Visibility": self.visibility,
            "UploadTime": self.UploadTime,
        }

        if self.body:
            post["Body"] = self.body

        for x in range(1, 6):
            if getattr(self, f"Image{x}") is not None:
                post[f"Image{x}"] = get_image_url(getattr(self, f"Image{x}"))
        return post


def getPostById(id: str, db) -> Post | None:
    post_info = db.execute(
        "SELECT lp.*, u.Username, u.GravatarURL FROM live_posts lp JOIN Users u ON lp.UserID = u.UserID WHERE lp.PostID = ?",
        (id,),
    ).fetchone() 

    if not post_info:
        return None
    
    post = Post(
        post_info[0],
        post_info[1],
        post_info[11],
        post_info[12],
        post_info[2],
        post_info[3],
        post_info[4],
        post_info[5],
        post_info[6], # Image 1
        post_info[7],
        post_info[8],
        post_info[9],
        post_info[10]
    )

    return post


class User(): 
    def __init__(self, userId: str, username: str, gravatar: str, bio: str, onboarded: bool|None = None, followers: int|None = None, following: int|None = None, is_following: bool = False):
        self.userId = userId
        self.username = username
        self.gravatar = gravatar
        self.onboarded = onboarded
        self.bio = bio
        self.followers = followers
        self.following = following
        self.is_following = is_following


    def getDict(self, db) -> dict:
        posts = db.execute(
            "SELECT lp.*, u.Username, u.GravatarURL FROM live_posts lp JOIN Users u ON lp.UserID = u.UserID WHERE u.Username = ?"
            , (self.username,)
            ).fetchall()
        
        post_list = []
        for post in posts:
            post_list.append(Post(
                post[0], post[1], post[11], post[12], post[2], post[3], post[4], post[5],
                post[6],  post[7], post[8], post[9], post[10]
            ).getDict())

        user = {
            "username": self.username,
            "gravatar": self.gravatar,
            "bio": self.bio,
            "followers": self.followers,
            "following": self.following,
            "is_following": self.is_following,
            "posts": post_list,
        }

        return user
    

def getUserByUsername(username: str, db) -> User | None:
    user_id = db.execute(
        "SELECT UserID FROM users WHERE Username = ?", (username,)
        ).fetchone()
    
    if not user_id:
        return None
    user_id = user_id[0]
    

    query = """
    SELECT GravatarURL as count
    FROM Users 
    WHERE UserID = ?
    UNION ALL
    SELECT COUNT(follower) as count
    FROM followers 
    WHERE followee = ?
    UNION ALL
    SELECT COUNT(followee) as count
    FROM followers
    WHERE follower = ?
    UNION ALL  
    SELECT Bio as count
    FROM users
    WHERE UserID = ?
    UNION ALL 
	SELECT COUNT(*) as count
    FROM followers 
    WHERE followee = ? AND Follower = ?
    """
    user_info = db.execute(
        query,
        (user_id, user_id, user_id, user_id, user_id, g.UserID),
    ).fetchall()

    if not user_info:
        return None

    user = User(user_id, username, user_info[0][0], user_info[3][0], followers=user_info[1][0], following=user_info[2][0], is_following=user_info[4][0] == 1)

    return user 