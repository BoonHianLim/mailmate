import json
import logging
import os

import src.repo.auth as auth

logger: logging.Logger = logging.getLogger('uvicorn.error')

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
GRANDPARENT_DIR = os.path.dirname(PARENT_DIR)

class DBObject:
    user_tokens = {}
    def __init__(self):
        pass

db = DBObject()

def get_user_tokens(key):
    """ Returns the user tokens """
    return db.user_tokens.get(key, None)

def set_user_tokens(key, value):
    """ Sets the user tokens """
    db.user_tokens[key] = value

def save_user_tokens(filename="user_tokens.json"):
    with open(os.path.join(GRANDPARENT_DIR, filename), "w") as f:
        json.dump(db.user_tokens, f)
    logger.info("User tokens saved successfully.")


def load_user_tokens(filename="user_tokens.json"):
    try:
        with open(os.path.join(GRANDPARENT_DIR, filename), "r") as f:
            db.user_tokens = json.load(f)
        logger.info("User tokens loaded successfully.")
    except FileNotFoundError:
        db.user_tokens = {}
        logger.warning(
            f"File {filename} not found. Starting with an empty user tokens dictionary.")
