import threading
from copy import deepcopy
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel

from common.execute import compile_and_run_prompt
from common.metadata import METADATA_ENTITY_KEY, MetadataMixIn
from dbs.mongo import MongoMixin, mongo_read, mongo_upsert
from entity.prompts.entity_update import (
    EmotionalSentimentTowardEntityPrompt,
    OverallOpinionTowardsEntityPrompt,
    PersonalityExtractionPrompt,
    RelationshipExtractionPrompt,
)


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
OVERALL_OPINION_KEY = "opinion"

UPDATE_COUNT_THRESHOLD = 5

default_user_reflection_dict = {
    RELATIONSHIP_KEY: RelationshipType.GENERIC,
    SENTIMENT_KEY: "neutral",
}


class Entity(BaseModel, MetadataMixIn, MongoMixin):
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

    created_at: datetime = datetime.now(tz=timezone.utc)

    last_updated: datetime = datetime.now(tz=timezone.utc)

    @classmethod
    def create_new(
        cls,
        name: str,
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
        user_reflection_dict = entity["user_reflection_dict"]
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
            "user_id": self.user_id,
            "names": self.names,
            "info_dict": self.info_dict,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "user_reflection_dict": self.convert_reflection_dict_for_mongo(),
        }

    def should_update(self) -> bool:
        return self.mentions % UPDATE_COUNT_THRESHOLD == 1

    def update(self, message: str):
        # Reset Mentions
        name = self.names[0]

        # TODO: implement and test the opinion update
        relationship_type = compile_and_run_prompt(
            RelationshipExtractionPrompt,
            {
                "entity_name": name,
                "former_type": self.relationship,
                "memories": message,
                "relationship_types": relationship_list,
            },
        )
        if relationship_type in relationship_list:
            self.set_relationship(RelationshipType(relationship_type))

        personality_res = compile_and_run_prompt(
            PersonalityExtractionPrompt,
            {
                "entity_name": name,
                "memories": message,
                "former_understanding": self.personality,
            },
        )
        if personality_res != "NO NEW INFO":
            self.set_personality(personality_res)

        sentiment_res = compile_and_run_prompt(
            EmotionalSentimentTowardEntityPrompt,
            {
                "entity_name": name,
                "memories": message,
                "personality": self.personality,
                "former_sentiment": self.sentiment,
            },
        )
        if sentiment_res != "NO CHANGE":
            self.set_sentiment(sentiment_res)

        self.last_updated = datetime.now(tz=timezone.utc)

        # Log changes to entity in mongo
        self.log_to_mongo()

    def trigger_update(self, message: str):
        if self.should_update():
            update_thread = threading.Thread(target=self.update, args=[message])
            update_thread.start()

    @property
    def relationship(self):
        return self.user_reflection_dict.get(RELATIONSHIP_KEY, RelationshipType.GENERIC)

    def set_relationship(self, relationship_val: RelationshipType):
        self.user_reflection_dict[RELATIONSHIP_KEY] = relationship_val

    @property
    def personality(self):
        return self.info_dict.get(PERSONALITY_KEY)

    def set_personality(self, personality: str):
        self.info_dict[PERSONALITY_KEY] = personality

    @property
    def sentiment(self):
        return self.user_reflection_dict.get(SENTIMENT_KEY, "neutral")

    def set_sentiment(self, sentiment: str):
        self.user_reflection_dict[SENTIMENT_KEY] = sentiment

    def format(self) -> str:
        main_name = self.names[0]

        return entity_format_str.format(
            name=main_name,
            relationship=self.relationship.value,
            personality=self.personality,
            core_sentiment=self.sentiment,
        )

    @property
    def metadata_key(self) -> str:
        return METADATA_ENTITY_KEY

    def modify_metadata_dict(self, metadata: dict) -> dict:
        curr_entity_ids = metadata.get(self.metadata_key, [])
        metadata[self.metadata_key] = curr_entity_ids + [self.entity_id]
        return metadata

    def log_to_mongo(self) -> None:
        entity_dict = self.to_dict()
        mongo_upsert("Entity", {"entity_id": self.entity_id}, entity_dict)


class EntityName(BaseModel):
    """Class for Entity Name. To Mirror Mongo."""

    name: str
    user_id: str
    created_at: datetime = datetime.now(tz=timezone.utc)
    entity_id: Optional[str] = None

    @classmethod
    def from_vals(
        cls,
        name,
        user_id,
        entity_id: Optional[str] = None,
        created_at: datetime = datetime.now(tz=timezone.utc),
    ):
        return cls(
            name=name, user_id=user_id, created_at=created_at, entity_id=entity_id
        )

    def to_dict(self):
        return {
            "name": self.name,
            "user_id": self.user_id,
            "entity_id": self.entity_id,
            "created_at": self.created_at,
        }

    def log_to_mongo(self) -> None:
        entity_name_dict = self.to_dict()
        mongo_upsert(
            "EntityName",
            {"entity_id": self.entity_id, "name": self.name},
            entity_name_dict,
        )


def find_entity_name(name: str, user_id: str) -> Optional[EntityName]:
    name_options = mongo_read(
        "EntityName", {"name": name, "user_id": user_id}, find_many=True
    )

    option_to_use = None
    num_options = 0
    # Just take the first option, do some smarter filtering in the future
    # or in general, try to avoid collisions
    for option in name_options:
        option_to_use = option
        num_options += 1
        break

    print(f"There are {num_options} entities with the name {name}")
    if num_options == 0:
        return None

    return EntityName.from_vals(name, user_id, option_to_use["entity_id"])
