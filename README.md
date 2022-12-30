# Toast Backend
## This repo servers as the backend for the Toast project. 

## Account login and signup
### POST /signup
Request format: 
```
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
```
{
    "username": "username",
    "password": "password"
}
```
Response format:  
If successful:  
If 2FA is enabled:  
```
{
    "session_id": {session_id},
    "message": "Verify 2FA code at /2faVerify"
}
```
If no 2FA:
```
{
    "session_id": {session_id},
    "message": "Logged in"
}
```
If unsuccessful:  
`'Incorrect username or password'`  

