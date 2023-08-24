from common.prompt import Prompt


class RelationshipExtractionPrompt(Prompt):
    name = "RelationshipExtractionPrompt"
    version = "0.0.1"
    template = """You are given some memories of a conversation about a person called {entity_name}. These memories were mentioned by your friend in the past.
Based on the new memories provided and the type of relationship you knew the two had, output what type of relationship {entity_name} and your friend could now have.

Former Relationship type: {former_type}
Output one of the following: {relationship_types}.
Memories:
{memories}

Relationship Type between your friend and {entity_name}:
"""


class PersonalityExtractionPrompt(Prompt):
    name = "PersonalityExtractionPrompt"
    version = "0.0.1"
    template = """You are given some memories of a conversation about a person called {entity_name}. These memories were mentioned by your friend in the past.
Based on the new memories provided and the type of personality you knew {entity_name} had, update the {entity_name}'s personality with a new short description. If the memories contain no new information,
then output "NO NEW INFO", otherwise output a short description of just the personality. nothing else.

Former Understanding of {entity_name}'s' Personality: {former_understanding}
Memories:
{memories}

New Understanding of {entity_name}'s personality:
"""


# Try to be more exact with friend's personality
# eg. how do they process new information. are they more likely to like or dislike people?
# basically use friend's personality as a "believability" filter on the content of the memories provided
class EmotionalSentimentTowardEntityPrompt(Prompt):
    name = "EmotionalSentimentTowardEntityPrompt"
    version = "0.0.1"
    template = """You are given some memories of a conversation about a person called {entity_name}. These memories were mentioned by your friend in the past.
Based on the new memories provided, information about your friend's personality, and how they did feel about {entity_name}, output how your friend now feels towards {entity_name} in a one to two word sentiment phrase. If there is no change or not enough information to determine updated sentiment,
then output "NO CHANGE", otherwise output the new 1-2 word sentiment phrase.

Friend's Personality: {personality}
Former Sentiment towards {entity_name}: {former_sentiment}
Memories:
{memories}

Friend's Sentiment towards {entity_name}:
"""


# Try to be more exact with friend's personality
# eg. how do they process new information. are they more likely to like or dislike people?
# basically use friend's personality as a "believability" filter on the content of the memories provided
class OverallOpinionTowardsEntityPrompt(Prompt):
    name = "OverallOpinionToEntityPrompt"
    version = "0.0.1"
    template = """You are given some memories of a conversation about a person called {entity_name}. These memories were mentioned by your friend in the past.
Based on the new memories provided and what you know about your friends former opinions about {entity_name}, output a short description of your friend's new overall opinion {entity_name}. If there is no change or not enough information to determine updated opinions,
then output "NO NEW INFO", otherwise output a short description of the opinion. If you have an opinion, Write "Overall, my friend opinion of {entity_name} is... because..."

Former former opinion towards {entity_name}: {former_opinion}
Memories that friend has mentioned:
{memories}

Friend's overall opinion towards {entity_name}:
"""
