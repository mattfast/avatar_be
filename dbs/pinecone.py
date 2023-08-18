from typing import Optional
from uuid import uuid4

from constants import embeddings
from dbs import pinecone_index


def upsert_piece(
    piece: str, metadata: Optional[dict] = None, namespace: Optional[str] = None
):
    """Upsert a string."""
    vec = embeddings.embed_query(piece)
    vec_id = str(uuid4())
    upsert_dict = {"id": vec_id, "values": vec}
    if metadata is not None:
        upsert_dict["metadata"] = metadata
    upsert_response = pinecone_index.upsert(vectors=[upsert_dict], namespace=namespace)
    print(upsert_response)
