import sys

import certifi
import pymongo
import pinecone
from keys import mongo_key, pinecone_key

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
