# Document Processing Reference

Comprehensive guide to document loading, parsing, and chunking for RAG.

---

## Document Loaders by Format

### PDF Documents

```python
# Basic PDF loading
from langchain_community.document_loaders import PyPDFLoader

loader = PyPDFLoader("document.pdf")
pages = loader.load()  # One Document per page

# With OCR for scanned PDFs
from langchain_community.document_loaders import UnstructuredPDFLoader

loader = UnstructuredPDFLoader(
    "scanned.pdf",
    mode="elements",  # Preserves structure
    strategy="hi_res"  # Better OCR
)

# PDF with table extraction
from langchain_community.document_loaders import PDFPlumberLoader

loader = PDFPlumberLoader("tables.pdf")
pages = loader.load()  # Better table handling
```

**Installation**:
```bash
pip install pypdf unstructured pdfplumber
# For OCR: pip install pytesseract pdf2image
```

### Word Documents

```python
from langchain_community.document_loaders import Docx2txtLoader

loader = Docx2txtLoader("document.docx")
docs = loader.load()

# Preserves more formatting
from langchain_community.document_loaders import UnstructuredWordDocumentLoader

loader = UnstructuredWordDocumentLoader(
    "document.docx",
    mode="elements"
)
```

### Images (OCR)

```python
from langchain_community.document_loaders import UnstructuredImageLoader

loader = UnstructuredImageLoader(
    "document.png",
    mode="elements"
)
docs = loader.load()

# For multiple images
from langchain_community.document_loaders import DirectoryLoader

loader = DirectoryLoader(
    "./images/",
    glob="**/*.{png,jpg,jpeg}",
    loader_cls=UnstructuredImageLoader
)
```

**Requirements**:
```bash
pip install unstructured pytesseract pillow
# System: tesseract-ocr
```

### Web Pages

```python
from langchain_community.document_loaders import WebBaseLoader
import bs4

# Basic loading
loader = WebBaseLoader("https://example.com/article")

# With HTML parsing
loader = WebBaseLoader(
    web_paths=["https://example.com/article"],
    bs_kwargs={
        "parse_only": bs4.SoupStrainer(
            class_=["article-content", "main-text"]
        )
    }
)

# Multiple URLs
loader = WebBaseLoader([
    "https://example.com/page1",
    "https://example.com/page2"
])
```

### CSV/Excel

```python
# CSV
from langchain_community.document_loaders import CSVLoader

loader = CSVLoader(
    "data.csv",
    csv_args={"delimiter": ","},
    source_column="id"  # Use as metadata
)

# Excel
from langchain_community.document_loaders import UnstructuredExcelLoader

loader = UnstructuredExcelLoader("data.xlsx", mode="elements")
```

### JSON

```python
from langchain_community.document_loaders import JSONLoader

# Simple JSON array
loader = JSONLoader(
    "data.json",
    jq_schema=".[]",
    text_content=False
)

# Nested JSON
loader = JSONLoader(
    "data.json",
    jq_schema=".records[].content",
    metadata_func=lambda record, metadata: {
        **metadata,
        "source": record.get("source"),
        "date": record.get("date")
    }
)
```

### Directory of Mixed Files

```python
from langchain_community.document_loaders import DirectoryLoader

# All PDFs
loader = DirectoryLoader(
    "./documents/",
    glob="**/*.pdf",
    loader_cls=PyPDFLoader,
    show_progress=True,
    use_multithreading=True
)

# Multiple types with auto-detection
from langchain_community.document_loaders import UnstructuredFileLoader

loader = DirectoryLoader(
    "./documents/",
    glob="**/*.*",
    loader_cls=UnstructuredFileLoader
)
```

---

## Text Splitting Strategies

### RecursiveCharacterTextSplitter (Default)

Splits hierarchically: paragraphs → sentences → words.

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", " ", ""]
)

chunks = splitter.split_documents(docs)
```

### Semantic Chunking

Group by semantic similarity.

```python
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings()

splitter = SemanticChunker(
    embeddings=embeddings,
    breakpoint_threshold_type="percentile",
    breakpoint_threshold_amount=95
)

chunks = splitter.split_documents(docs)
```

### Token-Based Splitting

For models with token limits.

```python
from langchain_text_splitters import TokenTextSplitter

splitter = TokenTextSplitter(
    chunk_size=500,      # Tokens, not characters
    chunk_overlap=50,
    encoding_name="cl100k_base"  # GPT-4 encoding
)
```

### Markdown Splitting

Preserves document structure.

```python
from langchain_text_splitters import MarkdownHeaderTextSplitter

headers_to_split = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3")
]

splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split)
chunks = splitter.split_text(markdown_text)
# Chunks have header metadata
```

### Code Splitting

Language-aware splitting.

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language

# Python
python_splitter = RecursiveCharacterTextSplitter.from_language(
    language=Language.PYTHON,
    chunk_size=2000,
    chunk_overlap=200
)

# JavaScript
js_splitter = RecursiveCharacterTextSplitter.from_language(
    language=Language.JS,
    chunk_size=2000,
    chunk_overlap=200
)

# Supported: PYTHON, JS, TS, JAVA, GO, RUST, CPP, CSHARP, etc.
```

---

## Chunking Guidelines

### Size Selection

| Content Type | chunk_size | chunk_overlap | Reason |
|--------------|------------|---------------|--------|
| General text | 1000 | 200 | Balance context/precision |
| Technical docs | 500-800 | 100 | Dense information |
| Legal/contracts | 500 | 100 | Precise language |
| Code | 2000 | 200 | Function-level units |
| Q&A/FAQ | Per item | 0 | Natural boundaries |
| Conversations | 1500 | 300 | Context flow |

### Overlap Calculation

**Rule**: Overlap = 10-20% of chunk_size

```python
chunk_size = 1000
chunk_overlap = int(chunk_size * 0.2)  # 200
```

### Metadata Preservation

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    add_start_index=True  # Track position
)

# Custom metadata
for i, chunk in enumerate(chunks):
    chunk.metadata["chunk_index"] = i
    chunk.metadata["total_chunks"] = len(chunks)
```

---

## Embedding Models

### Comparison

| Model | Dimensions | Quality | Cost | Speed |
|-------|------------|---------|------|-------|
| text-embedding-3-small | 1536 | Good | Low | Fast |
| text-embedding-3-large | 3072 | Best | Medium | Medium |
| all-MiniLM-L6-v2 | 384 | Good | Free | Fast |
| all-mpnet-base-v2 | 768 | Better | Free | Medium |
| multilingual-e5-large | 1024 | Best multilingual | Free | Slow |

### OpenAI Embeddings

```python
from langchain_openai import OpenAIEmbeddings

# Standard
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Reduced dimensions (saves storage)
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large",
    dimensions=1024  # Reduce from 3072
)
```

### Local Embeddings (Free)

```python
from langchain_huggingface import HuggingFaceEmbeddings

# General purpose
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# Higher quality
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2"
)

# Multilingual
embeddings = HuggingFaceEmbeddings(
    model_name="intfloat/multilingual-e5-large"
)
```

### Caching Embeddings

```python
from langchain.embeddings import CacheBackedEmbeddings
from langchain.storage import LocalFileStore

store = LocalFileStore("./embedding_cache")

cached_embeddings = CacheBackedEmbeddings.from_bytes_store(
    underlying_embeddings=embeddings,
    document_embedding_cache=store,
    namespace="my_embeddings"
)
```

---

## Processing Pipeline

### Complete Example

```python
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore

# 1. Load documents
loader = DirectoryLoader(
    "./documents/",
    glob="**/*.pdf",
    loader_cls=PyPDFLoader,
    show_progress=True
)
docs = loader.load()

# 2. Add custom metadata
for doc in docs:
    doc.metadata["ingestion_date"] = datetime.now().isoformat()
    doc.metadata["corpus"] = "technical_docs"

# 3. Split
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    add_start_index=True
)
chunks = splitter.split_documents(docs)

# 4. Embed and store
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vectorstore = QdrantVectorStore.from_documents(
    chunks,
    embeddings,
    url="http://localhost:6333",
    collection_name="technical_docs"
)

print(f"Indexed {len(chunks)} chunks from {len(docs)} documents")
```

### Batch Processing (Large Scale)

```python
from tqdm import tqdm

BATCH_SIZE = 100

for i in tqdm(range(0, len(chunks), BATCH_SIZE)):
    batch = chunks[i:i + BATCH_SIZE]
    vectorstore.add_documents(batch)
```

---

## Quality Checks

### Chunk Quality

```python
def check_chunk_quality(chunks):
    issues = []

    for i, chunk in enumerate(chunks):
        # Too short
        if len(chunk.page_content) < 100:
            issues.append(f"Chunk {i}: Too short ({len(chunk.page_content)} chars)")

        # Too long
        if len(chunk.page_content) > 2000:
            issues.append(f"Chunk {i}: Too long ({len(chunk.page_content)} chars)")

        # Missing metadata
        if "source" not in chunk.metadata:
            issues.append(f"Chunk {i}: Missing source metadata")

    return issues
```

### Embedding Sanity Check

```python
def test_embeddings(embeddings, test_texts):
    """Verify embeddings work correctly."""
    vectors = embeddings.embed_documents(test_texts)

    assert len(vectors) == len(test_texts)
    assert all(len(v) > 0 for v in vectors)
    assert all(isinstance(v[0], float) for v in vectors)

    # Check similarity makes sense
    from numpy import dot
    from numpy.linalg import norm

    cosine_sim = lambda a, b: dot(a, b) / (norm(a) * norm(b))

    # Similar texts should have high similarity
    sim = cosine_sim(vectors[0], vectors[1])
    print(f"Similarity between similar texts: {sim:.3f}")
```
