from enum import Enum


class MemoryType(Enum):
    GENERIC = "generic"
    REFLECTION = "reflection"


all_memory_types = [m.value for m in MemoryType]
