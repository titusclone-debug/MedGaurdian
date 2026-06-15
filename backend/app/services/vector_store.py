"""Vector Store — ChromaDB local-first vector database for RAG."""
import os

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global ChromaDB client
_chroma_client = None
_collections = {}


def get_chroma_client():
    """Get or create ChromaDB persistent client."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            )
        )
        logger.info(f"📦 ChromaDB initialized at {settings.CHROMA_PERSIST_DIR}")
    return _chroma_client


def init_chromadb():
    """Initialize all ChromaDB collections."""
    client = get_chroma_client()
    
    collections = [
        settings.CHROMA_COLLECTION_REGULATIONS,
        settings.CHROMA_COLLECTION_POLICIES,
        settings.CHROMA_COLLECTION_CONSENT,
    ]
    
    for name in collections:
        try:
            collection = client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
            _collections[name] = collection
            logger.info(f"  ✅ Collection '{name}' ready ({collection.count()} documents)")
        except Exception as e:
            logger.error(f"  ❌ Failed to create collection '{name}': {e}")
    
    return _collections


def get_collection(name: str):
    """Get a specific collection."""
    if name not in _collections:
        client = get_chroma_client()
        _collections[name] = client.get_or_create_collection(name=name)
    return _collections[name]


def add_documents(
    collection_name: str,
    documents: List[str],
    metadatas: List[Dict[str, Any]],
    ids: List[str]
):
    """Add documents to a ChromaDB collection."""
    collection = get_collection(collection_name)
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    logger.info(f"Added {len(documents)} documents to '{collection_name}'")


def search_regulations(
    query: str,
    limit: int = 10,
    filter_metadata: Optional[Dict] = None
) -> List[Dict[str, Any]]:
    """Semantic search across regulations."""
    collection = get_collection(settings.CHROMA_COLLECTION_REGULATIONS)
    
    kwargs = {
        "query_texts": [query],
        "n_results": limit,
    }
    
    if filter_metadata:
        kwargs["where"] = filter_metadata
    
    results = collection.query(**kwargs)
    
    # Format results
    formatted = []
    if results and results["documents"]:
        for i, doc in enumerate(results["documents"][0]):
            formatted.append({
                "content": doc,
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else None,
                "id": results["ids"][0][i] if results["ids"] else None,
            })
    
    return formatted


def search_policies(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search hospital policies."""
    collection = get_collection(settings.CHROMA_COLLECTION_POLICIES)
    
    results = collection.query(
        query_texts=[query],
        n_results=limit,
    )
    
    formatted = []
    if results and results["documents"]:
        for i, doc in enumerate(results["documents"][0]):
            formatted.append({
                "content": doc,
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else None,
            })
    
    return formatted


def ingest_regulation(
    title: str,
    content: str,
    source: str,
    published_date: str,
    update_type: str = "notification",
    affected_areas: List[str] = None
):
    """Ingest a regulatory document into the vector store."""
    import hashlib
    
    # Chunk the content
    chunks = _chunk_text(content, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
    
    collection = get_collection(settings.CHROMA_COLLECTION_REGULATIONS)
    
    ids = []
    documents = []
    metadatas = []
    
    for i, chunk in enumerate(chunks):
        doc_id = hashlib.sha256(f"{title}_{i}_{chunk[:50]}".encode()).hexdigest()[:16]
        
        ids.append(doc_id)
        documents.append(chunk)
        metadatas.append({
            "title": title,
            "source": source,
            "published_date": published_date,
            "update_type": update_type,
            "affected_areas": ",".join(affected_areas) if affected_areas else "",
            "chunk_index": i,
            "total_chunks": len(chunks),
        })
    
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )
    
    logger.info(f"Ingested regulation '{title}' as {len(chunks)} chunks")
    return len(chunks)


def _chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Split text into overlapping chunks for embedding."""
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    
    return chunks if chunks else [text]
