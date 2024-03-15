# blueprint to serve images from /content/images
#THIS SHOULD ONLY BE USED AS A FALLBACK - USE A PROPER CDN
from flask import Blueprint, make_response, send_from_directory
from flask import make_response
from os import path, getcwd

from .cache import cache

bp = Blueprint('images', __name__, url_prefix="/images")

@bp.route('/<path:filename>')
@cache(60 * 60 * 24)
def serve_image(filename):
    image = make_response(send_from_directory(path.join(getcwd(), 'content/images'), filename))
    image.headers['Content-Type'] = 'image/jpeg'
    return image