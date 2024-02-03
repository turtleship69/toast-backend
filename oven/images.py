# blueprint to serve images from /content/images
#THIS SHOULD ONLY BE USED AS A FALLBACK - USE A PROPER CDN
from flask import Blueprint, send_from_directory


bp = Blueprint('images', __name__, url_prefix="images")

@bp.route('/<path:filename>')
def serve_image(filename):
    return send_from_directory('images', filename)