from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from langchain.schema import AIMessage, BaseMessage, HumanMessage, SystemMessage

from dbs.mongo import mongo_read, mongo_write

ROLE_TO_CLASS_DICT = {"ai": AIMessage, "human": HumanMessage, "system": SystemMessage}


class Message:
    def __init__(
        self,
        content: str,
        role: str,
        session_id: str,
        speaker: Optional[str] = None,
        message_id: Optional[str] = None,
    ):
        self.content = content
        self.role = role
        self.session_id = session_id
        self.speaker = speaker or role
        self.created_time = datetime.now()
        self.message_id = message_id or str(uuid4())

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "content": self.content,
            "session_id": self.session_id,
            "created_time": self.created_time,
            "role": self.role,
            "speaker": self.speaker,
        }

    def log_to_mongo(self) -> None:
        message_dict = self.to_dict()
        mongo_write("Messages", message_dict)

    def format(self) -> str:
        return f"{self.speaker}: {self.content}"

    def as_langchain_message(self) -> BaseMessage:
        return ROLE_TO_CLASS_DICT[self.role](content=self.content)


def message_list_to_convo_prompt(conv_list: List[Message]) -> str:
    """Convert Conversation List to Prompt."""
    orig_str = "Conversation:\n"
    for i, element in enumerate(conv_list):
        orig_str += f"{element.format()}\n"
    return orig_str
