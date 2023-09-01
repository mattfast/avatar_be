import threading
from copy import deepcopy
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import uuid4

from langchain.schema import BaseMessage

from ai.personality import default_ai_session_info, default_writing_style
from common.execute import compile_and_run_prompt
from common.memory import MemoryType
from common.metadata import (
    METADATA_ACCESSED_KEY,
    METADATA_INSERT_TIME_KEY,
    METADATA_MEMORY_TYPE_KEY,
    METADATA_SESSION_ID_KEY,
    METADATA_USER_ID_KEY,
    Metadata,
    MetadataMixIn,
)
from conversation.message import (
    Message,
    message_list_to_convo_prompt,
    messages_for_chat_model,
    partition_prev_messages,
)
from conversation.prompts.chat import (
    AIRespondPrompt,
    AIThoughtPrompt,
    MainChatPrompt,
    TakeInitiativePrompt,
)
from conversation.prompts.chat_update import (
    AIGoalPrompt,
    AIReflectionPrompt,
    AISentimentPrompt,
    FriendNeedPrompt,
)
from conversation.prompts.emotion_extraction import (
    EmotionExtractionPrompt,
    PersonIntentPrompt,
    TopicSentimentPrompt,
)
from conversation.prompts.entity_resolution import ProperNounExtractionPrompt
from conversation.prompts.intelligence import (
    SpecificIQPrompt,
    TopicExtractionPrompt,
    idea_types,
)
from conversation.prompts.memory_creation import IsImportantMemoryPrompt
from conversation.utils import clean_json_list_output, clean_sentence, format_memories
from dbs.mongo import MongoMixin, mongo_read, mongo_upsert
from dbs.pinecone import search_for_str, upsert_piece
from entity.base import Entity, EntityName, find_entity_name

default_user_session_info = {
    "personality": "unknown",
    "sentiment": "neutral",
    "intent": None,
    "need": None,
}


# Need an onboarding session -> ask for names, etc...
class Session(MetadataMixIn, MongoMixin):
    def __init__(
        self,
        user,
        session_id: Optional[str] = None,
        messages: Optional[List[Message]] = None,
        session_info: Optional[dict] = None,
        session_user_info: Optional[dict] = None,
        last_message_sent: Optional[datetime] = None,
    ):
        self.user = user
        self.session_id = session_id or str(uuid4())
        self.prev_messages, self.user_messages = partition_prev_messages(messages)
        self.session_info = session_info or default_ai_session_info
        self.session_user_info = session_user_info or default_user_session_info
        self.last_message_sent = last_message_sent or datetime.now(tz=timezone.utc)

    @property
    def metadata_key(self) -> str:
        return METADATA_SESSION_ID_KEY

    def modify_metadata_dict(self, metadata: dict) -> dict:
        metadata[self.metadata_key] = self.session_id
        return metadata

    @classmethod
    def from_user(cls, user):
        print("Creating Session from User Info")
        user_name = user.get("name", None)
        session_id = user.get("session_id", None)

        if session_id is None:
            return Session(user)
        session = mongo_read("Session", {"session_id": session_id})

        if session is None:
            return Session(user)

        last_sent_time = session.get(
            "last_message_sent", datetime.now(tz=timezone.utc)
        ).replace(tzinfo=timezone.utc)
        print(last_sent_time)
        curr_time = datetime.now(tz=timezone.utc)
        try:
            duration_diff = (curr_time - last_sent_time).seconds
        except:
            duration_diff = 0

        if duration_diff >= 18000:
            return Session(user)

        session_info = session.get("session_info", None)
        session_user_info = session.get("session_user_info", None)
        messages = mongo_read("Messages", {"session_id": session_id}, find_many=True)

        last_messages = []
        last_sent_time = None
        for message in messages.sort("created_time", -1):
            if len(last_messages) == 12:
                break
            if last_sent_time is not None:
                last_sent_time = max(message["created_time"], last_sent_time)
            else:
                last_sent_time = message["created_time"]

            entity_ids = message.get("entity_ids", [])
            entities = [Entity.from_entity_id(entity_id) for entity_id in entity_ids]
            last_messages = [
                Message(
                    message["content"],
                    message["role"],
                    user_name,
                    message_id=message["message_id"],
                    entities=entities,
                )
            ] + last_messages
            print(message)

        return cls(
            user,
            session_id,
            last_messages,
            session_info,
            session_user_info,
            last_sent_time,
        )

    def to_dict(self) -> dict:
        """Return as dictionary."""
        return {
            "number": self.user["number"],
            "session_id": self.session_id,
            "last_message_sent": self.last_message_sent,
            "session_info": self.session_info,
            "session_user_info": self.session_user_info,
        }

    def log_to_mongo(self):
        session_dict = self.to_dict()
        mongo_upsert("Session", {"session_id": self.session_id}, session_dict)

    def extract_and_process_entities(self, message: str) -> List[Entity]:
        """Extract and process entities."""
        print(message)
        texts = self.format_recent_user_messages() + f"{message}\n"
        raw_entity_output = compile_and_run_prompt(
            ProperNounExtractionPrompt,
            {"texts": texts},
        )

        print("RAW ENTITY OUTPUT")
        print(raw_entity_output)
        entity_list = []
        entities = clean_json_list_output(raw_entity_output)

        # Only choose top 5 entities. Can Choose Custom Sorting Algorithm
        # in the future
        entities = entities[:4]
        print(entities)
        for name in entities:
            entity_name = find_entity_name(name, self.user["user_id"])
            # No entity found, create new one
            if entity_name is None:
                print(f"Couldn't find entity: {name}")
                entity = Entity.create_new(name, self.user["user_id"])
            else:
                print(f"Found Entity: {entity_name}")
                entity = Entity.from_entity_id(entity_name.entity_id)

            entity.mentions += 1
            entity_list.append(entity)

        return entity_list

    def process_next_message(self, message: str) -> Message:
        message = clean_sentence(message)
        user_message = Message(message, "human", self.session_id)
        user_message.log_to_mongo()

        emotions_list = []
        emotions_thread = threading.Thread(
            target=self.extract_emotions, args=[message, emotions_list]
        )
        emotions_thread.start()

        entity_list = self.extract_and_process_entities(message)
        user_message.add_entities(entity_list)
        print(user_message)
        user_message.log_to_mongo()

        self.user_messages += [user_message]

        emotions_thread.join()

        return self.run_main_prompt(
            emotions_list,
        )

    def extract_emotions(self, curr_user_message, emotions_list):
        """Extract Emotions."""
        prev_conversation = message_list_to_convo_prompt(self.prev_messages)
        last_texts = self.format_recent_user_messages() + f"{curr_user_message}\n"
        emotion_result = compile_and_run_prompt(
            EmotionExtractionPrompt,
            {"conversation": prev_conversation, "texts": last_texts},
        )
        emotions = [emotion.strip().lower() for emotion in emotion_result.split(",")]
        emotions_list.extend(emotions)
        return None

    def get_relevant_entity_memories(self, message: str, entities: List[Entity]) -> str:
        # Metadata Information for Relevant Memory Retrieval
        memory_metadata = Metadata()
        memory_metadata.kv_add(METADATA_USER_ID_KEY, self.user["user_id"])
        for entity in entities:
            memory_metadata.add(entity)
        metadata_filter = memory_metadata.format_for_retrieval()
        matches = search_for_str(message, metadata_filter=metadata_filter)
        return format_memories(matches)

    def format_recent_user_messages(self) -> str:
        """Format all recent user messages."""
        user_message_str = ""
        for message in self.user_messages:
            user_message_str += f"{message.content}\n"
        return user_message_str

    def run_intelligence_prompts(
        self,
        message_list: List[BaseMessage],
        entities: List[Entity],
        intel_vals: List[str],
    ):
        """Run intelligence prompts."""
        topics = compile_and_run_prompt(
            TopicExtractionPrompt, {}, messages=deepcopy(message_list)
        )
        relevant_people = "None"
        if len(entities) > 0:
            relevant_people = "\n".join([entity.format() for entity in entities])
        intelligence_res = compile_and_run_prompt(
            SpecificIQPrompt,
            {
                "message": self.format_recent_user_messages(),
                "topics": topics,
                "relevant_people": relevant_people,
                "idea_types": idea_types,
            },
            messages=deepcopy(message_list),
        )
        intel_vals.append(intelligence_res)

    def update_friend_need(self, message_list: List[BaseMessage]):
        friend_sentiment = self.session_user_info.get("sentiment", None)
        friend_intent = self.session_user_info.get("intent", None)
        self_name = self.session_info.get("name")
        prev_need = self.session_user_info.get("need", None)
        friend_need = compile_and_run_prompt(
            FriendNeedPrompt,
            {
                "self_name": self_name,
                "sentiment": friend_sentiment,
                "intent": friend_intent,
                "previous_need": prev_need,
            },
            messages=deepcopy(message_list),
        )
        self.session_user_info.update(
            {
                "need": friend_need,
            }
        )

    def run_initiative(self, message_list: List[BaseMessage], init_list: List[str]):
        """Run Initiative Building."""
        self_personality = self.session_info.get("personality")
        self_name = self.session_info.get("name")

        initiative_res = compile_and_run_prompt(
            TakeInitiativePrompt,
            {"self_name": self_name, "personality": self_personality},
            messages=deepcopy(message_list),
        )
        init_list.append(initiative_res)

    def run_main_prompt(
        self,
        emotions_list: List[str],
    ):
        # TODO: Update with all entities mentioned in the past 3-5 messages
        # Build an LRU cache
        entities = self.user_messages[-1].entities

        prev_messages = messages_for_chat_model(self.prev_messages)
        message_list = prev_messages + messages_for_chat_model(self.user_messages)
        intel_list = []
        intelligence_thread = threading.Thread(
            target=self.run_intelligence_prompts,
            args=[message_list, entities, intel_list],
        )
        intelligence_thread.start()

        ## General Information about Conversant

        # Session Specific Information About Conversant
        current_need = self.session_user_info.get("need", None)

        ## Information about ai
        self_name = self.session_info.get("name")
        self_personality = self.session_info.get("personality")
        # or positive/negative -> can use sentiment detection here
        self_sentiment = self.session_info.get("sentiment")

        goals = self.session_info.get("goal")

        init_list = []
        init_thread = threading.Thread(
            target=self.run_initiative, args=[message_list, init_list]
        )
        init_thread.start()

        if len(entities) > 0:
            recent_people_info = "\n".join([entity.format() for entity in entities])
        else:
            recent_people_info = "None"

        thought_res = compile_and_run_prompt(
            AIThoughtPrompt,
            {
                "self_name": self_name,
                "personality": self_personality,
                "self_sentiment": self_sentiment,
                "goals": goals,
                "message": self.format_recent_user_messages(),
            },
            messages=deepcopy(message_list),
        )

        self_respond = compile_and_run_prompt(
            AIRespondPrompt,
            {
                "self_name": self_name,
                "personality": self_personality,
                "thoughts": thought_res,
                "recent_people_info": recent_people_info,
                "message": self.format_recent_user_messages(),
            },
            messages=deepcopy(message_list),
        )

        relevant_memories = self.get_relevant_entity_memories(
            self.format_recent_user_messages(), entities
        )
        emotions = ", ".join(emotions_list)

        examples = default_writing_style
        intelligence_thread.join()

        init_thread.join()
        chat_response = compile_and_run_prompt(
            MainChatPrompt,
            {
                "self_name": self_name,
                "message": self.format_recent_user_messages(),
                "emotions": emotions,
                "specifics": intel_list[0],
                "thoughts": thought_res,
                "init_res": init_list[0],
                "last_message": self.get_last_ai_message(),
                "planned_response": self_respond,
                "self_personality": self_personality,
                "writing_examples": examples,
            },
            messages=deepcopy(message_list),
        ).lower()
        print(chat_response)

        ai_message = Message(chat_response, "ai", self.session_id)
        return ai_message

    def update_on_send(self, ai_message: Message):
        ai_message.log_to_mongo()
        update_thread = threading.Thread(
            target=self.async_update_chat_info,
            args=[ai_message],
        )
        update_thread.start()

        process_memory_thread = threading.Thread(
            target=self.process_interaction_as_memory,
        )
        process_memory_thread.start()
        self.last_message_sent = ai_message.created_time
        self.log_to_mongo()

    def get_last_ai_message(self) -> Optional[str]:
        for message in self.prev_messages[::-1]:
            if message.role == "ai":
                return message.content
        return None

    def process_interaction_as_memory(self) -> None:
        last_user_message = self.user_messages[-1]
        relevant_memories = self.get_relevant_entity_memories(
            self.format_recent_user_messages(), last_user_message.entities
        )
        entities = last_user_message.entities
        formatted_convo = message_list_to_convo_prompt(self.prev_messages)
        names = ", ".join([entity.names[0] for entity in entities])
        # First determine if this message should be saved as a memory
        is_important_memory = compile_and_run_prompt(
            IsImportantMemoryPrompt,
            {
                "prior_info": relevant_memories,
                "entities": names,
                "conversation": formatted_convo,
                "message": self.format_recent_user_messages(),
            },
        )
        should_save = is_important_memory.split(":")[0].strip()
        print(should_save)

        # If not meant to save, then don't
        if "YES" not in should_save:
            return

        # Only update user entities reflections if the memory is an important one
        # TODO: check if the memory is important to this specific entity
        for entity in entities:
            print(f"TRIGGERING ENTITY {entity.names[0]} UPDATE")

            # Entity is New, so let's process its name as well
            if entity.mentions == 1:
                name = entity.names[0]
                entity_name = EntityName.from_vals(
                    name, self.user["user_id"], entity.entity_id
                )
                entity_name.log_to_mongo()

            entity.trigger_update(last_user_message.content)
            print(f"FINISHED ENTITY {entity.names[0]} UPDATE")
        content_to_save = self.format_recent_user_messages()

        # If so, the save it the metadata
        memory_metadata = Metadata()
        curr_time_secs = datetime.now(tz=timezone.utc).timestamp()
        memory_metadata.add(self)
        memory_metadata.kv_add(METADATA_MEMORY_TYPE_KEY, MemoryType.GENERIC.value)
        memory_metadata.kv_add(METADATA_ACCESSED_KEY, curr_time_secs)
        memory_metadata.kv_add(METADATA_INSERT_TIME_KEY, curr_time_secs)
        memory_metadata.kv_add(METADATA_USER_ID_KEY, self.user["user_id"])

        # Add Entity and Message Information
        memory_metadata.add(last_user_message)
        print("MESSAGE ENTITIES")
        print(last_user_message.entities)
        print(memory_metadata)

        # TODO: More integrated process of saving info about a message

        # Save Memory
        upsert_piece(content_to_save, memory_metadata)

    def async_update_chat_info(self, ai_message) -> None:
        personality = self.session_info.get("personality")
        self_name = self.session_info.get("name")
        non_ai_messages = messages_for_chat_model(
            self.prev_messages + self.user_messages
        )
        all_messages = non_ai_messages + messages_for_chat_model([ai_message])

        sentiment_res = compile_and_run_prompt(
            AISentimentPrompt,
            {"self_name": self_name, "personality": personality},
            messages=deepcopy(all_messages),
        )

        # Not a single word answer, fall on a default
        if len(sentiment_res.split(" ")) > 4:
            sentiment_res = "neutral"

        # reflection_res = compile_and_run_prompt(
        #     AIReflectionPrompt,
        #     {
        #         "self_name": self_name,
        #         "personality": personality,
        #         "sentiment": sentiment_res,
        #     },
        #     messages=deepcopy(all_messages),
        # )
        # goal_res = compile_and_run_prompt(
        #     AIGoalPrompt,
        #     {
        #         "self_name": self_name,
        #         "personality": personality,
        #         "sentiment": sentiment_res,
        #         "reflection": reflection_res,
        #     },
        #     messages=deepcopy(all_messages),
        # )

        self.session_info.update(
            {
                "sentiment": sentiment_res,
                # "goal": goal_res,
            }
        )
        self.log_to_mongo()

        # friend_sentiment = compile_and_run_prompt(
        #     TopicSentimentPrompt, {}, messages=deepcopy(non_ai_messages)
        # )
        # friend_intent = compile_and_run_prompt(
        #     PersonIntentPrompt, {}, messages=deepcopy(non_ai_messages)
        # )
        # prev_need = self.session_user_info.get("need", None)
        # friend_need = compile_and_run_prompt(
        #     FriendNeedPrompt,
        #     {
        #         "self_name": self_name,
        #         "sentiment": friend_sentiment,
        #         "intent": friend_intent,
        #         "previous_need": prev_need,
        #     },
        #     messages=deepcopy(all_messages),
        # )
        # self.session_user_info.update(
        #     {
        #         "sentiment": friend_sentiment,
        #         "intent": friend_intent,
        #         "need": friend_need,
        #     }
        # )
        # self.log_to_mongo()
        return None


# Hey! Need to ask you a few questions first! This would be part of app flow
# Get Name/ Age/ interests/ how you would describe your personality/ Tell me what's on your mind -> categorization of use case ->
# leave it to the ai to continue talking
