"""this module contains various functions used throughout the project"""

import hashlib
import os
from typing import Literal
import requests
from .config import HANKO_API_URL
def gravatar(email, size=""):
    url = f"https://www.gravatar.com/avatar/{hashlib.md5(email.lower().encode('utf-8')).hexdigest()}"
    if size:
        url += f"?s={size}"
    return url

def getGravatarFromHankoJwt(hankoId: str):
    #make a request to /emails with the provided jwt and get the users email
    #then use the email to get the gravatar
    headers = {
        "Authorization": f"Bearer {hankoId}"
    }
    response = requests.get(f"{HANKO_API_URL}/emails", headers=headers)
    print(response.text)
    if response.status_code == 200:
        email = response.json()[0]["address"]
        return gravatar(email)
    else:
        raise Exception("Error getting email from Hanko")


#UUIDs
from uuid import uuid4
def generate_session_id():
    return str(uuid4())


#accessing the database
import sqlite3 
from flask import current_app, g
from .config import DATABASE
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()

class User():
    def __init__(self, id, username, GravatarURL, Onboarded, profilePicture):
        self.id = id
        self.username = username
        self.GravatarURL = GravatarURL
        self.Onboarded = Onboarded
        self.profilePicture = profilePicture




 
import PIL
from PIL import Image
import numpy as np
import cv2
import io
import json
from .config import image_dir

"""these functions deal with compressing (and encoding) images after they have been
    processed by the image processing module"""
# def get_opencv_img_from_buffer(buffer, flags):
#     bytes_as_np_array = np.frombuffer(buffer.read(), dtype=np.uint8)
#     return cv2.imdecode(bytes_as_np_array, flags)
def compress_image(image: io.BytesIO, quality=60) -> tuple[io.BytesIO, str]:
    """compresses the image and returns the compressed image"""
    img = cv2.imdecode(np.frombuffer(image.read(), dtype=np.uint8), cv2.IMREAD_COLOR)

    type = "gif" if img.ndim == 4 else "jpg"
    if type == "jpg":
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        result, encimg = cv2.imencode('.jpg', img, encode_param)
    else: 
        #compress gif but maintain transparency
        gif_quality = 60
        # encode_param = [int(cv2.IMWRITE_GIF_QUALITY), gif_quality]
        # result, encimg = cv2.imencode('.gif', img, encode_param)
    #convert to bytesio
    compressed_image = io.BytesIO(encimg) # type: ignore
    return compressed_image, type

#function so it can be adapted in future
def save_image(image, UserID: str, filename: str, PostID: str, postTime: int, public: bool):
    animated = False
    processed_image = Image.open(image)
    print(processed_image.format)

    if processed_image.format == "GIF":
        filename+=".gif"
        processed_image.save(f"{image_dir}/{filename}", quality=60, save_all=True)
        animated = True
    else:
        filename+=".png"
        processed_image.save(f"{image_dir}/{filename}", quality=60,)
        
    print(filename)
    g.db.execute(
                'INSERT INTO images (UserID, ImageURI, PostID, UploadDate, Public, Animated) VALUES (?, ?, ?, ?, ?, ?)',
                (UserID, filename, PostID, postTime, int(public), animated)
            )
    return filename

#function so it can be adapted before deployment
def cv_save_image(image, UserID: str, filename: str, PostID: str, postTime: int, public: Literal[0, 1]):
    compressed_image, type = compress_image(image)
    path = f"{image_dir}/{filename}.{type}"
    with open(path, 'wb') as f:
        f.write(compressed_image.getbuffer())
    g.db.execute(
                'INSERT INTO images (UserID, ImageURI, PostID, UploadDate, Public) VALUES (?, ?, ?, ?, ?)',
                (UserID, filename, PostID, postTime, public)
            )
    return path

def get_image_url(filename: str):
    return f"/images/{filename}"


#load image
""" if __name__ == '__main__':
    #open image as bytesio
    image = io.BytesIO(open('test3.jpg', 'rb').read())
    #compress image
    compressed_image = compress_image(image)
    #save the bytesio to a file
    with open('compressed 3.jpg', 'wb') as f:
        f.write(compressed_image.getvalue())
     """



def addToArchive(UserID: str, Post: dict):
    #get the json file, and add the newest post to it at the end
    filename = f'content/archives/{UserID}.json'

    if not os.path.exists(filename):
        data = {}
    else: 
        with open(filename) as f:
            data = json.load(f)

    data[Post['PostID']] = Post

    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)
