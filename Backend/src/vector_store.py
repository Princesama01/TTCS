import re
import uuid
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams


class LegalVectorStore:
    def __init__(self, path: Optional[str] = None, collection_name: str = "legal_contracts", dim: int = 384):
        self.client = QdrantClient(path=path) if path else QdrantClient(":memory:")
        self.collection_name = collection_name
        self.dim = dim

    @staticmethod
    def _validate_filter_value(value: str, field_name: str) -> str:
        if not value:
            raise ValueError(f"{field_name} cannot be empty")
        if field_name == "version" and not re.match(r"^v\d+$", value):
            raise ValueError(f"Invalid version format: {value}")
        if field_name == "article_no" and not re.match(r"^\d+$", value):
            raise ValueError(f"Invalid article_no format: {value}")
        if field_name == "clause_no" and not re.match(r"^\d+(\.\d+)*$", value):
            raise ValueError(f"Invalid clause_no format: {value}")
        if field_name == "doc_id" and not re.match(r"^[a-zA-Z0-9_-]+$", value):
            raise ValueError(f"Invalid doc_id format: {value}")
        return value

    def create_collection(self):
        if self.client.collection_exists(self.collection_name):
            return
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config={
                "micro": VectorParams(size=self.dim, distance=Distance.COSINE),
                "macro": VectorParams(size=self.dim, distance=Distance.COSINE),
                "xref": VectorParams(size=self.dim, distance=Distance.COSINE),
            },
        )

    def upsert_points(self, points: List[PointStruct]):
        self.client.upsert(collection_name=self.collection_name, points=points)

    def build_point(self, vector_name: str, vector: list, payload: dict) -> PointStruct:
        return PointStruct(id=str(uuid.uuid4()), vector={vector_name: vector}, payload=payload)

    def search(
        self,
        vector_name: str,
        query_vector: list,
        limit: int = 5,
        version_filter: Optional[str] = None,
        article_filter: Optional[str] = None,
        clause_filter: Optional[str] = None,
        doc_id_filter: Optional[str] = None,
    ) -> list:
        must = []
        if version_filter:
            must.append(FieldCondition(key="version", match=MatchValue(value=self._validate_filter_value(version_filter, "version"))))
        if article_filter:
            must.append(FieldCondition(key="article_no", match=MatchValue(value=self._validate_filter_value(article_filter, "article_no"))))
        if clause_filter:
            must.append(FieldCondition(key="clause_no", match=MatchValue(value=self._validate_filter_value(clause_filter, "clause_no"))))
        if doc_id_filter:
            must.append(FieldCondition(key="doc_id", match=MatchValue(value=self._validate_filter_value(doc_id_filter, "doc_id"))))

        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            using=vector_name,
            query_filter=Filter(must=must) if must else None,
            limit=limit,
            with_payload=True,
        )
        return response.points

    def scroll_by_doc(self, doc_id: str, chunk_type: str = "micro", limit: int = 200):
        validated_doc_id = self._validate_filter_value(doc_id, "doc_id")
        must = [FieldCondition(key="doc_id", match=MatchValue(value=validated_doc_id))]
        if chunk_type:
            if chunk_type not in ["micro", "macro", "xref"]:
                raise ValueError(f"Invalid chunk_type: {chunk_type}")
            must.append(FieldCondition(key="chunk_type", match=MatchValue(value=chunk_type)))
        points, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(must=must),
            limit=limit,
            with_payload=True,
        )
        return points

    def scroll_filtered(
        self,
        *,
        version_filter: Optional[str] = None,
        article_filter: Optional[str] = None,
        chunk_type: str = "micro",
        doc_id_filter: Optional[str] = None,
        limit: int = 500,
    ) -> list:
        must = []
        if version_filter:
            must.append(
                FieldCondition(
                    key="version",
                    match=MatchValue(value=self._validate_filter_value(version_filter, "version")),
                )
            )
        if article_filter:
            must.append(
                FieldCondition(
                    key="article_no",
                    match=MatchValue(value=self._validate_filter_value(article_filter, "article_no")),
                )
            )
        if doc_id_filter:
            must.append(
                FieldCondition(
                    key="doc_id",
                    match=MatchValue(value=self._validate_filter_value(doc_id_filter, "doc_id")),
                )
            )
        if chunk_type:
            if chunk_type not in ["micro", "macro", "xref"]:
                raise ValueError(f"Invalid chunk_type: {chunk_type}")
            must.append(FieldCondition(key="chunk_type", match=MatchValue(value=chunk_type)))
        points, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(must=must) if must else None,
            limit=limit,
            with_payload=True,
        )
        return points
