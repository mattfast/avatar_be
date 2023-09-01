from common.prompt import Prompt

idea_types = ["question", "description", "recommendation"]


class TopicExtractionPrompt(Prompt):
    name = "TopicExtractionPrompt"
    version = "0.0.1"
    template = """Output the single most recent topical focus in the conversation. Be specific to the context of the conversation and details mentioned.

Output as a single phrase. Do not be generic.
Topics:
"""


class SpecificIQPrompt(Prompt):
    name = "SpecificIQPrompt"
    verbose = True
    version = "0.0.1"
    template = """"Brainstorm at most 3 ideas and examples specific to the following message in the context of the conversation that has been occurring: {message}
If you have already been talking about 

Focus on the following topics: {topics}
choose the most appropriate idea types from this list: {idea_types}

Relevant People Mentioned (include this information if relevant to the message):
{relevant_people}

# Example
Conversation: i'm looking to do more
that's a great idea
how should i do that?
Specific Ideas: [recommendation: swim more, question: what do you like to do?]

Format your output as a short JSON comma separated list: [idea type: idea 1, idea type: idea 2...].

Specific Ideas:
"""
