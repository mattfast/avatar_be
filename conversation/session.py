from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel
from entity.base import Entity, EntityName, find_entity_name
from conversation.prompts.chat import MainChatPrompt
from conversation.prompts.entity_resolution import (
    EntityExtractionPrompt,
    ResolvePronounsPrompt,
)
from common.execute import compile_and_run_prompt
from conversation.message import Message, message_list_to_convo_prompt
from dbs.mongo import mongo_read, mongo_upsert


class Session:
    def __init__(
        self,
        user_num,
        session_id: Optional[str] = None,
        messages: Optional[List[Message]] = None,
        last_message_sent: Optional[datetime] = None,
    ):
        self.user_num = user_num
        self.session_id = session_id or str(uuid4())
        self.messages = messages or []
        self.last_message_sent = last_message_sent or datetime.now()

    @classmethod
    def from_user(cls, user):
        print("Creating Session from User Info")
        user_num = user["number"]
        user_name = user.get("name", None)
        session_id = user.get("session_id", None)

        if session_id is None:
            return Session(user_num)
        session = mongo_read("Session", {"session_id": session_id})

        if session is None:
            return Session(user_num)

        messages = mongo_read("Messages", {"session_id": session_id}, find_many=True)
        if messages is None:
            return Session(user_num, session_id)

        last_messages = []
        last_sent_time = None
        for message in messages.sort("created_time", -1):
            if len(last_messages) == 10:
                break
            if last_sent_time is not None:
                last_sent_time = max(message["created_time"], last_sent_time)
            else:
                last_sent_time = message["created_time"]
            last_messages = [Message(message["content"], message["role"], user_name)] + last_messages

        return cls(user_num, session_id, last_messages, last_sent_time)

    def to_dict(self) -> dict:
        """Return as dictionary."""
        return {
            "number": self.user_num,
            "session_id": self.session_id,
            "last_message_sent": self.last_message_sent,
        }

    def log_to_mongo(self):
        session_dict = self.to_dict()
        mongo_upsert("Session", {"session_id": self.session_id}, session_dict)

    def process_next_message(self, message: str) -> str:
        return_message = "Hello!"
        user_message = Message(message, "human", self.session_id)
        user_message.log_to_mongo()
        initial_conv = message_list_to_convo_prompt(self.messages)
        rewritten_sentence = compile_and_run_prompt(ResolvePronounsPrompt, {"conv_list": initial_conv, "last_message": message})
        raw_entity_output = compile_and_run_prompt(EntityExtractionPrompt, {"sentence": rewritten_sentence})

        print("RAW ENTITY OUTPUT")
        print(raw_entity_output)
        entities = []
        entity_list = []
        if not raw_entity_output.lower() == "none":
            entities = [entity.strip().replace("\"'_.`", "") for entity in raw_entity_output.strip().lower().split(",")]
        print(entities)
        for name in entities:
            entity_name = find_entity_name(name)
            # No entity found, create new one
            if entity_name is None:
                print(f"Couldn't find entity: {entity_name}")
                entity = Entity.create_new(name)
                entity_name = EntityName.from_vals(name, entity.entity_id)
                entity.update_mongo()
                entity_name.update_mongo()
            else:
                print(f"Found Entity: {entity_name}")
                entity = Entity.from_entity_id(entity_name.entity_id)

            entity_list.append(entity)

        ai_message = Message(return_message, "ai", self.session_id)
        self.last_message_sent = ai_message.created_time
        ai_message.log_to_mongo()
        self.log_to_mongo()
        return return_message