from uuid import uuid4

from pydantic import BaseModel

from common.metadata import METADATA_USER_ID_KEY, MetadataMixIn
from dbs.mongo import mongo_read, mongo_write


class User(BaseModel, MetadataMixIn):
    @property
    def metadata_key(self) -> str:
        return METADATA_USER_ID_KEY


# TODO: Move over to using user_id when using app
def get_user(user_number, is_cookie=False):
    if is_cookie:
        return mongo_read("Users", {"cookie": user_number})

    return mongo_read("Users", {"number": user_number})


def get_users():
    return mongo_read("Users", {}, find_many=True)


def create_user(user_number, is_cookie=False):
    mongo_write(
        "Users",
        {
            "number": "" if is_cookie else user_number,
            "session_id": "",
            "cookie": user_number if is_cookie else "",
            "user_id": str(uuid4()),
        },
    )
    return mongo_read("Users", {"cookie" if is_cookie else "number": user_number})
