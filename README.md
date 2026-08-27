# 🚀 SmartDocs AI — Enterprise Document Intelligence & Multi-Modal RAG Platform

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.38%2B-FF4B4B.svg?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector%20DB-DC2626.svg?logo=qdrant&logoColor=white)](https://qdrant.tech)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248.svg?logo=mongodb&logoColor=white)](https://mongodb.com)
[![AWS S3](https://img.shields.io/badge/AWS-S3%20Storage-FF9900.svg?logo=amazon-aws&logoColor=white)](https://aws.amazon.com/s3)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](https://docker.com)
[![Tests](https://img.shields.io/badge/pytest-100%25%20Passing-brightgreen.svg?logo=pytest&logoColor=white)](https://pytest.org)

**SmartDocs AI** is a production-ready, full-stack **Retrieval-Augmented Generation (RAG)** platform designed for conversational intelligence over complex multi-format documents (PDF, DOCX, TXT). 

Featuring **dynamic mathematical graph generation**, **AI text-to-image synthesis (FLUX/SD)**, **publication-grade document exports (PDF, Word, TXT)**, **scoped persistent memory threads**, and **granular Role-Based Access Control (RBAC)** with dynamic seniority protection.

---

## 🏛️ System Architecture
                            ┌─────────────────────────────────────────┐
                              │      Streamlit Frontend (Port 8501)     │
                              │  • Auto-Theme Dark/Light UI             │
                              │  • Dynamic Matplotlib Plot Renderer     │
                              │  • AI Image Diffusion Viewer            │
                              │  • 1-Click PDF / DOCX / TXT Exporter    │
                              └────────────────────┬────────────────────┘
                                                   │ HTTP / REST
                                                   ▼
                              ┌─────────────────────────────────────────┐
                              │       FastAPI Backend (Port 8000)       │
                              │  • JWT Auth & Dynamic RBAC Hierarchy    │
                              │  • Query Contextualization & Multi-Query│
                              │  • Document Ingestion & Chunking Engine │
                              └──────┬─────────────┬─────────────┬──────┘
                                     │             │             │
                ┌────────────────────┘             │             └───────────────────┐
                ▼                                  ▼                                 ▼
  ┌───────────────────────────┐      ┌───────────────────────────┐     ┌───────────────────────────┐
  │     AWS S3 Storage        │      │    Qdrant Vector DB       │     │     MongoDB Atlas         │
  │  • Original PDF/DOCX Docs │      │  • all-MiniLM-L6-v2 Embed │     │  • User Auth & Roles      │
  │  • Streamed File Downloads│      │  • HNSW Cosine Indexing   │     │  • Document Metadata      │
  │                           │      │  • Sub-25ms Top-K Search  │     │  • Scoped Chat Histories  │
  └───────────────────────────┘      └─────────────┬─────────────┘     └───────────────────────────┘
                                                   │ Top-K Chunks
                                                   ▼
                                     ┌───────────────────────────┐
                                     │      Groq LPU Engine      │
                                     │  • Ultra-fast LLM (450+t/s)│
                                     │  • Grounded Source Citations│
                                     │  • Multi-Turn Memory Synthesis│
                                     └───────────────────────────┘


---

## ✨ Key Features & Engineering Highlights

### 1. 🧠 Multi-Modal RAG & Mathematical Visualization Engine
- **Dynamic Python Graph Execution:** Automatically interprets mathematical equations from documents, executes `matplotlib` in isolated buffers, and provides **1-Click High-Res PNG Graph Downloads**.
- **Real-Time AI Image Synthesis:** Automatically converts descriptive scene prompts into photorealistic/artistic images via **FLUX / Stable Diffusion** pipelines.
- **LaTeX Math Support:** Real-time formatting of complex calculus, logarithms, and matrix equations into styled KaTeX math notation (`$ ... $` and `$$ ... $$`).

### 2. 📑 1-Click Publication-Grade Document Export
- **Export to PDF:** Converts synthesized AI research reports into formatted PDFs with custom headers, bordered data tables, and citation footers (zero missing-glyph black boxes).
- **Export to Word (.docx):** Generates structured Microsoft Word documents with native styled data tables, headings, and italicized source references.
- **Export to Text (.txt):** Clean ASCII-bordered report format.

### 3. 🛡️ Enterprise RBAC & Dynamic Seniority Protection
- **Granular Permissions:** Strict separation between `user` and `admin` roles.
- **Dynamic Seniority Verification:** Utilizes MongoDB `ObjectId.generation_time` UNIX timestamps so newer administrators cannot demote founding administrators—preventing hostile privilege takeover without hardcoded names.

### 4. 💬 Persistent Document-Scoped Memory Threads
- Chat sessions are independently scoped per document (or globally across all files) and persisted in MongoDB.
- Switching between documents automatically reloads the conversation history for that specific file.
- Persistent session storage across browser refreshes (**F5**).

---

## ⚡ Performance Benchmarks

Measured on local test suites over 10 iterations:

| Metric / Layer | Measured Performance | SLA Target |
| :--- | :--- | :--- |
| **GET /health API Latency** | `7.91 ms` | `< 50 ms` |
| **GET / Root Latency** | `4.56 ms` | `< 20 ms` |
| **Embedding Generation (`all-MiniLM-L6-v2`)** | `~12 - 18 ms` | `< 50 ms` |
| **Qdrant Vector Retrieval (Cosine HNSW)** | `~15 - 25 ms` | `< 50 ms` |
| **Groq LPU Inference Token Rate** | `~450+ tokens/sec` | `> 100 t/s` |

---

## 📁 Repository Structure

```text
SmartDocsAI/
├── backend/
│   ├── app/
│   │   ├── database.py         # MongoDB Atlas connection & collections
│   │   ├── main.py             # FastAPI REST endpoints & RBAC routes
│   │   ├── rag_service.py      # Multi-query RAG synthesis & Groq orchestration
│   │   ├── s3_storage.py       # AWS S3 file upload & streaming engine
│   │   ├── schemas.py          # Pydantic data validation models
│   │   ├── security.py         # Passlib Bcrypt hashing & JWT token handling
│   │   ├── utils_chunking.py   # Recursive text chunking with word boundary overlap
│   │   └── vector_db.py        # Qdrant collection management & vector search
│   ├── .env                    # Environment variables (Mongo, S3, Groq, Qdrant)
│   └── Dockerfile              # Container spec for FastAPI backend
│
├── frontend/
│   ├── api_client.py           # Clean Python requests SDK for backend APIs
│   ├── app.py                  # Streamlit UI with auto-theme detection
│   ├── export_utils.py         # PDF, Word (.docx), Matplotlib & AI Image engine
│   └── Dockerfile              # Container spec for Streamlit frontend
│
├── tests/
│   ├── __init__.py
│   ├── test_system.py          # FastAPI health & root endpoint tests
│   └── test_utils.py           # Text chunking, LaTeX math & extension unit tests
│
├── benchmark.py                # Automated system latency benchmark tool
├── docker-compose.yml          # Multi-service container orchestration
├── requirements.txt            # Project dependencies
└── README.md                   # Project documentation
