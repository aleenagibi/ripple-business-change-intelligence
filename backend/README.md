# Ripple

### Enterprise Business Change Intelligence

> **Understand what a business change will impact — before implementation begins.**

Ripple analyzes proposed business requirement changes and identifies the potentially affected **business concepts, APIs, workflows, policies, documentation, support knowledge, modules, and teams**.

It combines **Hybrid Information Retrieval + NLP + Knowledge Graphs** to move beyond simple search and reason about the downstream impact of change.

---

## ⚡ How Ripple Works

```text
Business Requirement
        ↓
Hybrid Retrieval
 TF-IDF + Dense Search
        ↓
Business Concepts
        ↓
Knowledge Graph
        ↓
Impact Propagation
        ↓
Affected Artifacts & Teams
        ↓
Impact Graph
````

### Example

**Change:**

> Replace the existing Payment Gateway.

**Ripple identifies:**

```text
Payment Gateway
   ├── Payment API
   ├── Checkout Workflow
   ├── Refund Service
   ├── Payment Policy
   ├── Support Documentation
   └── Engineering Team
```

---

## 🧠 Core Technology

| Layer           | Technology                     |
| --------------- | ------------------------------ |
| API             | FastAPI                        |
| NLP             | spaCy                          |
| Retrieval       | TF-IDF + Sentence Transformers |
| Vector Search   | FAISS                          |
| Database        | PostgreSQL                     |
| Knowledge Graph | NetworkX                       |
| Frontend        | React + TypeScript             |
| Styling         | Tailwind CSS                   |
| Graph UI        | React Flow                     |

---

## 🔍 Why Ripple?

Traditional search answers:

> **"Where is this mentioned?"**

Ripple aims to answer:

> **"What will this change affect, and who will be impacted?"**

---

## 🚧 Status

**Backend foundation in development**

Currently implemented:

* Document ingestion & extraction
* Intelligent chunking
* Business entity extraction
* TF-IDF retrieval
* Dense semantic retrieval
* Hybrid retrieval
* Relationship extraction
* Knowledge graph foundation

Next: **Business Impact Analysis & Impact Scoring**

---

### Academic Project

**Semantic Business Impact Analysis using Hybrid Information Retrieval and Natural Language Processing**


