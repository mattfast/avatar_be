from langchain.chat_models.openai import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.llms.openai import OpenAI

from keys import openai_api_key

embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)

fast_model = OpenAI(
    model="text-davinci-003", temperature=0, openai_api_key=openai_api_key
)
chat_model = ChatOpenAI(
    temperature=0.2, model="gpt-3.5-turbo", openai_api_key=openai_api_key
)
old_chat_model = ChatOpenAI(
    temperature=0.2, model="gpt-3.5-turbo-0301", openai_api_key=openai_api_key
)
simple_model = OpenAI(
    model="text-babbage-001", temperature=0, openai_api_key=openai_api_key
)
gpt_4_model = ChatOpenAI(
    temperature=0.2, model_name="gpt-4", openai_api_key=openai_api_key
)

chat_models_list = ["chat", "gpt-4", "old_chat"]
MODEL_DICT = {
    "babbage": simple_model,
    "chat": chat_model,
    "old_chat": old_chat_model,
    "fast": fast_model,
    "gpt-4": gpt_4_model,
}
pronoun_list = [
    "she",
    "he",
    "it",
    "they",
    "him",
    "his",
    "her",
    "hers",
    "their",
    "theirs",
    "its",
    "them",
]
