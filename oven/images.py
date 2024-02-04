# blueprint to serve images from /content/images
#THIS SHOULD ONLY BE USED AS A FALLBACK - USE A PROPER CDN
from flask import Blueprint, make_response, send_from_directory
from flask import make_response
from os import path, getcwd

bp = Blueprint('images', __name__, url_prefix="/images")

@bp.route('/<path:filename>')
def serve_image(filename):
    image = send_from_directory(path.join(getcwd(), 'content/images'), filename)
    image.headers['Cache-Control'] = 'public, max-age=604800' # one week
    image.headers['Netlify-CDN-Cache-Control'] = 'public, max-age=604800' # one week
    image.headers['Content-Type'] = 'image/jpeg'
    return image