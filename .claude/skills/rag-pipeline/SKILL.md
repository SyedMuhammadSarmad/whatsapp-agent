---
name: rag-pipeline
description: |
  Build production RAG (Retrieval-Augmented Generation) pipelines with LangChain and Qdrant.
  Use when users ask to implement semantic search, document Q&A, build RAG systems,
  create vector search, implement HyDE, CRAG, or Agentic RAG patterns.
---

# RAG Pipeline Builder

Build production-grade RAG systems from simple semantic search to advanced patterns.

## What This Skill Does

- Guide RAG pipeline implementation with LangChain + Qdrant
- Document ingestion (PDF, Word, images, web pages)
- Text splitting and chunking strategies
- Vector embeddings and storage
- Retrieval patterns (dense, sparse, hybrid)
- Advanced RAG: HyDE, CRAG, Agentic RAG with LangGraph

## What This Skill Does NOT Do

- Deploy production infrastructure
- Handle authentication/authorization systems
- Provide LLM fine-tuning guidance
- Manage cloud billing or quotas

---

## Before Implementation

Gather context to ensure successful implementation:

| Source | Gather |
|--------|--------|
| **Codebase** | Existing structure, dependencies, Python version |
| **Conversation** | Data types, scale, query patterns, latency needs |
| **Skill References** | Patterns from `references/` for chosen approach |
| **User Guidelines** | Team conventions, security requirements |

---

## Required Clarifications

Ask about USER's context:

1. **Data source**: "What documents? (PDF, Word, images, web, database)"
2. **Scale**: "How much data? (MB/GB/TB)"
3. **Query type**: "What queries? (factual, comparative, analytical)"
4. **Deployment**: "Local, cloud, or hybrid?"
5. **Pattern**: "Simple RAG, or advanced (HyDE/CRAG/Agentic)?"

---

## RAG Pattern Selection

```
What's your use case?
│
├─ Simple Q&A over documents
│  └─ Basic RAG (see references/langchain-rag.md)
│
├─ Complex queries, poor retrieval accuracy
│  └─ HyDE - Hypothetical Document Embeddings
│     (see references/advanced-patterns.md#hyde)
│
├─ Need to validate/filter retrieved docs
│  └─ CRAG - Corrective RAG
│     (see references/advanced-patterns.md#crag)
│
├─ Multi-step reasoning, tool use, complex workflows
│  └─ Agentic RAG with LangGraph
│     (see references/advanced-patterns.md#agentic-rag)
│
└─ High recall + precision needed
   └─ Hybrid Search (dense + sparse)
      (see references/qdrant-integration.md#hybrid-search)
```

---

## Implementation Workflow

### Phase 1: Document Ingestion

1. **Load documents** - Use appropriate loader for format
2. **Split text** - Chunk with overlap for context preservation
3. **Generate embeddings** - Convert chunks to vectors
4. **Store in Qdrant** - Index with metadata

```python
# Quick start pattern
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore

# Load
loader = PyPDFLoader("document.pdf")
docs = loader.load()

# Split
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = splitter.split_documents(docs)

# Store
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vectorstore = QdrantVectorStore.from_documents(
    chunks, embeddings,
    location=":memory:",  # or url="http://localhost:6333"
    collection_name="my_docs"
)
```

### Phase 2: Retrieval Setup

Choose retrieval mode based on needs:

| Mode | Use When | Code |
|------|----------|------|
| **Dense** | Semantic similarity | `retrieval_mode=RetrievalMode.DENSE` |
| **Sparse** | Keyword matching | `retrieval_mode=RetrievalMode.SPARSE` |
| **Hybrid** | Best of both | `retrieval_mode=RetrievalMode.HYBRID` |

### Phase 3: RAG Chain/Agent

**Simple chain**:
```python
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o")
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=vectorstore.as_retriever(search_kwargs={"k": 5})
)
result = qa_chain.invoke({"query": "your question"})
```

**Agentic RAG** - See `references/advanced-patterns.md#agentic-rag`

---

## Chunking Strategy Guide

| Document Type | Chunk Size | Overlap | Splitter |
|---------------|------------|---------|----------|
| Technical docs | 1000-1500 | 200 | RecursiveCharacterTextSplitter |
| Legal/contracts | 500-800 | 100 | RecursiveCharacterTextSplitter |
| Code | By function | 50 | Language-specific splitter |
| Q&A/FAQ | Per question | 0 | Custom delimiter |

**Key principle**: Chunk overlap preserves context at boundaries.

---

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Poor retrieval | Chunks too large | Reduce chunk_size to 500-800 |
| Missing context | No overlap | Add chunk_overlap=100-200 |
| Slow queries | No index | Enable HNSW indexing in Qdrant |
| Hallucinations | Bad docs retrieved | Use CRAG pattern or add reranking |
| Wrong language | Embedding mismatch | Use multilingual embeddings |

---

## Output Checklist

Before delivering RAG implementation:

- [ ] Document loaders handle all required formats
- [ ] Chunking preserves semantic units
- [ ] Embeddings match document language
- [ ] Vector store properly indexed
- [ ] Retrieval returns relevant documents
- [ ] LLM generates grounded responses
- [ ] Error handling for missing docs/timeouts
- [ ] Metadata preserved for citations

---

## Reference Files

| File | When to Read |
|------|--------------|
| `references/langchain-rag.md` | Core RAG implementation details |
| `references/qdrant-integration.md` | Vector DB setup, search modes, filtering |
| `references/advanced-patterns.md` | HyDE, CRAG, Agentic RAG patterns |
| `references/document-processing.md` | Loaders, splitters, embeddings |
| `references/production-patterns.md` | Scaling, monitoring, best practices |
