# Mistri.AI - Core RAG Pipeline

## 📋 Overview

This is the core RAG (Retrieval-Augmented Generation) pipeline for **Mistri.AI**, the "Stack Overflow for Hardware Repair". The system uses AWS Bedrock for embeddings and text generation, with a local FAISS vector store (designed to be replaced with Amazon Aurora pgvector in production).

## 🏗️ Architecture

```
┌─────────────────┐
│  Error CSV      │
│  (Ground Truth) │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  rag_ingest.py          │
│  - Read CSV             │
│  - Format text chunks   │
│  - Bedrock embeddings   │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  FAISS Vector Store     │
│  (Local - Mock Aurora)  │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  rag_retrieve.py        │
│  - Semantic search      │
│  - Top-K retrieval      │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  FastAPI /diagnose      │
│  - Accept text + image  │
│  - Return diagnosis     │
└─────────────────────────┘
```

## 📦 Files Created

### 1. `backend/config.py`
- **Purpose**: AWS configuration singleton
- **Features**:
  - Loads credentials from `.env`
  - Validates required environment variables
  - Defines Bedrock model IDs:
    - Embeddings: `amazon.titan-embed-text-v1` (1536 dimensions)
    - LLM: `anthropic.claude-3-sonnet-20240229-v1:0`

### 2. `backend/rag_ingest.py`
- **Purpose**: Ingestion pipeline for error codes
- **Features**:
  - Reads `data/error_codes/lg_error.csv`
  - Formats each row as: `"Error {code}: {name} - {description}"`
  - Generates embeddings via Bedrock Titan
  - Stores in FAISS index with metadata
  - **Production TODO**: Replace FAISS with Aurora pgvector (commented in code)

### 3. `backend/rag_retrieve.py`
- **Purpose**: Semantic search over error codes
- **Features**:
  - `search_manual(query_text, query_image_bytes, top_k=3)`
  - Embeds user query using Bedrock
  - Searches FAISS for top-K matches
  - Returns structured results with similarity scores
  - **Production TODO**: Aurora connection pool (commented in code)

### 4. `backend/main.py`
- **Purpose**: FastAPI REST API
- **Endpoints**:
  - `GET /` - Health check
  - `GET /health` - Detailed health status
  - `POST /diagnose` - Main diagnosis endpoint
    - Accepts: `text` (required), `image` (optional)
    - Returns: JSON matching "Senior Mistri" persona format
- **Features**:
  - CORS middleware
  - Image processing with Pillow
  - Error-specific repair steps
  - Global exception handling

## 🚀 Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure AWS Credentials
Create a `.env` file (use `.env.example` as template):
```bash
cp .env.example .env
```

Edit `.env`:
```env
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1
```

### 3. Ingest Error Codes
```bash
python backend/rag_ingest.py
```

Expected output:
```
INFO - Loaded 11 error codes from data/error_codes/lg_error.csv
INFO - Processing 1/11: IE
...
INFO - ✅ Ingestion complete! Indexed 11 error codes.
```

### 4. Start the API Server
```bash
uvicorn backend.main:app --reload
```

Or:
```bash
python backend/main.py
```

### 5. Test the API
```bash
curl -X POST http://localhost:8000/diagnose \
     -F "text=washing machine not draining"
```

Expected response:
```json
{
  "diagnosis": "The DE error means: DRAIN ERROR. Not fully drained within 10 minutes.",
  "safety_warning": "⚠️ SAFETY FIRST: Unplug the machine...",
  "steps": [
    "Check the drain hose for clogs",
    "Inspect the drain pump filter...",
    ...
  ],
  "matched_errors": [
    {"code": "DE", "name": "DRAIN ERROR", "similarity": 0.89}
  ],
  "confidence_score": 0.89
}
```

## 🔧 AWS Bedrock Models Used

| Purpose | Model ID | Dimensions |
|---------|----------|------------|
| **Embeddings** | `amazon.titan-embed-text-v1` | 1536 |
| **Text Generation** | `anthropic.claude-3-sonnet-20240229-v1:0` | N/A |

## 🗄️ Migration to Amazon Aurora

The code includes `TODO` comments marking where FAISS should be replaced with Aurora pgvector:

**In `rag_ingest.py`:**
```python
# TODO: Replace with Amazon Aurora pgvector connection
# Example Aurora setup:
# import psycopg2
# conn = psycopg2.connect(...)
# cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
```

**In `rag_retrieve.py`:**
```python
# TODO: Replace with Amazon Aurora pgvector query
# cursor.execute("""
#     SELECT id, code, embedding <=> %s AS distance
#     FROM error_embeddings
#     ORDER BY distance LIMIT %s;
# """)
```

## 🛡️ Error Handling

All Bedrock API calls are wrapped in try/except blocks:
- Configuration validation on startup
- Graceful degradation for missing images
- Detailed logging for debugging
- HTTP exception handling in FastAPI

## 📝 Next Steps

1. **Test locally** with the commands above
2. **Add more error codes** to `data/error_codes/`
3. **Enhance with Claude 3 Sonnet** for dynamic repair step generation
4. **Deploy to AWS** and migrate to Aurora pgvector
5. **Add PDF manual ingestion** for richer context

## 🎯 Production Checklist

- [ ] Replace FAISS with Amazon Aurora pgvector
- [ ] Set up Aurora Serverless v2 cluster
- [ ] Configure VPC and security groups
- [ ] Implement connection pooling
- [ ] Add CloudWatch monitoring
- [ ] Restrict CORS origins
- [ ] Add authentication (API keys or Cognito)
- [ ] Implement rate limiting
- [ ] Add PDF manual chunking pipeline
