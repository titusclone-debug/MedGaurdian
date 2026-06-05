import pytest
from unittest.mock import patch
import chromadb
from app.services.vector_store import (
    init_chromadb,
    get_chroma_client,
    ingest_regulation,
    search_regulations,
    _collections
)

class DummyEmbeddingFunction:
    def __call__(self, input):
        embeddings = []
        for text in input:
            if "fire safety" in text.lower():
                embeddings.append([1.0] + [0.0] * 383)
            elif "patient privacy" in text.lower():
                embeddings.append([0.0] + [1.0] + [0.0] * 382)
            else:
                embeddings.append([0.0] * 384)
        return embeddings

@pytest.fixture(autouse=True)
def setup_vector_store_test():
    # Force client to use EphemeralClient with DummyEmbeddingFunction
    client = chromadb.EphemeralClient()
    
    orig_get_or_create = client.get_or_create_collection
    def get_or_create_wrapper(name, **kwargs):
        if "embedding_function" not in kwargs:
            kwargs["embedding_function"] = DummyEmbeddingFunction()
        return orig_get_or_create(name, **kwargs)
    
    client.get_or_create_collection = get_or_create_wrapper
    
    # We clear the global collections dictionary in vector_store so it recreates them
    _collections.clear()
    
    with patch("app.services.vector_store.get_chroma_client", return_value=client), \
         patch("app.services.vector_store.init_chromadb", wraps=init_chromadb):
        yield client

def test_init_chromadb(setup_vector_store_test):
    from app.core.config import settings
    # init_chromadb should create collections
    cols = init_chromadb()
    assert settings.CHROMA_COLLECTION_REGULATIONS in cols
    assert settings.CHROMA_COLLECTION_POLICIES in cols
    assert settings.CHROMA_COLLECTION_CONSENT in cols

def test_ingest_regulation(setup_vector_store_test):
    # ingest_regulation should add chunks to the collection
    init_chromadb()
    
    title = "Test Fire Safety Directive"
    content = "This directive mandates proper fire safety procedures, fire extinguishers, and regular fire drills."
    source = "gazette"
    published_date = "2026-05-24"
    
    chunks_count = ingest_regulation(
        title=title,
        content=content,
        source=source,
        published_date=published_date,
        update_type="directive",
        affected_areas=["fire_safety"]
    )
    
    assert chunks_count > 0
    
    # Verify the collection has elements
    collection = setup_vector_store_test.get_collection("regulations")
    assert collection.count() == chunks_count

def test_search_regulations(setup_vector_store_test):
    init_chromadb()
    
    # Add two distinct regulations
    ingest_regulation(
        title="Fire Safety Order",
        content="This order concerns fire safety, fire NOC, and firefighting equipment regulations.",
        source="gazette",
        published_date="2026-05-24",
        update_type="order",
        affected_areas=["fire_safety"]
    )
    
    ingest_regulation(
        title="Data Protection Policy",
        content="This policy concerns patient privacy, data breach notification, and consent records.",
        source="mohfw",
        published_date="2026-05-24",
        update_type="policy",
        affected_areas=["dpdp"]
    )
    
    # Search for "fire safety"
    results = search_regulations("fire safety", limit=5)
    assert len(results) > 0
    # The closest document should be about fire safety
    assert "fire safety" in results[0]["content"].lower()
    
    # Search for "patient privacy"
    results = search_regulations("patient privacy", limit=5)
    assert len(results) > 0
    assert "patient privacy" in results[0]["content"].lower()
