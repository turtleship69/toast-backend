from datetime import datetime
from flask import Flask
from os import urandom

def create_app():
    app = Flask(__name__)
    if app.debug:
        app.config['SECRET_KEY'] = 'secret'
    else:
        app.config['SECRET_KEY'] = urandom(24)

    # main page and server uptime
    startTime = datetime.now()
    @app.route('/')
    def index():
        return f"Server running for {datetime.now() - startTime}"

    # from . import auth
    # app.register_blueprint(auth.bp)

    from . import new_post
    app.register_blueprint(new_post.bp)

    from . import get_posts
    app.register_blueprint(get_posts.bp)

    from . import hanko
    app.register_blueprint(hanko.bp)

    from . import friendships
    app.register_blueprint(friendships.bp)

    from . import images
    app.register_blueprint(images.bp)

    from . import notifs
    app.register_blueprint(notifs.bp)

    return app