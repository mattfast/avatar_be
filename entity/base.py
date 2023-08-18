from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import uuid4
from dbs.mongo import mongo_read, mongo_upsert

from pydantic import BaseModel


class RelationshipType(Enum):
    """Relationship types."""

    MOTHER = "Mother"
    FATHER = "Father"
    SIBLING = "Sibling"
    GRANDPARENT = "Grandparent"
    AUNT = "Aunt"
    UNCLE = "Uncle"
    COUSIN = "Cousin"
    GENERAL_FAMILY = "General Family Member"
    FRIEND = "Friend"
    CLOSE_FRIEND = "Close Friend"
    ACQUAINTANCE = "Acquaintance"
    GENERIC = "Generic"


relationship_list = set([r.value for r in RelationshipType])

MAX_CORE_MEMORIES = 5
# TODO: add segmenting of type of memories each person has


class Entity(BaseModel):
    """Class for Entity. To Mirror Mongo."""

    entity_id: str
    """Entity ID."""

    names: List[str] = []
    """Should map to entity name key."""

    relationship: RelationshipType = RelationshipType.GENERIC
    """Relationship with person."""

    personality: str = ""
    """Personality."""

    opinion: str = ""
    """Persons opinions on this entity."""

    core_memories: List[str] = []
    """Memories Associated with this Entity."""

    memory_namespace: str = ""
    """Pinecone namespace associated with memories for this Entity."""

    created_at: datetime = datetime.now()

    last_updated: datetime = datetime.now()

    @classmethod
    def create_new(cls, name, relationship: RelationshipType = RelationshipType.GENERIC):
        entity_id = str(uuid4())
        entity_namespace = entity_id
        return cls(
            id=entity_id,
            names=[name],
            relationship=relationship,
            memories_namespace=entity_namespace,
        )

    @classmethod
    def from_entity_id(cls, entity_id: str):
        if entity_id is None:
            raise ValueError("EntityID provided is None")

        entity = mongo_read("Entity", {"entity_id": entity_id})
        if entity is None:
            raise ValueError(f"Entity ID {entity_id} not found in Mongo")
        return cls(
            entity_id=entity["entity_id"],
            names=entity["names"],
            relationship=RelationshipType(entity["relationship"]),
            personality=entity["personality"],
            opinion=entity["opinion"],
            core_memories=entity["core_memories"],
            memory_namespace=entity["memory_namespace"],
            created_at=entity["created_at"]
        )

    def to_dict(self):
        return {
            "entity_id": self.entity_id,
            "names": self.names,
            "relationship": self.relationship.value,
            "personality": self.personality,
            "opinion": self.opinion,
            "core_memories": self.core_memories,
            "memory_namespace": self.memory_namespace,
            "created_at": self.created_at,
            "last_updated": self.last_updated
        }

    def update_mongo(self) -> None:
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
            "last_updated": self.last_updated
        }

    def update_mongo(self) -> None:
        entity_name_dict = self.to_dict()
        mongo_upsert("EntityName", {"entity_id": self.entity_id, "name": self.name}, entity_name_dict)
        return


def find_entity_name(name: str) -> Optional[EntityName]:
    name_options = mongo_read("EntityName", {"name": name}, find_many=True)
    if name_options is None:
        return None

    option_to_use = None
    num_options = 0
    # Just take the last option at first, do some smarter filtering in the future
    # or in general, try to avoid collisions
    for option in name_options:
        option_to_use = option
        num_options += 1
    print(f"There are {num_options} entities with the name {name}")
    return EntityName.from_vals(name, option_to_use["entity_id"])
