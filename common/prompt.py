class Prompt:
    name: str = ""
    verbose: bool = False
    model: str = "chat"
    version: str = "0.0"
    template: str = ""

    def __init__(self, kwargs):
        self.template = self.template.format(**kwargs)
