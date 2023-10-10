from uuid import uuid4

from pydantic import BaseModel
from pymongo import DESCENDING

from dbs.mongo import mongo_read, mongo_read_sort, mongo_write


def get_user(token, is_number=False):
    if is_number:
        return mongo_read("Users", {"number": token})

    cookie = mongo_read("Cookies", {"cookie": token})
    if cookie is None:
        return None

    user_id = cookie.get("user_id", None)

    if cookie is not None and user_id is not None:
        return mongo_read("Users", {"user_id": user_id})

    return None


def get_users():
    return mongo_read("Users", {}, find_many=True)


def get_top_users(limit=100):
    sortFilter = [("Votes", DESCENDING)]
    return mongo_read_sort("Users", {"images_generated": True, "active": { "$exists": False }}, sortFilter, limit=limit)


def create_user(number):
    mongo_write(
        "Users",
        {
            "number": number,
            "cookie": str(uuid4()),
            "user_id": str(uuid4()),
        },
    )
    return mongo_read("Users", {"number": number})
