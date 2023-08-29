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


class ProperNounExtractionPrompt(Prompt):
    name = "ProperNounExtractionPrompt"
    version = "0.0.1"
    model = "chat"
    template = """Output all proper noun names or titles, if any, in the following texts as a comma separated list. Include whole modifiers in your response.
If there are no proper noun names or titles, output NONE. Do not include any non-named words or descriptors in your output. YOUR OUTPUT MUST ONLY BE NAMES, NOT DESCRIPTORS.

##### Start Examples #####
Example 1:
Last Texts: She's fine
Names or Titles: NONE

Example 2:
Last Texts: Nancy told me about James.
Names or Titles: [Nancy, James]

Example 3:
Last Texts: I told my friend Isabelle 
about your mom.
what do you think?
Names or Titles: [Isabelle]

Example 4:
Last Texts: I told you
I'm ok.
Names or Titles: NONE

##### End Examples #####

Last Texts: {texts}
Names or Titles:"""


class IdentifyAmbiguousPersonsPrompt(Prompt):
    name = "IdentifyAmbiguousPersonsPrompt"
    version = "0.0.1"
    model = "chat"
    template = """You are given a sentence and a list of known entities/ names in that sentence. Output all subjects that could refer to a person and don't have names. Include modifiers. 
If there are no such words, output "NONE". DO NOT include subjects that refer to yourself or the other person (eg.  "I", "me" or "you")

##### Start Examples #####
Example 1:
Sentence: How's your mom doing?
Known Names: [mom]
Non-named subjects: [your mom]

Example 2:
Sentence: I'm doing well
Known Names: NONE
Non-named subjects: NONE 

Example 3:
Sentence: My day was amazing. I ended up hanging with my friend, Nancy. How was your day?
Known Names: [Nancy]
Non-named subjects: NONE 

Example 4:
Sentence: What did she say about me?
Known Names: NONE
Non-named subjects: [she] 

##### End Examples #####

Sentence:{sentence}
Known Names: {known_names}
Non-named subjects:
"""


# Add more examples
# add examples of how person references people
class DifferentMentionsPrompt(Prompt):
    name = "DifferentMentionsPrompt"
    version = "0.0.1"
    model = "chat"
    template = """For the following name, come up with at most 5 ways the person can be casually referenced in a sentence with different wording. Output as a json list.

##### Start Examples #####
Example 1:
Person: john
Relationship: friend
How to Reference: [john, my friend john]

##### End Examples #####
Person: {person}
Relationship: {relationship}
How to Reference:
"""


# Try to add more examples
class ResolveReferencesPrompt(Prompt):
    name = "ResolveReferencesPrompt"
    version = "0.0.1"
    model = "chat"
    template = """You are given a recent descriptor used in a sentence. You are trying to determine if the entire descriptor (not one part of the descriptor) refers to a list of people to check against.
Using the logic of the conversation and a list to check against, determine if the entire descriptor refers to an element of that list or not.
If the descriptor could not be anyone listed, output NONE. Otherwise, output the person's name.
Output a short reason for your answer as well.

##### Start Examples #####
Example 1:
Conversation:
You: Did you talk to justin?
Sentence: Yeah, he's awesome
People to check against: [justin]
Descriptor: he

Who Descriptor refers to in the people to check against (if anyone):   justin, because he refers to justin in the previous sentence

Example 2:
Conversation:
You: Did you talk to her?
Sentence: Yeah, she's awesome
People to check against:  NONE
Descriptor: she

Who Descriptor refers to in the people to check against (if anyone):    NONE, because there is noone to check against.


##### End Examples #####


{conversation}
Sentence: {sentence}
People to check against:
{entities}
Descriptor: {phrase}

Who Descriptor refers to in the people to check against (if anyone):  
"""


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
