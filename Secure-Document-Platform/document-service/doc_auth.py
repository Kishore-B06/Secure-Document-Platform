from jose import JWTError, jwt
from fastapi import HTTPException
from dotenv import load_dotenv
import os

# Load .env from document-service folder
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

if SECRET_KEY:
    SECRET_KEY = SECRET_KEY.strip()
if ALGORITHM:
    ALGORITHM = ALGORITHM.strip()

if not SECRET_KEY or not ALGORITHM:
    raise Exception("SECRET_KEY or ALGORITHM not loaded from .env")


def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role", "user")  # default role

        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        return {"username": username, "role": role}

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")