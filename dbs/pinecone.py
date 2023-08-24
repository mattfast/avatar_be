from typing import Optional
from uuid import uuid4

from common.metadata import METADATA_CONTENT_KEY, Metadata
from constants import embeddings
from dbs import pinecone_index


def upsert_piece(
    content: str,
    metadata: Optional[Metadata] = None,
    namespace: Optional[str] = None,
):
    """Upsert a string."""
    vec = embeddings.embed_query(content)
    vec_id = str(uuid4())
    upsert_dict = {"id": vec_id, "values": vec}

    validate = True
    if metadata is None:
        validate = False
        metadata = Metadata()

    metadata.kv_add(METADATA_CONTENT_KEY, content)
    upsert_dict["metadata"] = metadata.format_for_insertion(validate=validate)
    upsert_response = pinecone_index.upsert(vectors=[upsert_dict], namespace=namespace)
    print(upsert_response)


def search_for_str(piece: str, metadata_filter: Optional[dict] = None, top_k: int = 3):
    """Search for string."""
    vec = embeddings.embed_query(piece)
    matches = pinecone_index.query(
        vector=vec, filter=metadata_filter, top_k=top_k, include_metadata=True
    )
    return matches["matches"]
