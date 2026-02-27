# Qdrant Vector Database Integration

Complete reference for using Qdrant with LangChain.

---

## Installation

```bash
# Python client
pip install langchain-qdrant qdrant-client

# Docker (recommended for local)
docker pull qdrant/qdrant
docker run -p 6333:6333 -p 6334:6334 \
    -v "$(pwd)/qdrant_storage:/qdrant/storage:z" \
    qdrant/qdrant
```

**Access points**:
- REST API: `http://localhost:6333`
- Web UI: `http://localhost:6333/dashboard`
- gRPC: `localhost:6334`

---

## Deployment Modes

### In-Memory (Development)

```python
from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings()
vectorstore = QdrantVectorStore.from_documents(
    docs, embeddings,
    location=":memory:",
    collection_name="my_docs"
)
```

### Local Persistence

```python
vectorstore = QdrantVectorStore.from_documents(
    docs, embeddings,
    path="./qdrant_data",
    collection_name="my_docs"
)
```

### Docker/Server

```python
vectorstore = QdrantVectorStore.from_documents(
    docs, embeddings,
    url="http://localhost:6333",
    prefer_grpc=True,  # Faster for large datasets
    collection_name="my_docs"
)
```

### Qdrant Cloud

```python
vectorstore = QdrantVectorStore.from_documents(
    docs, embeddings,
    url="https://xxx.qdrant.io:6333",
    api_key="your-api-key",
    collection_name="my_docs"
)
```

---

## Search Modes

### Dense Search (Default)

Semantic similarity using embeddings.

```python
from langchain_qdrant import RetrievalMode

vectorstore = QdrantVectorStore.from_documents(
    docs,
    embedding=embeddings,
    location=":memory:",
    collection_name="my_docs",
    retrieval_mode=RetrievalMode.DENSE
)

results = vectorstore.similarity_search("semantic query", k=5)
```

### Sparse Search

Keyword-based using BM25.

```python
from langchain_qdrant import FastEmbedSparse, RetrievalMode

sparse_embeddings = FastEmbedSparse(model_name="Qdrant/BM25")

vectorstore = QdrantVectorStore.from_documents(
    docs,
    sparse_embedding=sparse_embeddings,
    location=":memory:",
    collection_name="my_docs",
    retrieval_mode=RetrievalMode.SPARSE
)
```

### Hybrid Search (Recommended for Production)

Combines dense + sparse with score fusion.

```python
from langchain_qdrant import QdrantVectorStore, FastEmbedSparse, RetrievalMode
from langchain_openai import OpenAIEmbeddings

dense_embeddings = OpenAIEmbeddings()
sparse_embeddings = FastEmbedSparse(model_name="Qdrant/BM25")

vectorstore = QdrantVectorStore.from_documents(
    docs,
    embedding=dense_embeddings,
    sparse_embedding=sparse_embeddings,
    location=":memory:",
    collection_name="my_docs",
    retrieval_mode=RetrievalMode.HYBRID
)

# Benefits:
# - Semantic understanding (dense)
# - Exact keyword matching (sparse)
# - Automatic score fusion
```

**Mode Comparison**:

| Mode | Best For | Trade-off |
|------|----------|-----------|
| Dense | Semantic queries | May miss exact terms |
| Sparse | Keyword/exact match | No semantic understanding |
| Hybrid | Production systems | Higher compute cost |

---

## Filtering

### Metadata Filters

```python
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range

# Exact match
filter = Filter(
    must=[
        FieldCondition(key="category", match=MatchValue(value="technical"))
    ]
)

# Range filter
filter = Filter(
    must=[
        FieldCondition(key="year", range=Range(gte=2020, lte=2024))
    ]
)

# Multiple conditions
filter = Filter(
    must=[
        FieldCondition(key="department", match=MatchValue(value="engineering")),
        FieldCondition(key="status", match=MatchValue(value="active"))
    ]
)

results = vectorstore.similarity_search(
    "query",
    k=5,
    filter=filter
)
```

### Filter Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `must` | All conditions required | AND logic |
| `should` | At least one required | OR logic |
| `must_not` | Exclude matches | NOT logic |

```python
# Complex filter: (A AND B) OR C, NOT D
filter = Filter(
    should=[
        Filter(must=[conditionA, conditionB]),
        conditionC
    ],
    must_not=[conditionD]
)
```

---

## Collection Management

### Direct Client Access

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(url="http://localhost:6333")

# Create collection
client.create_collection(
    collection_name="my_collection",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
)

# List collections
collections = client.get_collections()

# Delete collection
client.delete_collection("my_collection")

# Collection info
info = client.get_collection("my_collection")
print(f"Points: {info.points_count}")
print(f"Vectors: {info.vectors_count}")
```

### Batch Operations

```python
from qdrant_client.models import PointStruct

# Bulk upsert
points = [
    PointStruct(
        id=i,
        vector=embedding,
        payload={"text": text, "source": source}
    )
    for i, (embedding, text, source) in enumerate(data)
]

client.upsert(
    collection_name="my_collection",
    points=points,
    wait=True
)
```

---

## Performance Optimization

### HNSW Index Configuration

```python
from qdrant_client.models import HnswConfigDiff

# Optimize for search speed
client.update_collection(
    collection_name="my_collection",
    hnsw_config=HnswConfigDiff(
        m=16,              # Number of edges per node (default: 16)
        ef_construct=100,  # Index build quality (default: 100)
        full_scan_threshold=10000  # Switch to brute force below this
    )
)
```

### Quantization (Reduce Memory)

```python
from qdrant_client.models import ScalarQuantization, ScalarQuantizationConfig, ScalarType

client.update_collection(
    collection_name="my_collection",
    quantization_config=ScalarQuantization(
        scalar=ScalarQuantizationConfig(
            type=ScalarType.INT8,
            quantile=0.99,
            always_ram=True
        )
    )
)
```

### Payload Indexing

```python
from qdrant_client.models import PayloadSchemaType

# Index frequently filtered fields
client.create_payload_index(
    collection_name="my_collection",
    field_name="category",
    field_schema=PayloadSchemaType.KEYWORD
)

client.create_payload_index(
    collection_name="my_collection",
    field_name="timestamp",
    field_schema=PayloadSchemaType.INTEGER
)
```

---

## LangChain Integration Patterns

### Existing Collection

```python
from langchain_qdrant import QdrantVectorStore

# Connect to existing (no document loading)
vectorstore = QdrantVectorStore.from_existing_collection(
    embedding=embeddings,
    collection_name="existing_docs",
    url="http://localhost:6333"
)
```

### Custom Retriever

```python
retriever = vectorstore.as_retriever(
    search_type="mmr",
    search_kwargs={
        "k": 5,
        "fetch_k": 20,
        "lambda_mult": 0.5,  # Diversity vs relevance balance
        "filter": Filter(must=[...])
    }
)
```

### Multi-Collection Search

```python
from langchain.retrievers import EnsembleRetriever

retriever1 = vectorstore1.as_retriever(search_kwargs={"k": 3})
retriever2 = vectorstore2.as_retriever(search_kwargs={"k": 3})

ensemble = EnsembleRetriever(
    retrievers=[retriever1, retriever2],
    weights=[0.6, 0.4]
)
```

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Slow search | No HNSW index | Configure HNSW |
| High memory | Large vectors | Enable quantization |
| Connection timeout | Wrong URL/port | Check Docker ports |
| Empty results | Wrong collection | Verify collection name |
| Low recall | k too small | Increase k or use MMR |

---

## Production Checklist

- [ ] Use persistent storage (not `:memory:`)
- [ ] Enable HNSW indexing
- [ ] Index filterable payload fields
- [ ] Configure appropriate vector dimensions
- [ ] Set up backup strategy
- [ ] Monitor collection metrics
- [ ] Use gRPC for high throughput
- [ ] Consider quantization for large datasets
