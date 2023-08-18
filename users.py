from dbs.mongo import mongo_read, mongo_write


def get_user(user_number):
    return mongo_read("Users", {"number": user_number})


def create_user(user_number):
    mongo_write("Users", {"number": user_number, "session_id": ""})
    return mongo_read("Users", {"number": user_number})