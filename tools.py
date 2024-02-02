"""this module contains various functions used throughout the project"""

import hashlib
def gravatar(email, size=200):
    return f"https://www.gravatar.com/avatar/{hashlib.md5(email.lower().encode('utf-8')).hexdigest()}?s={size}"

#UUIDs
from uuid import uuid4
def generate_session_id():
    return str(uuid4())

"""accessing the database"""
import sqlite3 
from flask import current_app, g
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db

def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()


import PIL
from PIL import Image
import numpy as np
import cv2
import io

"""these functions deal with compressing (and encoding) images after they have been
    processed by the image processing module"""
def get_opencv_img_from_buffer(buffer, flags):
    bytes_as_np_array = np.frombuffer(buffer.read(), dtype=np.uint8)
    return cv2.imdecode(bytes_as_np_array, flags)
def compress_image(image):
    """compresses the image and returns the compressed image"""
    img = get_opencv_img_from_buffer(image, cv2.IMREAD_COLOR)
    #get image size
    height, width, channels = img.shape
    #encode image
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
    result, encimg = cv2.imencode('.jpg', img, encode_param)
    #convert to bytesio
    compressed_image = io.BytesIO(encimg) # type: ignore
    return compressed_image

#load image
if __name__ == '__main__':
    #open image as bytesio
    image = io.BytesIO(open('test3.jpg', 'rb').read())
    #compress image
    compressed_image = compress_image(image)
    #save the bytesio to a file
    with open('compressed 3.jpg', 'wb') as f:
        f.write(compressed_image.getvalue())
    
