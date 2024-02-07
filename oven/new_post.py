import json
import time, re
from flask import Blueprint, g, request, jsonify, make_response
from .hanko import login_required
from .tools import addToArchive, get_db, compress_image, save_image, addToArchive, get_image_url

from uuid import uuid4
from pprint import pprint
from datetime import datetime


bp = Blueprint('submit', __name__, url_prefix="/new_post")

# 0 = Only Me
# 1 = Only Friends
# 2 = Everyone


@bp.route('/postold', methods=['POST'])
@login_required
def uploadold():
    """
    request object:
    {
        session_id: {{ session_id }}, # optional, if not in cookies
        image1Visibility: {{ image1Visibility }}, # 0-2
        image1: {{ image1 }},
        image2Visibility: {{ image2Visibility }}, # 0-2
        image2: {{ image2 }},
        image3Visibility: {{ image3Visibility }}, # 0-2
        image3: {{ image3 }},
        image4Visibility: {{ image4Visibility }}, # 0-2
        image4: {{ image4 }},
        image5Visibility: {{ image5Visibility }}, # 0-2
        image5: {{ image5 }},
        caption0: {{ caption0 }}, 
        caption1: {{ caption1 }}, 
        caption2: {{ caption2 }} 
    }
    """
    db = get_db()
    error = None
    # get session from cookies or if not in cookies, get from request body
    session_id = g.session_id
    UserID = g.user[1]
    print(f"UserID: {UserID}\tSessionID: {session_id}")
    # check if user already has a post today, if so, return post id
    today = db.cursor().execute('SELECT * FROM archive WHERE UserID = ? AND Date LIKE ?', (UserID, datetime.now().strftime("%Y-%m-%d") + "%")).fetchone()
    if today is not None:
        response  = {
            'status': 'error',
            'message': 'You already have a post today',
        }
        return make_response(jsonify(response), 400)
    # check if there are any images, if not, just save the caption
    # save to table archive("PostID", "UserID", "Date", "Image1", "Image2", "Image3", "Image4", "Image5", "Caption")
    # PostID is a random uuid
    # UserID is the UserID of the user who uploaded the post
    # Date is the current date using datetime("now")
    # Images is the number 
    # Caption is the caption of the post
    # save to table images("UserID", "ImageURI", "PostID", "UploadDate")
    

    pprint(request.form)
    
    archiveEntry = {
        'EntryID': str(uuid4()),
        'UserID': UserID,
        'Caption': '',
        'images': []
    }

    if request.form.get('caption0'):
        archiveEntry['Caption'] += f"Only visible for you: {request.form['caption0']}\n"
    if request.form.get('caption1'):
        archiveEntry['Caption'] += f"Only visible for your friends: {request.form['caption1']}\n"
    if request.form.get('caption2'):
        archiveEntry['Caption'] += f"Visible for everyone: {request.form['caption2']}"
    pprint(archiveEntry)

    OFpost = {
        'PostID': str(uuid4()),
        'UserID': UserID, 
        'caption': request.form.get('caption1'),
        'images': []
    }
    Epost = {
        'PostID': str(uuid4()),
        'UserID': UserID, 
        'caption': request.form.get('caption2'),
        'images': []
    }
    posts = [None, "OFpost", "Epost"]
    #pprint(post)

    images = [None, [], [], [], [], []]

    #check how many images are being uploaded, and that there are no gaps in the numbering
    #compress and save image, then save the name of the image to the database
    if request.files.get('image1'):
        name = str(uuid4())
        compressedImage = compress_image(request.files['image1'])
        save_image(compressedImage, name)
        images[1] = [request.form['image1Visibility'], name]
        if request.form['image1Visibility'] == '0':
            archiveEntry['images'].append(name)
        elif request.form['image1Visibility'] == '1':
            OFpost['images'].append(name)
        elif request.form['image1Visibility'] == '2':
            Epost['images'].append(name)
    if request.files.get('image2'):
        name = str(uuid4())
        compressedImage = compress_image(request.files['image2'])
        save_image(compressedImage, name)
        images[2] = [request.form['image2Visibility'], name]
        if request.form['image1Visibility'] == '0':
            archiveEntry['images'].append(name)
        elif request.form['image1Visibility'] == '1':
            OFpost['images'].append(name)
        elif request.form['image1Visibility'] == '2':
            Epost['images'].append(name)
    if request.files.get('image3'):
        name = str(uuid4())
        compressedImage = compress_image(request.files['image3'])
        save_image(compressedImage, name)
        images[3] = [request.form['image3Visibility'], name]
        if request.form['image1Visibility'] == '0':
            archiveEntry['images'].append(name)
        elif request.form['image1Visibility'] == '1':
            OFpost['images'].append(name)
        elif request.form['image1Visibility'] == '2':
            Epost['images'].append(name)
    if request.files.get('image4'):
        name = str(uuid4())
        compressedImage = compress_image(request.files['image4'])
        save_image(compressedImage, name)
        images[4] = [request.form['image4Visibility'], name]
        if request.form['image1Visibility'] == '0':
            archiveEntry['images'].append(name)
        elif request.form['image1Visibility'] == '1':
            OFpost['images'].append(name)
        elif request.form['image1Visibility'] == '2':
            Epost['images'].append(name)
    if request.files.get('image5'):
        name = str(uuid4())
        compressedImage = compress_image(request.files['image5'])
        save_image(compressedImage, name)
        images[5] = [request.form['image5Visibility'], name]
        if request.form['image1Visibility'] == '0':
            archiveEntry['images'].append(name)
        elif request.form['image1Visibility'] == '1':
            OFpost['images'].append(name)
        elif request.form['image1Visibility'] == '2':
            Epost['images'].append(name)
    #insert into database table images (UserID, ImageURI, PostID, UploadDate)
    scriptToExecute = 'INSERT INTO images (UserID, ImageURI, PostID, UploadDate) VALUES (?, ?, ?, datetime("now"))'
    scriptToExecuteValues = []
    
    for x in range(1, 6):
        if images[x]:
            if images[x][0] == '0':
                scriptToExecuteValues.append((UserID, images[x][1], None))
            elif images[x][0] == '1':
                scriptToExecuteValues.append((UserID, images[x][1], OFpost['PostID']))
            elif images[x][0] == '2':
                scriptToExecuteValues.append((UserID, images[x][1], Epost['PostID']))
            else:
                raise RuntimeError("Invalid image visibility")
    db.cursor().executemany(scriptToExecute, scriptToExecuteValues)


    #live_posts("PostID", "UserID", "Visibility", "Image1", "Image2", "Image3", "Image4", "Image5", "Caption", "UploadTime")
    #visiblity: 1 = Only Friends, 2 = Everyone
    # if applicable, make a post visible for friends
    OF = True if OFpost['caption'] or OFpost['images'] else False
    if OF:
        stringToExecute = 'INSERT INTO live_posts (PostID, UserID, Visibility, '
        for x in range(1, 6):
            if images[x]:
                stringToExecute += f'Image{x}, ' if images[x][0] == '1' else ''
        stringToExecute += 'Caption, UploadTime) VALUES (?, ?, 1, '
        for x in range(1, 6):
            if images[x]:
                stringToExecute += '?, ' if images[x][0] == '1' else ''
        stringToExecute += '?, datetime("now"))'
        print(stringToExecute)
        db.cursor().execute(stringToExecute, (OFpost['PostID'], UserID, *OFpost['images'], OFpost['caption']))

    # if applicable, make a post visible for everyone
    E = True if Epost['caption'] or Epost['images'] else False
    if E:
        stringToExecute = 'INSERT INTO live_posts (PostID, UserID, Visibility, '
        for x in range(1, 6):
            if images[x]:
                stringToExecute += f'Image{x}, ' if images[x][0] == '2' else ''
        stringToExecute += 'Caption, UploadTime) VALUES (?, ?, 2, '
        for x in range(1, 6):
            if images[x]:
                stringToExecute += '?, ' if images[x][0] == '2' else ''
        stringToExecute += '?, datetime("now"))'
        print(stringToExecute)
        db.cursor().execute(stringToExecute, (Epost['PostID'], UserID, *Epost['images'], Epost['caption']))
    
    # make an archive entry
    #archive table is as follows: EntryID, UserID, Date, Image1, Image2, Image3, Image4, Image5, Caption
    stringToExecute = 'INSERT INTO archive (EntryID, UserID, Date, Caption, '
    #add images to the archive entry
    for x in range(1, 6):
        if images[x]:
            stringToExecute += f'Image{x}, '
    stringToExecute = stringToExecute[:-2] + ') VALUES (?, ?, datetime("now"), ?, '
    for x in range(1, 6):
        if images[x]:
            stringToExecute += '?, '
    stringToExecute = stringToExecute[:-2] + ')'
    print(stringToExecute)
    db.cursor().execute(stringToExecute, (archiveEntry['EntryID'], UserID, archiveEntry['caption'], *archiveEntry['images']))
    db.commit()
    print("post saved")
    PostIDs = {'OF': None, 
               'E': None, 
               'A': archiveEntry['EntryID']}
    if OFpost['caption'] or OFpost['images']:
        PostIDs['OF'] = OFpost['PostID']
    else:
        del PostIDs['OF']
    if Epost['caption'] or Epost['images']:
        PostIDs['E'] = Epost['PostID']
    else:
        del PostIDs['E']

    response = {
        'status': 'success',
        'message': 'Post(s) saved',
        'IDs': PostIDs
    }
    return jsonify(response)


@bp.route('/new', methods=['POST'])
@login_required
def upload():
    print("flag c")


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


    db = get_db()
    
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
    if request.form.get('privacy') != "0":
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
        db.execute(stringToExecute, stringToExecuteValues)

    # make archive
    addToArchive(UserID, post)


    db.commit()
    return jsonify({"status": "success", "message": "Post saved", "id": PostID})

