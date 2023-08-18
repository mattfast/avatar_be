from common.prompt import Prompt


class MainChatPrompt(Prompt):
    name = "MainChatPrompt"
    version = "0.0.1"
    template = prefix_prompt = """Use the context for the following message and information about all people mentioned to respond.

# Context for message content

## Emotional Sentiment: {emotions}

## Information About Recent People Mentioned:
{recent_people_info}

## Potentially Relevant Information:
{vector_info}

# Description of conversant

## Name: {name}
## Age: {age}
## Personality: {personality}
## Current Mood about topic: {sentiment}
## Current Intent: {current_intent}
## Current response need: {current_need}
## Relevant Interests: {relevant_interests}
## Opinions on people mentioned: {current_opinions}

# Description of Yourself (how you respond)

## Name: {self_name}
## Age: {self_age}
## Personality: {self_personality}
## Current Feeling about topic: {self_sentiment}
## Current Intent: {self_current_intent}
## Relevant Interests: {self_relevant_interests}
## Opinions on people mentioned: {self_current_opinions}
"""
