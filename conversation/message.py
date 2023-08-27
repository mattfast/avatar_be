from copy import deepcopy
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import uuid4

from langchain.schema import AIMessage, BaseMessage, HumanMessage, SystemMessage

from common.metadata import METADATA_MESSAGE_ID_KEY, MetadataMixIn
from dbs.mongo import MongoMixin, mongo_upsert
from entity.base import Entity

ROLE_TO_CLASS_DICT = {"ai": AIMessage, "human": HumanMessage, "system": SystemMessage}


class Message(MetadataMixIn, MongoMixin):
    def __init__(
        self,
        content: str,
        role: str,
        session_id: str,
        speaker: Optional[str] = None,
        message_id: Optional[str] = None,
        entities: Optional[List[Entity]] = None,
        message_type: Optional[str] = "Plaintext",
    ):
        self.content = content
        self.role = role
        self.session_id = session_id
        self.speaker = speaker or role
        self.created_time = datetime.now(tz=timezone.utc)
        self.message_id = message_id or str(uuid4())
        self.entities = entities or []
        self.message_type = message_type

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "content": self.content,
            "session_id": self.session_id,
            "created_time": self.created_time,
            "role": self.role,
            "speaker": self.speaker,
            "entity_ids": [entity.entity_id for entity in self.entities],
            "message_type": self.message_type,
        }

    @property
    def metadata_key(self) -> str:
        return METADATA_MESSAGE_ID_KEY

    def modify_metadata_dict(self, metadata: dict) -> dict:
        metadata[self.metadata_key] = self.message_id
        # For all entities in the dictionary, modify the dictionary
        for entity in self.entities:
            metadata = entity.modify_metadata_dict(metadata)
        return metadata

    def add_entities(self, entities: List[Entity]) -> None:
        self.entities.extend(entities)

    def log_to_mongo(self) -> None:
        message_dict = self.to_dict()
        mongo_upsert("Messages", {"message_id": self.message_id}, message_dict)

    def format(self) -> str:
        return f"{self.speaker}: {self.content}"

    def as_langchain_message(self) -> BaseMessage:
        return ROLE_TO_CLASS_DICT[self.role](content=self.content)


# TODO: try to refactor this into the common class
def messages_for_chat_model(message_list: List[Message]) -> List[BaseMessage]:
    return deepcopy([message.as_langchain_message() for message in message_list])


def message_list_to_convo_prompt(conv_list: List[Message]) -> str:
    """Convert Conversation List to Prompt."""
    orig_str = "Conversation:\n"
    if len(conv_list) == 0:
        orig_str += "None\n"
        return orig_str

    for i, element in enumerate(conv_list):
        orig_str += f"{element.format()}\n"
    return orig_str


def partition_prev_messages(
    messages: Optional[List[Message]] = None,
) -> Tuple[List[Message], List[Message]]:
    """Partition Previous Messages into those to include with current user message and not."""
    if messages is None:
        return [], []
    partition_point = len(messages)
    for i, message in enumerate(messages[::-1]):
        if message.role == "ai":
            partition_point = len(messages) - i
            break
    messages_to_respond_to = messages[partition_point:]
    prev_messages = messages[:partition_point]
    return prev_messages, messages_to_respond_to
