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

def mongo_write_many(collection, entries):
    try:
        result = mongo_db[collection].insert_many(entries)
    except pymongo.errors.OperationFailure:
        print("MONGO WRITE ERROR")
        print(f"Collection: {collection}")
        print(f"Entry: {entries}")
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


def mongo_count(collection, query = None):
    try:
        result = mongo_db[collection].count(query)
    except pymongo.errors.OperationFailure:
        print("MONGO COUNT ERROR")
        print(f"Collection: {collection}")
        print(f"Query: {query}")
        result = None

    print(result)
    return result

def mongo_delete_many(collection, number = 100):
    try:
        to_delete = mongo_db[collection].find().limit(number).sort("createdAt", pymongo.ASCENDING)
        ids_to_delete = []
        for item in to_delete:
            ids_to_delete.append(item["_id"])
        
        print("about to delete")
        print(ids_to_delete)
        result = mongo_db[collection].delete_many({ "_id": { "$in": ids_to_delete } })
        print("deleted")
        print(result)
    except pymongo.errors.OperationFailure:
        print("MONGO DELETE ERROR")
        print(f"Collection: {collection}")
        print(f"Number: {number}")
        result = None

    print(result)
    return result
