import threading
from copy import deepcopy
from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel

from common.metadata import METADATA_ENTITY_KEY, MetadataMixIn
from dbs.mongo import mongo_read, mongo_upsert


class RelationshipType(Enum):
    """Relationship types."""

    MOTHER = "mother"
    FATHER = "father"
    SIBLING = "sibling"
    GRANDPARENT = "grandparent"
    AUNT = "aunt"
    UNCLE = "uncle"
    COUSIN = "cousin"
    GENERAL_FAMILY = "general family member"
    FRIEND = "friend"
    CLOSE_FRIEND = "close friend"
    ACQUAINTANCE = "acquaintance"
    GENERIC = "generic"


relationship_list = set([r.value for r in RelationshipType])

MAX_CORE_MEMORIES = 5
# TODO: add segmenting of type of memories each person has

entity_format_str = """Information about {name}:

Relationship: {relationship}
{name} Personality: {personality}
Core sentiment towards {name}: {core_sentiment}
"""

RELATIONSHIP_KEY = "relationship"
PERSONALITY_KEY = "personality"
SENTIMENT_KEY = "sentiment"

UPDATE_COUNT_THRESHOLD = 5

default_user_reflection_dict = {
    RELATIONSHIP_KEY: RelationshipType.GENERIC,
    SENTIMENT_KEY: "neutral",
}


class Entity(BaseModel, MetadataMixIn):
    """Class for Entity. To Mirror Mongo."""

    entity_id: str
    """Entity ID."""

    user_id: str

    names: List[str] = []
    """Should map to entity name key."""

    info_dict: dict = {
        PERSONALITY_KEY: "unknown",
    }
    """Information about the entity."""

    related_entities: List[str] = []
    """Related Entity IDs."""

    user_reflection_dict = default_user_reflection_dict
    """Dictionary to reference for reflection."""

    mentions: int = 0

    created_at: datetime = datetime.now()

    last_updated: datetime = datetime.now()

    @classmethod
    def create_new(
        cls,
        name,
        user_id: str,
        relationship: RelationshipType = RelationshipType.GENERIC,
    ):
        entity_id = str(uuid4())
        user_reflection_dict = default_user_reflection_dict
        user_reflection_dict.update({RELATIONSHIP_KEY: relationship})
        return cls(
            entity_id=entity_id,
            user_id=user_id,
            names=[name],
            user_reflection_dict=user_reflection_dict,
        )

    @classmethod
    def from_entity_id(cls, entity_id: str):
        if entity_id is None:
            raise ValueError("EntityID provided is None")

        entity = mongo_read("Entity", {"entity_id": entity_id})
        if entity is None:
            raise ValueError(f"Entity ID {entity_id} not found in Mongo")
        user_reflection_dict = entity["reflection_dict"]
        user_reflection_dict[RELATIONSHIP_KEY] = RelationshipType(
            user_reflection_dict.get(RELATIONSHIP_KEY, RelationshipType.GENERIC.value)
        )
        return cls(
            entity_id=entity["entity_id"],
            user_id=entity["user_id"],
            names=entity["names"],
            info_dict=entity["info_dict"],
            created_at=entity["created_at"],
            user_reflection_dict=user_reflection_dict,
        )

    def convert_reflection_dict_for_mongo(self) -> dict:
        reflection_dict = deepcopy(self.user_reflection_dict)
        reflection_dict[RELATIONSHIP_KEY] = self.user_reflection_dict.get(
            RELATIONSHIP_KEY
        ).value
        return reflection_dict

    def to_dict(self):
        return {
            "entity_id": self.entity_id,
            "names": self.names,
            "info_dict": self.info_dict,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "user_reflection_dict": self.convert_reflection_dict_for_mongo(),
        }

    def should_update(self) -> bool:
        return self.mentions > UPDATE_COUNT_THRESHOLD

    def update(self):
        # Reset Mentions
        self.mentions = 0

        # TODO: implement the update

        # Log changes to entity in mongo
        self.log_to_mongo()
        return None

    def increment_mentions(self, is_first_time: bool = False):
        self.mentions += 1
        if self.should_update() or is_first_time:
            update_thread = threading.Thread(target=self.update)
            update_thread.start()

    @property
    def relationship(self):
        return self.info_dict.get(RELATIONSHIP_KEY, RelationshipType.GENERIC)

    @property
    def personality(self):
        return self.info_dict.get(PERSONALITY_KEY)

    def format(self) -> str:
        main_name = self.names[0]
        sentiment = self.user_reflection_dict.get(SENTIMENT_KEY, "neutral")

        return entity_format_str.format(
            name=main_name,
            relationship=self.relationship.value,
            personality=self.personality,
            core_sentiment=sentiment,
        )

    @property
    def metadata_key(self) -> str:
        return METADATA_ENTITY_KEY

    def modify_metadata_dict(self, metadata: dict) -> dict:
        curr_entity_ids = metadata.get(self.metadata_key, [])
        metadata[self.metadata_key] = curr_entity_ids.extend(self.entity_id)
        return metadata

    def log_to_mongo(self) -> None:
        entity_dict = self.to_dict()
        mongo_upsert("Entity", {"entity_id": self.entity_id}, entity_dict)
        return


class EntityName(BaseModel):
    """Class for Entity Name. To Mirror Mongo."""

    name: str
    created_at: datetime = datetime.now()
    last_updated: datetime = datetime.now()
    entity_id: Optional[str] = None

    @classmethod
    def from_vals(cls, name, entity_id: Optional[str] = None):
        return cls(name=name, entity_id=entity_id)

    def to_dict(self):
        return {
            "name": self.name,
            "entity_id": self.entity_id,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
        }

    def log_to_mongo(self) -> None:
        entity_name_dict = self.to_dict()
        mongo_upsert(
            "EntityName",
            {"entity_id": self.entity_id, "name": self.name},
            entity_name_dict,
        )
        return


def find_entity_name(name: str) -> Optional[EntityName]:
    name_options = mongo_read("EntityName", {"name": name}, find_many=True)

    option_to_use = None
    num_options = 0
    # Just take the last option at first, do some smarter filtering in the future
    # or in general, try to avoid collisions
    for option in name_options:
        option_to_use = option
        num_options += 1

    print(f"There are {num_options} entities with the name {name}")
    if num_options == 0:
        return None

    return EntityName.from_vals(name, option_to_use["entity_id"])
