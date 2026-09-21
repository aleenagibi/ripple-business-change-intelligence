---
title: Ripple
emoji: "〽️"
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: 6.28.0
python_version: 3.12.12
app_file: hf_app.py
pinned: false
---

# Ripple

**Semantic Business Impact Analysis using Hybrid Information Retrieval and Natural Language Processing**

Ripple is an Enterprise Business Change Intelligence Platform that predicts the business impact of requirement changes across enterprise documents.

## Architecture

- React + TypeScript frontend
- FastAPI backend
- PostgreSQL
- TF-IDF retrieval
- Dense semantic retrieval
- FAISS
- Knowledge Graph
- NetworkX
- Sentence Transformers
- Hugging Face ZeroGPU deployment

The production frontend is maintained separately from this Space.

## Deployment

This Space provides the Ripple backend runtime using Hugging Face ZeroGPU.

The existing Ripple API contract remains under:

`/api/...`

The React frontend communicates with this backend through the API.