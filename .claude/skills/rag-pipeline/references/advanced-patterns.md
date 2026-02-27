# Advanced RAG Patterns

HyDE, CRAG, and Agentic RAG implementations with LangChain and LangGraph.

---

## HyDE - Hypothetical Document Embeddings

**Problem**: Query embeddings often don't match document embeddings well.
**Solution**: Generate hypothetical answer, embed that instead.

### How It Works

```
Query → LLM generates hypothetical answer → Embed answer → Search → Retrieve real docs
```

### Implementation

```python
from langchain.chains import HypotheticalDocumentEmbedder
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

llm = ChatOpenAI(model="gpt-4o", temperature=0)
base_embeddings = OpenAIEmbeddings()

# Create HyDE embeddings
hyde_embeddings = HypotheticalDocumentEmbedder.from_llm(
    llm=llm,
    base_embeddings=base_embeddings,
    prompt_key="web_search"  # or "qa" for Q&A style
)

# Use in vector store
vectorstore = QdrantVectorStore.from_documents(
    docs,
    embedding=hyde_embeddings,
    collection_name="hyde_docs"
)

# Query uses hypothetical document for retrieval
results = vectorstore.similarity_search("What are the benefits of RAG?")
```

### Custom HyDE Prompt

```python
from langchain.prompts import PromptTemplate

hyde_prompt = PromptTemplate(
    input_variables=["question"],
    template="""Write a detailed paragraph answering this question.
Write as if you are an expert with complete knowledge.

Question: {question}

Detailed Answer:"""
)

hyde_embeddings = HypotheticalDocumentEmbedder.from_llm(
    llm=llm,
    base_embeddings=base_embeddings,
    custom_prompt=hyde_prompt
)
```

### Multiple Hypothetical Documents

```python
# Generate multiple hypotheticals and average embeddings
hyde_embeddings = HypotheticalDocumentEmbedder.from_llm(
    llm=llm,
    base_embeddings=base_embeddings,
    num_hypothetical_documents=5  # Default is 1
)
```

### When to Use HyDE

| Use | Don't Use |
|-----|-----------|
| Complex analytical queries | Simple factual lookups |
| Poor baseline retrieval | Already good retrieval |
| Domain-specific jargon mismatch | Direct keyword queries |
| Conceptual questions | Exact phrase searches |

### Trade-offs

- **Pros**: Better semantic matching, handles query-document gap
- **Cons**: +1 LLM call latency, 25-40% slower, may hallucinate

---

## CRAG - Corrective RAG

**Problem**: Retrieved documents may be irrelevant or wrong.
**Solution**: Grade documents, rewrite query if needed, use web search fallback.

### Architecture

```
Query → Retrieve → Grade Docs → Branch:
  ├─ All Relevant → Generate
  ├─ Some Relevant → Filter + Generate
  └─ None Relevant → Rewrite Query → Web Search → Generate
```

### LangGraph Implementation

```python
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_core.documents import Document

class GraphState(TypedDict):
    question: str
    documents: List[Document]
    generation: str
    web_search_needed: bool

# Node: Retrieve documents
def retrieve(state: GraphState) -> GraphState:
    question = state["question"]
    documents = retriever.invoke(question)
    return {"documents": documents, "question": question}

# Node: Grade documents for relevance
def grade_documents(state: GraphState) -> GraphState:
    question = state["question"]
    documents = state["documents"]

    grader_prompt = """You are a grader assessing relevance of a document to a question.
    Document: {document}
    Question: {question}
    Is this document relevant? Answer 'yes' or 'no'."""

    filtered_docs = []
    web_search_needed = True

    for doc in documents:
        score = llm.invoke(grader_prompt.format(
            document=doc.page_content,
            question=question
        ))
        if "yes" in score.content.lower():
            filtered_docs.append(doc)
            web_search_needed = False

    return {
        "documents": filtered_docs,
        "question": question,
        "web_search_needed": web_search_needed
    }

# Node: Rewrite query for web search
def rewrite_query(state: GraphState) -> GraphState:
    question = state["question"]

    rewrite_prompt = f"""Rewrite this question for a web search.
    Original: {question}
    Better search query:"""

    new_question = llm.invoke(rewrite_prompt).content
    return {"question": new_question, "documents": state["documents"]}

# Node: Web search
def web_search(state: GraphState) -> GraphState:
    question = state["question"]

    # Use Tavily or other web search
    from langchain_community.tools.tavily_search import TavilySearchResults
    search = TavilySearchResults(max_results=3)
    results = search.invoke(question)

    web_docs = [
        Document(page_content=r["content"], metadata={"source": r["url"]})
        for r in results
    ]

    return {"documents": state["documents"] + web_docs, "question": question}

# Node: Generate answer
def generate(state: GraphState) -> GraphState:
    question = state["question"]
    documents = state["documents"]

    context = "\n\n".join(doc.page_content for doc in documents)

    generation = llm.invoke(f"""Answer based on context:
    Context: {context}
    Question: {question}
    Answer:""").content

    return {"generation": generation, **state}

# Routing logic
def route_after_grading(state: GraphState) -> str:
    if state["web_search_needed"]:
        return "rewrite"
    return "generate"

# Build graph
workflow = StateGraph(GraphState)

workflow.add_node("retrieve", retrieve)
workflow.add_node("grade", grade_documents)
workflow.add_node("rewrite", rewrite_query)
workflow.add_node("web_search", web_search)
workflow.add_node("generate", generate)

workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "grade")
workflow.add_conditional_edges(
    "grade",
    route_after_grading,
    {"rewrite": "rewrite", "generate": "generate"}
)
workflow.add_edge("rewrite", "web_search")
workflow.add_edge("web_search", "generate")
workflow.add_edge("generate", END)

app = workflow.compile()

# Run
result = app.invoke({"question": "What is CRAG?"})
print(result["generation"])
```

### Grading Prompts

```python
# Binary grading
BINARY_GRADER = """Document: {document}
Question: {question}
Is this document relevant to answering the question? (yes/no)"""

# Scored grading
SCORED_GRADER = """Document: {document}
Question: {question}
Rate relevance 1-5:
1 = Not relevant
3 = Somewhat relevant
5 = Highly relevant
Score:"""
```

### When to Use CRAG

| Use | Don't Use |
|-----|-----------|
| Unreliable retrieval | Trusted document corpus |
| Need high accuracy | Latency-critical apps |
| Mixed quality sources | Simple Q&A |
| Factual queries | Creative tasks |

---

## Agentic RAG

**Problem**: Static retrieval doesn't handle complex, multi-step queries.
**Solution**: LLM agent decides when/how to retrieve dynamically.

### Architecture

```
Query → Agent decides:
  ├─ Simple → Answer directly
  ├─ Needs docs → Retrieve → Answer
  ├─ Multiple sources → Retrieve from each → Synthesize
  └─ Complex → Multi-step retrieval → Reason → Answer
```

### LangGraph Agentic RAG

```python
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

# Define retrieval tools
@tool
def search_technical_docs(query: str) -> str:
    """Search technical documentation for engineering questions."""
    docs = technical_retriever.invoke(query)
    return "\n\n".join(doc.page_content for doc in docs)

@tool
def search_policy_docs(query: str) -> str:
    """Search company policies and HR documents."""
    docs = policy_retriever.invoke(query)
    return "\n\n".join(doc.page_content for doc in docs)

@tool
def web_search(query: str) -> str:
    """Search the web for current information."""
    from langchain_community.tools.tavily_search import TavilySearchResults
    search = TavilySearchResults(max_results=3)
    results = search.invoke(query)
    return "\n\n".join(r["content"] for r in results)

# Create agent
tools = [search_technical_docs, search_policy_docs, web_search]
llm = ChatOpenAI(model="gpt-4o").bind_tools(tools)

# Agent node
def agent(state: AgentState):
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

# Tool execution node
def tool_node(state: AgentState):
    last_message = state["messages"][-1]
    tool_calls = last_message.tool_calls

    results = []
    for call in tool_calls:
        tool = {"search_technical_docs": search_technical_docs,
                "search_policy_docs": search_policy_docs,
                "web_search": web_search}[call["name"]]
        result = tool.invoke(call["args"])
        results.append({"role": "tool", "content": result, "tool_call_id": call["id"]})

    return {"messages": results}

# Routing
def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END

# Build graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent)
workflow.add_node("tools", tool_node)

workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
workflow.add_edge("tools", "agent")

app = workflow.compile()

# Run
result = app.invoke({
    "messages": [{"role": "user", "content": "Compare our vacation policy with industry standards"}]
})
```

### Adaptive RAG Pattern

Route queries to appropriate strategy:

```python
def route_query(state: AgentState) -> str:
    """Route based on query complexity."""
    query = state["messages"][-1].content

    # Use LLM to classify
    classification = llm.invoke(f"""Classify this query:
    Query: {query}

    Types:
    - simple: Can answer from general knowledge
    - retrieval: Needs document search
    - multi_source: Needs multiple document sources
    - web: Needs current web information

    Type:""").content.strip().lower()

    return classification

workflow.add_conditional_edges(
    "classify",
    route_query,
    {
        "simple": "direct_answer",
        "retrieval": "single_retrieval",
        "multi_source": "multi_retrieval",
        "web": "web_search"
    }
)
```

### Self-Reflective RAG

Agent checks its own answers:

```python
def check_answer(state: AgentState) -> str:
    """Check if answer has hallucinations or is incomplete."""
    messages = state["messages"]
    answer = messages[-1].content
    question = messages[0].content

    check_prompt = f"""Question: {question}
    Answer: {answer}

    Check:
    1. Does the answer address the question?
    2. Is there any unsupported claim?
    3. Is information missing?

    Verdict (good/needs_improvement):"""

    verdict = llm.invoke(check_prompt).content.strip().lower()

    if "good" in verdict:
        return END
    return "retry_with_more_context"
```

### When to Use Agentic RAG

| Use | Don't Use |
|-----|-----------|
| Complex multi-step queries | Simple lookups |
| Multiple data sources | Single corpus |
| Dynamic tool selection | Static pipelines |
| Reasoning required | Direct extraction |

---

## Pattern Comparison

| Pattern | Latency | Accuracy | Complexity | Best For |
|---------|---------|----------|------------|----------|
| Basic RAG | Low | Medium | Low | Simple Q&A |
| HyDE | Medium | High | Low | Semantic gap |
| CRAG | High | Very High | Medium | Unreliable retrieval |
| Agentic | Variable | Highest | High | Complex reasoning |

---

## Combining Patterns

```python
# CRAG + Agentic: Agent with self-correction
@tool
def retrieve_with_grading(query: str) -> str:
    """Retrieve and grade documents, fallback to web if needed."""
    docs = retriever.invoke(query)

    relevant = [d for d in docs if grade_document(d, query)]

    if not relevant:
        # Rewrite and web search
        new_query = rewrite_query(query)
        return web_search(new_query)

    return "\n\n".join(d.page_content for d in relevant)

# HyDE + Agentic: Agent uses HyDE embeddings
hyde_retriever = vectorstore.as_retriever()
hyde_retriever.search_kwargs["embedding"] = hyde_embeddings
```
