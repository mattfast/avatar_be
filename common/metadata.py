import numbers
from abc import abstractmethod
from copy import deepcopy

from pydantic import BaseModel

METADATA_ENTITY_KEY = "entity_ids"
METADATA_USER_ID_KEY = "user_id"
METADATA_MEMORY_TYPE_KEY = "memory_type"
METADATA_INSERT_TIME_KEY = "insertion_time"
METADATA_ACCESSED_KEY = "last_accessed"
METADATA_SESSION_ID_KEY = "session_id"
METADATA_KEYWORDS_KEY = "keywords"
METADATA_CONTENT_KEY = "content"
METADATA_MESSAGE_ID_KEY = "message_id"


DEFAULT_REQUIRED_INSERTION_KEYS = {
    METADATA_ENTITY_KEY,
    METADATA_USER_ID_KEY,
    METADATA_INSERT_TIME_KEY,
    METADATA_MEMORY_TYPE_KEY,
    METADATA_SESSION_ID_KEY,
    METADATA_ACCESSED_KEY,
    METADATA_CONTENT_KEY,
    METADATA_MESSAGE_ID_KEY,
}

## Insertion Metadata for Pinecone ##
## {"user_id": str, "entity_ids": list[str], memorytype: str, session_id: str,
# timeinserted: timestamp (seconds), lastaccesed: timestamp (seconds), keywords: [list]} ##

## Query Metadata for Pinecone ##
## {user_id: "eq": value, entity_ids: int value, memory_type "eq" value,
# session_id "eq" value, lastaccessed $gt value, keywords $in value}, ##


class MetadataMixIn:
    @property
    def metadata_key(self) -> str:
        return ""

    @abstractmethod
    def modify_metadata_dict(self, metadata: dict) -> dict:
        return {}


class Metadata(BaseModel):

    metadata_dict: dict = {}
    required_insert: set = DEFAULT_REQUIRED_INSERTION_KEYS

    def kv_add(self, key, value):
        self.metadata_dict[key] = value

    def add(self, mixin: MetadataMixIn):
        self.metadata_dict = mixin.modify_metadata_dict(deepcopy(self.metadata_dict))

    def format_for_insertion(self, validate=True):
        """Format for insertion."""
        if validate:
            req_key_diff = self.required_insert - set(self.metadata_dict.keys())
            if len(req_key_diff) > 0:
                raise ValueError(f"Missing Required Insertion Keys {req_key_diff}")
        return self.metadata_dict

    def format_for_retrieval(self, **kwargs):
        """Format for retrieval. Default is pinecone."""
        filter = {}
        defined_filters = kwargs.get("filters", {})
        for key, val in self.metadata_dict.items():
            if key in defined_filters:
                filter[key] = defined_filters[key]
            elif isinstance(val, str) or isinstance(val, numbers.Number):
                filter[key] = {"$eq": val}
            elif isinstance(val, list):
                filter[key] = {"$in": val}
        return filter
