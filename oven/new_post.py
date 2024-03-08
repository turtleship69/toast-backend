import time
from flask import Blueprint, g, request, jsonify

from .models import getPostById
from .hanko import login_required
from .tools import addToArchive, save_image, addToArchive

from uuid import uuid4
from pprint import pprint

bp = Blueprint('submit', __name__, url_prefix="/new_post")

# 0 = Only Me
# 1 = Only Friends
# 2 = Everyone


@bp.route('/new', methods=['POST'])
@login_required
def upload():
    postTime = int(time.time())
    error = None

    #validate form
    if not request.form.get('title'):
        error = 'Title is required'
    elif not request.form.get('privacy') in ["0", "1", "2"]:
        error = 'Invalid privacy setting'
        print(request.form.get('privacy'))
    
    if error: 
        response = {
            'status': 'error',
            'message': error
        }
        pprint(response)
        return jsonify(response)

    pprint(request.form)
    
    UserID = g.UserID
    print(UserID)

    PostID = str(uuid4())
    post = {
        'PostID': PostID,
        'UserID': UserID, 
        "title": request.form.get('title'),
        "Visibility": request.form.get('privacy'),
        "UploadTime": postTime,
    } 

    if request.form.get('body'):
        post['body'] = request.form.get('body')

    public = True if request.form.get('privacy') == "2" else False

    imagesToInsert = 0
    imagesToInsertCommand = ""
    imagesToInsertNames = []
    for x in range(1, 6):
        if request.files.get(f'image{x}'):
            print(f"flag d {x}")
            name = str(uuid4())
            # compressedImage = compress_image(request.files[f'image{x}'])
            filename = save_image(request.files[f'image{x}'], UserID, name, PostID, postTime, public)
            
            post[f'image{x}'] = filename
            imagesToInsertCommand += f', Image{x}'
            imagesToInsert += 1
            imagesToInsertNames.append(filename)
        else:
            break


    # make post
    stringToExecute = 'INSERT INTO live_posts (PostID, UserID, Title, Visibility, UploadTime'
    if request.form.get('body'):
        stringToExecute += ', Body'
    stringToExecute += imagesToInsertCommand
    

    stringToExecute += ') VALUES (?, ?, ?, ?, ?'
    if request.form.get('body'):
        stringToExecute += ', ?'
    for x in range(1, imagesToInsert + 1):
        stringToExecute += ', ?'
    stringToExecute += ')'

    stringToExecuteValues = [PostID, UserID, post['title'], post['Visibility'], post['UploadTime']]
    if request.form.get('body'):
        stringToExecuteValues.append(post['body'])
    stringToExecuteValues.extend(imagesToInsertNames)
        
    print(f"command: {stringToExecute}")
    print(f"values: {stringToExecuteValues}")
    g.db.execute(stringToExecute, stringToExecuteValues)

    # make archive
    addToArchive(UserID, post)

    return jsonify({"status": "success", "message": "Post saved", "id": PostID})

@bp.route('/delete/<id>')
@login_required
def delete(id):
    post = getPostById(id)
    error = None
    if not post:
        error = "Post not found"
    elif post.poster_id != g.UserID:
        error = "Not your post"

    if error:
        response = {
            'status': 'error',
            'message': error
        }
        return jsonify(response)
    else:
        g.db.execute("DELETE FROM live_posts WHERE PostID = ?", (id,))
        return jsonify({"status": "success", "message": "Post deleted"})