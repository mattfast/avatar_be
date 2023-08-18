import pymongo

from dbs import mongo_db


def mongo_write(collection, entry):
    try:
        result = mongo_db[collection].insert_one(entry)
    except pymongo.errors.OperationFailure:
        print("MONGO WRITE ERROR")
        print(f"Collection: {collection}")
        print(f"Entry: {entry}")
        result = None

    print(result)
    return result


def mongo_upsert(collection, query, update):
    try:
        result = mongo_db[collection].update_one(query, {"$set": update}, upsert=True)
    except pymongo.errors.OperationFailure:
        print("MONGO UPDATE ERROR")
        print(f"Collection: {collection}")
        print(f"Query Param: {query}")
        print(f"Update Param: {update}")
        result = None

    print(result)
    return result


def mongo_read(collection, filter, find_many: bool = False):

    try:
        print("ABOUT TO FIND RESULT")
        print(mongo_db)
        print(mongo_db[collection])
        if not find_many:
            result = mongo_db[collection].find_one(filter)
        else:
            result = mongo_db[collection].find(filter)
        print("FOUND RESULT")
    except pymongo.errors.OperationFailure:
        print("MONGO READ ERROR")
        print(f"Collection: {collection}")
        print(f"Filter: {filter}")
        result = None

    return result
