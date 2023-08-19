from langchain.chat_models.openai import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.llms.openai import OpenAI

from keys import openai_api_key

embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)

fast_model = OpenAI(
    model="text-davinci-003", temperature=0, openai_api_key=openai_api_key
)
chat_model = ChatOpenAI(temperature=0, openai_api_key=openai_api_key)
simple_model = OpenAI(
    model="text-babbage-001", temperature=0, openai_api_key=openai_api_key
)

MODEL_DICT = {"babbage": simple_model, "chat": chat_model, "fast": fast_model}
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
