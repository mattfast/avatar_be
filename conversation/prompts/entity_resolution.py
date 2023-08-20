from common.prompt import Prompt


## Pronoun resolution also needs to resolve more vague phrases. ie "that chick" or "that person"
class ResolvePronounsPrompt(Prompt):
    name = "ResolvePronounsPrompt"
    version = "0.0.1"
    model = "chat"
    template = """Using the context from the following conversation, rewrite the sentence provided with the relevant pronouns replaced with actual subjects. Include modifiers. If you can't identify the correct pronoun, output IDK.
Just output the rewritten sentence. Nothing else.

##### Start Examples #####
Example 1:
Conversation:
You: How's your mom doing?

Sentence: She's fine
Rewritten Sentence: Mom is fine.

Example 2:
Conversation:
You: How are you?

Sentence: Who is she?
Rewritten sentence: IDK

##### End Examples #####

{conv_list}
Sentence:
{last_message}

Rewritten Sentence:
"""


class EntityExtractionPrompt(Prompt):
    name = "EntityExtractionPrompt"
    version = "0.0.1"
    model = "chat"
    template = """Output the people, if any, in the following sentence as a comma separated list. Include possessives as one entry.
If there are no people, output NONE. People are words/ sets of words that can be people. Do not include "me", "I" or other pronouns as an option.

##### Start Examples #####
Example 1:
Sentence: She's fine
People (that refer to proper nouns): NONE

Example 2:
Sentence: Nancy told me about James.
People (that refer to proper nouns): [Nancy, James]

Example 3:
Sentence: My mom told my friend, Isabelle, about her.
People (that refer to proper nouns): [My mom, Isabelle]

Example 4:
Sentence: I told you, I'm ok.
People (that refer to proper nouns): NONE

##### End Examples #####

Sentence: {sentence}
People (that refer to proper nouns):"""


class EntityComparisonPrompt(Prompt):
    name = "EntityComparisonPrompt"
    version = "0.0.1"
    template = """You are given information about two different people. Is the first the same as the second?
Write YES: REASON FOR DECISION if so. otherwise, write NO: REASON FOR DECISION

Person 1: {first_person}
Person 1 Info: {first_person_info}

Person 2: {second_person}
Person 2 Info: {second_person_info}

Decision:
"""
