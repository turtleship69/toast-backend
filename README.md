# Toast Backend
## This repo servers as the backend for the Toast project. 

## Account login and signup
### POST /signup
Request format: 
```json
{
    "username": "username",
    "email": "email",
    "phone": "phone",
    "password": "password"
}
```
Response format:  
If successful:  
`'Signed up successfully'`  
Otherwise one of the following:  
`'Username already taken'`  
`'Email already taken'`  
`'Phone already taken'`  

### POST /login
request format:  
```json
{
    "username": {username},
    "password": {password}
}
```
Response format:  
If successful:  
If 2FA is enabled:  
```json
{
    "session_id": {session_id}, #optional, or use cookie
    "message": "Verify 2FA code at /2faVerify"
}
```
If no 2FA:
```json
{
    "session_id": {session_id},
    "message": "Logged in"
}
```
If unsuccessful:  
```json
{
    "status": "error",
    "message": "Incorrect username or password"
}
```

### POST /2faVerify
request format:  
```json
{
    "session_id": {session_id}, #optional, or use cookie
    "code": {code}
}
```
Response format:
If successful:  
```json
{
    "session_id": {session_id},
    "message": "2FA verified successfully"
}
```
If unsuccessful:  
```json
{
    "status": "error",
    "message": "Incorrect 2FA code" or "2FA not enabled"
}
```

## ENABLING 2FA
### POST /2faEnable
To enable 2FA, there are two steps. 
For either step, if session_id is not provided or invalid, the following response will be returned:
```json
{
    "status": "error",
    "message": "Session does not exist"
}
```
If 2FA is already enabled, the following response will be returned:
```json
{
    "status": "error",
    "message": "2FA already enabled"
}
```
First, you need to verify your identity. This is done by sending a POST request to /2faEnable with the following request format:
```json
{
    "step": 0,
    "session_id": {session_id}, #optional, or use cookie
    "password": {password}
}
```
If the correct password for the account is not provided, the following response will be returned:
```json
{
    "status": "error",
    "message": "Incorrect password"
}
```
If the session and password are correct, the following response will be returned:
```json
{
    "status": "success",
    "message": "proceed to step 1",
    "url": {url}
}
```
The url is what the user needs to scan with their 2FA app. Generate a QR code for the user to scan. The user will then be prompted to enter a code. The code is then sent to the backend with the following request format:
```json
{
    "step": 1,
    "session_id": {session_id}, #optional, or use cookie
    "code": {code}
}
```
If the code is incorrect, the following response will be returned:
```json
{
    "status": "error",
    "message": "Incorrect 2FA code, try again"
}
```
If the code is correct, the following response will be returned:
```json
{
    "status": "success",
    "message": "2FA enabled successfully"
}
```

## UPLOAD
### POST /upload
```json
request object:
{
    session_id: {{ session_id }}, # optional, if not in cookies
    noOfImages: {{ number }}, # 0-5
    image1Visiblity: {{ image1Visibility }}, # 0-2
    image2Visiblity: {{ image2Visibility }}, # 0-2
    image3Visiblity: {{ image3Visibility }}, # 0-2
    image4Visiblity: {{ image4Visibility }}, # 0-2
    image5Visiblity: {{ image5Visibility }}, # 0-2
    image1: {{ image1 }},
    image2: {{ image2 }},
    image3: {{ image3 }},
    image4: {{ image4 }},
    image5: {{ image5 }},
    caption0: {{ caption0 }}, # optional
    caption1: {{ caption1 }}, # optional
    caption2: {{ caption2 }} # optional
}
```
Visibility: 0 Only visible to user, 1 Visible to user and friends, 2 Visible to everyone
session_id: the session_id of the user, can alternatively be in the cookies
noOfImages: the number of images to upload, 0-5
image`x`Visibility: the visibility of image`x`1, 0-2
image`x`: the image to upload
caption`y`: captions with varying visibility, optional. Anyone can see caption 2, only friends can see caption 1, only user can see caption 0

If the user has already posted today:
```json
{
    "status": "not uploaded", 
    "message": "You already have a post today",
    "postID": {postID} # the postID of the post that was already uploaded
}
```
If successful:
```json
{
    "status": "uploaded",
    "message": "Post uploaded successfully",
    "postID": {postID}
}
```

## FOLLOWING
### POST /follow
```json
{
    "session_id": {session_id}, #optional, or use cookie
    "userToFollow": {username},
    "level": {level} # 1 for follow, 2 for friend (request will be sent) 
}
```
FRIEND REQUESTS HAVE NOT BEEN IMPLEMENTED YET, only follow. Level 2 will return an error. 
If the user doesn't exist:
```json
{
    "status": "error",
    "message": "User does not exist"
}
```
If the user is already followed:
```json
{
    "status": "error",
    "message": "You are already following this user"
}
```
If successful:
```json
{
    "status": "success",
    "message": "You are now following {userToFollow}"
}
```

### POST /unfollow
```json
{
    "session_id": {session_id}, #optional, or use cookie
    "userToUnfollow": {username}
}
```
If the user is not following the user:
```json
{
    "status": "error",
    "message": "You are not following {userToUnfollow}"
}
```
If successful:
```json
{
    "status": "success",
    "message": "You are no longer following {userToUnfollow}"
}
```

## GET or POST /following
request object
```json
{
    "session_id": {session_id}, #optional, or use cookie
}
```
If a get request is used, `session_id` must be in the cookies. If a post request is used, `session_id` can be in the cookies or in the request object.
responce object if post request is used:
```json
{
    "status": "success",
    "message": "you are following {{number of users}} users",
    "number": {{number of users}},
    "users": [
        {
            "username": {{ username }},
            "level": {{ level }} #1 = follow, 2 = friend
        },
        ...
    ]
}
```

## GET or POST /followers
request object if post request is used:
```json
{
    "session_id": {session_id}, #optional, or use cookie
}
```
If a get request is used, `session_id` must be in the cookies. If a post request is used, `session_id` can be in the cookies or in the request object.
responce object if post request is used:
```json
{
    "status": "success",
    "message": "{{username}} is followed by {{number of users}} users",
    "number": {{number of users}},
    "users": [
        {
            "username": {{ username }},
            "level": {{ level }} #1 = follow, 2 = friend
        },
        ...
    ]
}
```