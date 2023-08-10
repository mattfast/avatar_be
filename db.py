import sys

import pymongo
import pinecone
import certifi
from keys import pinecone_key, mongo_key

# init mongodb
print(mongo_key)
mongo_conection_string = f"mongodb+srv://matthew:{mongo_key}@cluster0.4exrr9f.mongodb.net/?retryWrites=true&w=majority"
try:
    client = pymongo.MongoClient(mongo_conection_string, tlsCAFile=certifi.where())
except pymongo.errors.ConfigurationError:
    print(
        "An Invalid URI host error was received. Is your Atlas host name correct in your connection string?"
    )
    sys.exit(1)
else:
    print("MONGO CLIENT")
    print(client)
mongo_db = client["Prod"]

# init pinecone db
pinecone.init(api_key=pinecone_key, environment="gcp-starter")
pinecone_index = pinecone.Index("test-index")
print("PINECONE INDEX")
print(pinecone_index)

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

def mongo_read(collection, filter):

    try: 
        print("ABOUT TO FIND RESULT")
        print(mongo_db)
        print(mongo_db[collection])
        result = mongo_db[collection].find_one(filter)
        print("FOUND RESULT")
        print(result)
    except pymongo.errors.OperationFailure:
        print("MONGO READ ERROR")
        print(f"Collection: {collection}")
        print(f"Filter: {filter}")
        result = None
    
    return result

