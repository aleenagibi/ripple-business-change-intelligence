# Ripple

### Enterprise Business Change Intelligence Platform

**Ripple** analyzes how a change in a business requirement can propagate across enterprise documents, APIs, workflows, policies, systems, teams, and support knowledge.

It combines **Hybrid Information Retrieval (TF-IDF + Dense Semantic Retrieval), NLP, Entity Resolution, and Knowledge Graphs** to identify potentially affected business assets before implementation begins.

> **Core problem:** When one business requirement changes, what else in the organization could be affected?

---

## 🚀 Live Demo

**Frontend:** https://ripple-business-change-intelligence.vercel.app/

**Backend:** Deployed through Hugging Face Spaces

---

## 🎯 Problem

Enterprise systems rarely operate in isolation.

A change to one requirement can affect multiple interconnected artifacts:

```text
Requirement Change
       │
       ├── API
       ├── Business Process
       ├── Workflow
       ├── Policy
       ├── System
       ├── Documentation
       ├── Support Knowledge
       └── Team
```

Traditional keyword-based document search can identify documents containing similar words, but it does not adequately model the **semantic relationships and dependencies between business entities**.

Ripple addresses this by combining semantic retrieval with entity relationships and graph-based analysis.

---

# 🧠 How Ripple Works

```text
                  Business Requirement
                           │
                           ▼
                  Document Processing
                           │
                 ┌─────────┴─────────┐
                 │                   │
                 ▼                   ▼
          Entity Extraction    Relationship Extraction
                 │                   │
                 └─────────┬─────────┘
                           ▼
                  Canonical Entities
                           │
                           ▼
                 Hybrid Retrieval
                 ┌─────────┴─────────┐
                 │                   │
              TF-IDF             Dense Search
                 │                   │
                 └─────────┬─────────┘
                           ▼
                    Impact Analysis
                           │
                           ▼
                  Knowledge Graph
                           │
                           ▼
                 Affected Business Assets
```

---

# 🔍 Hybrid Information Retrieval

Ripple deliberately combines **lexical retrieval** and **semantic retrieval**.

### TF-IDF

TF-IDF is useful when exact terminology matters.

It helps retrieve documents containing:

* API names
* Error codes
* Business terminology
* System names
* Explicit requirements
* Domain-specific vocabulary

### Dense Semantic Retrieval

Sentence Transformers represent document chunks as dense vectors.

This allows Ripple to find semantically related content even when the wording differs.

For example:

```text
Requirement:
"Modify carrier-specific pricing rules."

Semantic matches may include:

"dynamic rate calculation"

"carrier pricing configuration"

"rate quote generation"
```

### Why Hybrid?

Neither retrieval method is sufficient on its own.

```text
TF-IDF
  │
  └── Strong lexical precision

Dense Retrieval
  │
  └── Strong semantic coverage

        ↓

Hybrid Retrieval
        ↓
Better evidence for impact analysis
```

Dense vectors are indexed using **FAISS** for efficient similarity search.

---

# 🕸️ Knowledge Graph

Ripple constructs an organization-level knowledge graph from extracted and canonicalized entities.

Example:

```text
                    Rate Engine
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
 RateEngine API   CarrierConnect   Pricing Policy
        │               │               │
        ▼               ▼               ▼
     System          Workflow          Team
```

This allows impact analysis to consider both:

* **Direct semantic matches**
* **Indirect relationships and dependencies**

The graph is implemented using **NetworkX**.

---

# 🧩 NLP Pipeline

Ripple processes enterprise documents through multiple NLP stages:

```text
Document
   │
   ▼
Text Extraction
   │
   ▼
Chunking
   │
   ▼
Entity Extraction
   │
   ▼
Relationship Extraction
   │
   ▼
Canonical Entity Resolution
   │
   ▼
Knowledge Graph
```

Entity categories include concepts such as:

* Business Concepts
* APIs
* Systems
* Workflows
* Policies
* Teams
* Organizations
* Technologies

Canonical entity resolution helps merge multiple mentions of the same underlying business entity.

---

# 📊 Impact Analysis

Impact analysis combines multiple signals rather than relying on a single similarity score.

The current pipeline considers:

* Hybrid retrieval relevance
* Entity similarity
* Canonical entity relationships
* Relationship confidence
* Knowledge graph connectivity
* Direct dependencies
* Indirect dependencies

Conceptually:

```text
                    Requirement
                         │
                         ▼
                 Retrieval Evidence
                         │
                         ▼
                  Business Entity
                         │
                         ▼
                  Entity Relations
                         │
                         ▼
                  Knowledge Graph
                         │
                         ▼
              Potentially Affected Assets
```

This provides an evidence-oriented basis for understanding **why an asset is considered relevant**.

---

# 🏗️ System Architecture

```text
┌──────────────────────────────────────────────┐
│                  React Frontend              │
│                                              │
│ Documents │ Impact Analysis │ Insights       │
└──────────────────────┬───────────────────────┘
                       │
                       │ REST API
                       ▼
┌──────────────────────────────────────────────┐
│                  FastAPI                     │
│                                              │
│ API Routes                                   │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│                  Services                    │
│                                              │
│ Document │ Retrieval │ Entity │ Impact       │
└──────────────────────┬───────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       NLP Engine  Retrieval     Graph Engine
                    Engines
          │            │            │
          │       ┌────┴────┐       │
          │       ▼         ▼       │
          │    TF-IDF    Dense      │
          │               FAISS     │
          │            │            │
          └────────────┼────────────┘
                       ▼
                 PostgreSQL
```

---

# 🛠️ Technology Stack

| Area               | Technologies                        |
| ------------------ | ----------------------------------- |
| Frontend           | React, TypeScript, Tailwind CSS     |
| UI / Visualization | React Flow, Framer Motion           |
| Backend            | Python, FastAPI                     |
| ORM                | SQLAlchemy                          |
| Database           | PostgreSQL                          |
| Migrations         | Alembic                             |
| NLP                | spaCy                               |
| Embeddings         | Sentence Transformers               |
| Lexical Retrieval  | TF-IDF, scikit-learn                |
| Vector Search      | FAISS                               |
| Knowledge Graph    | NetworkX                            |
| Deployment         | Vercel, Hugging Face Spaces, Docker |
| Version Control    | Git, GitHub                         |

---

# 🧱 Backend Architecture

The backend follows a layered architecture designed to keep responsibilities separated.

```text
API Layer
    │
    ▼
Service Layer
    │
    ▼
Engine Layer
    │
    ▼
Repository Layer
    │
    ▼
PostgreSQL
```

### API

Handles HTTP requests, validation, authentication, and response schemas.

### Services

Coordinates business workflows such as:

* Document processing
* Entity management
* Retrieval
* Impact analysis
* Knowledge graph construction

### Engines

Contains domain-specific processing logic:

* NLP Engine
* TF-IDF Engine
* Dense Retrieval Engine
* Hybrid Retrieval Engine
* Entity Extraction Engine
* Relationship Extraction Engine
* Canonical Resolution Engine
* Impact Analysis Engine
* Knowledge Graph Engine

### Repositories

Encapsulate database access and keep persistence logic separate from business logic.

---

# 🗄️ Data Model

Ripple persists the core business intelligence generated during document processing.

Conceptually:

```text
Organization
     │
     ▼
Documents
     │
     ▼
Document Chunks
     │
     ▼
Business Entity Mentions
     │
     ▼
Canonical Entities
     │
     ▼
Entity Relationships
```

This enables the system to retain relationships between source documents and the normalized business entities used during impact analysis.

---

# 📁 Project Structure

```text
Ripple/
│
├── app/
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── engines/
│   ├── models/
│   ├── repositories/
│   ├── schemas/
│   └── services/
│
├── alembic/
│   └── versions/
│
├── datasets/
│
├── frontend/
│   ├── public/
│   └── src/
│
├── tests/
│
├── hf_app.py
├── pyproject.toml
├── requirements.txt
├── uv.lock
└── README.md
```

---

# ⚙️ Engineering Highlights

### Modular NLP Architecture

NLP, retrieval, graph construction, and impact analysis are implemented as separate engines and services.

### Hybrid Retrieval

Combines sparse lexical retrieval with dense semantic retrieval instead of depending on a single search strategy.

### Canonical Entity Resolution

Normalizes repeated mentions of the same business entity across multiple documents.

### Graph-Based Dependency Analysis

Uses entity relationships to identify connected business assets beyond direct document similarity.

### Explainable Results

Impact scores are supported by retrieval evidence, entity relationships, and graph connectivity.

### Production-Oriented API

FastAPI provides typed REST endpoints with Pydantic schemas, authentication dependencies, service-layer processing, and PostgreSQL persistence.

---

# 🧪 Testing

The repository contains tests covering core components including:

* Change understanding
* Impact analysis
* Knowledge graph construction
* Relationship extraction
* Relationship pipelines
* Canonical entity reconciliation
* Knowledge graph services

The project also includes dedicated debugging and evaluation utilities for retrieval and impact-analysis behavior.

---

# 🚀 Deployment

### Frontend

The React frontend is deployed through **Vercel**.

### Backend

The NLP and impact-analysis backend supports deployment through **Hugging Face Spaces**, including GPU-backed execution for embedding-based workloads.

### Containerization

Docker configuration is included for reproducible deployment and local infrastructure setup.

---

# 📌 Current Features

* [x] Enterprise document ingestion
* [x] Document chunking
* [x] NLP entity extraction
* [x] Relationship extraction
* [x] Canonical entity resolution
* [x] TF-IDF retrieval
* [x] Dense semantic retrieval
* [x] FAISS vector search
* [x] Hybrid retrieval
* [x] Knowledge graph construction
* [x] Impact analysis
* [x] PostgreSQL persistence
* [x] FastAPI REST API
* [x] React frontend
* [x] Document indexing statistics
* [x] Production deployment

---

# 🎓 Project Context

**Academic Title**

> Semantic Business Impact Analysis using Hybrid Information Retrieval and Natural Language Processing

**Project Type**

Enterprise NLP / Information Retrieval / Business Intelligence

**Primary Objective**

To investigate how hybrid lexical-semantic retrieval combined with entity relationships and knowledge graphs can support semantic analysis of business change impact.

---


