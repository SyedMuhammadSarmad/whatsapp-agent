# LangChain RAG Core Patterns

Complete reference for building RAG pipelines with LangChain.

---

## Architecture Overview

```
Documents → Load → Split → Embed → Store → Retrieve → Generate
```

Two phases:
1. **Indexing** (offline): Load → Split → Embed → Store
2. **Query** (runtime): Retrieve → Generate

---

## Document Loading

### Available Loaders

| Format | Loader | Install |
|--------|--------|---------|
| PDF | `PyPDFLoader` | `pip install pypdf` |
| Word | `Docx2txtLoader` | `pip install docx2txt` |
| HTML | `BSHTMLLoader` | `pip install beautifulsoup4` |
| Web | `WebBaseLoader` | `pip install beautifulsoup4` |
| CSV | `CSVLoader` | Built-in |
| JSON | `JSONLoader` | Built-in |
| Images | `UnstructuredImageLoader` | `pip install unstructured` |

### PDF Loading

```python
from langchain_community.document_loaders import PyPDFLoader

loader = PyPDFLoader("document.pdf")
pages = loader.load()  # List of Document objects

# Each page has:
# - page_content: str
# - metadata: dict (source, page number)
```

### Web Loading

```python
from langchain_community.document_loaders import WebBaseLoader
import bs4

loader = WebBaseLoader(
    web_paths=["https://example.com/article"],
    bs_kwargs={"parse_only": bs4.SoupStrainer(class_=("content", "article"))}
)
docs = loader.load()
```

### Directory Loading

```python
from langchain_community.document_loaders import DirectoryLoader

loader = DirectoryLoader(
    "./documents/",
    glob="**/*.pdf",
    loader_cls=PyPDFLoader,
    show_progress=True
)
docs = loader.load()
```

---

## Text Splitting

### RecursiveCharacterTextSplitter (Recommended)

Splits on multiple separators in priority order: `\n\n` → `\n` → ` ` → ``

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,      # Max characters per chunk
    chunk_overlap=200,    # Overlap between chunks
    length_function=len,
    add_start_index=True  # Track position in metadata
)

chunks = splitter.split_documents(docs)
```

### Language-Specific Splitters

```python
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    Language
)

# Python code
python_splitter = RecursiveCharacterTextSplitter.from_language(
    language=Language.PYTHON,
    chunk_size=2000,
    chunk_overlap=200
)

# Markdown
md_splitter = RecursiveCharacterTextSplitter.from_language(
    language=Language.MARKDOWN,
    chunk_size=1000,
    chunk_overlap=100
)
```

### Chunking Guidelines

| Scenario | chunk_size | chunk_overlap |
|----------|------------|---------------|
| General documents | 1000 | 200 |
| Dense technical | 500-800 | 100-150 |
| Conversational | 1500-2000 | 300 |
| Code | 2000 | 200 |

**Rule**: Overlap should be 10-20% of chunk_size.

---

## Embeddings

### OpenAI Embeddings

```python
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",  # or "text-embedding-3-large"
    # dimensions=1536  # Optional: reduce dimensions
)

# Single text
vector = embeddings.embed_query("What is RAG?")

# Multiple texts
vectors = embeddings.embed_documents(["doc1", "doc2"])
```

### Model Comparison

| Model | Dimensions | Cost | Best For |
|-------|------------|------|----------|
| text-embedding-3-small | 1536 | Low | General use |
| text-embedding-3-large | 3072 | Medium | High accuracy |
| text-embedding-ada-002 | 1536 | Low | Legacy |

### Alternative Providers

```python
# HuggingFace (free, local)
from langchain_huggingface import HuggingFaceEmbeddings
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Cohere
from langchain_cohere import CohereEmbeddings
embeddings = CohereEmbeddings(model="embed-english-v3.0")
```

---

## Vector Store Operations

### Creating Store

```python
from langchain_qdrant import QdrantVectorStore

# From documents (creates collection)
vectorstore = QdrantVectorStore.from_documents(
    documents=chunks,
    embedding=embeddings,
    location=":memory:",
    collection_name="my_docs"
)

# From existing collection
vectorstore = QdrantVectorStore.from_existing_collection(
    embedding=embeddings,
    collection_name="my_docs",
    url="http://localhost:6333"
)
```

### Adding Documents

```python
# Add more documents to existing store
vectorstore.add_documents(new_chunks)

# Add with custom IDs
vectorstore.add_documents(
    new_chunks,
    ids=["doc1", "doc2", "doc3"]
)
```

---

## Retrieval

### Basic Retrieval

```python
# As retriever
retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 5}
)
docs = retriever.invoke("query")

# Direct search
docs = vectorstore.similarity_search("query", k=5)

# With scores
docs_with_scores = vectorstore.similarity_search_with_score("query", k=5)
```

### Search Types

| Type | Description | Use Case |
|------|-------------|----------|
| `similarity` | Cosine similarity | General |
| `mmr` | Maximal Marginal Relevance | Diverse results |
| `similarity_score_threshold` | Filter by score | High precision |

```python
# MMR for diversity
retriever = vectorstore.as_retriever(
    search_type="mmr",
    search_kwargs={"k": 5, "fetch_k": 20}
)

# Score threshold
retriever = vectorstore.as_retriever(
    search_type="similarity_score_threshold",
    search_kwargs={"score_threshold": 0.8}
)
```

---

## RAG Chains

### Simple QA Chain

```python
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o", temperature=0)

qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",  # stuff, map_reduce, refine, map_rerank
    retriever=retriever,
    return_source_documents=True
)

result = qa_chain.invoke({"query": "What is the main topic?"})
print(result["result"])
print(result["source_documents"])
```

### Custom Prompt

```python
from langchain.prompts import PromptTemplate

template = """Use the following context to answer the question.
If you don't know, say "I don't know."

Context: {context}

Question: {question}

Answer:"""

prompt = PromptTemplate(
    template=template,
    input_variables=["context", "question"]
)

qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    chain_type_kwargs={"prompt": prompt}
)
```

### LCEL Chain (Modern Approach)

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

prompt = ChatPromptTemplate.from_template(
    "Answer based on context:\n\n{context}\n\nQuestion: {question}"
)

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

answer = chain.invoke("What is RAG?")
```

---

## Conversation Memory

```python
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory

memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True,
    output_key="answer"
)

conv_chain = ConversationalRetrievalChain.from_llm(
    llm=llm,
    retriever=retriever,
    memory=memory,
    return_source_documents=True
)

# First question
result = conv_chain.invoke({"question": "What is the document about?"})

# Follow-up (uses history)
result = conv_chain.invoke({"question": "Can you elaborate on that?"})
```

---

## Error Handling

```python
from langchain.callbacks import get_openai_callback

try:
    with get_openai_callback() as cb:
        result = qa_chain.invoke({"query": question})
        print(f"Tokens used: {cb.total_tokens}")
        print(f"Cost: ${cb.total_cost:.4f}")
except Exception as e:
    if "rate_limit" in str(e).lower():
        # Implement backoff
        pass
    elif "context_length" in str(e).lower():
        # Reduce chunk size or k value
        pass
    raise
```

---

## Best Practices

### Do

- Use `chunk_overlap` to preserve context
- Track metadata (source, page) for citations
- Use MMR for diverse retrieval
- Monitor token usage
- Test with representative queries

### Don't

- Chunk too large (>2000 chars)
- Ignore embedding model language support
- Skip metadata preservation
- Use same chunk size for all content types
- Forget to handle empty results
