from fastapi import Depends, Request, HTTPException


def require_auth(request: Request):
    token = request.cookies["key"]
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return token
