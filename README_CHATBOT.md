# 🤖 NexusAI Business Chatbot

**AI-powered business advisor for the NexusAI platform — specialized in startup validation and entrepreneurial intelligence.**

---

## 📌 Role

The chatbot is **not** a generic assistant. It acts as:

- **Business consultant** — analyzes startup viability scores
- **Startup advisor** — provides actionable recommendations
- **Pedagogical AI assistant** — explains scores and methodology
- **AI module orchestrator** — calls existing FastAPI services automatically

It understands user intent, calls the appropriate AI endpoints, retrieves knowledge from internal documents (RAG), and generates a comprehensive response via an external LLM or structured templates.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Angular / Streamlit UI                       │
│                  (port 8501 for Streamlit)                      │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP POST /api/v1/chatbot/message
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  chatbot_api.py (port 8002)                     │
│               FastAPI — Chatbot Endpoint                       │
└────────┬───────────────┬───────────────┬───────────────────────┘
         │               │               │
         ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
│chatbot_engine│ │  rag_engine  │ │   llm_client     │
│  (intent +   │ │  (TF-IDF /   │ │ (OpenAI/Gemini/  │
│   API calls) │ │   keyword)   │ │  Mistral/Claude) │
└──────┬───────┘ └──────────────┘ └──────────────────┘
       │
       ▼ HTTP calls to existing APIs
┌─────────────────────────────────────────────────────────────────┐
│          business_validation_api.py (port 8001)                │
│   /startup-success  /sentiment  /market-analysis               │
│   /specialists      /business-validation                       │
└─────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│  ML Models (.joblib)  │  Market Data (World Bank)              │
│  Specialists (CSV)    │  Sentiment Pipeline                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Files Created

| File | Description |
|------|-------------|
| `chatbot_config.py` | Central config — env vars, endpoints, intent keywords |
| `chatbot_prompts.py` | System prompt + specialized prompts + fallback templates |
| `llm_client.py` | External LLM client (OpenAI, Gemini, Mistral, Claude) |
| `rag_engine.py` | Simple RAG — TF-IDF retrieval from internal knowledge |
| `chatbot_engine.py` | Core orchestration — intent → API → RAG → LLM → response |
| `chatbot_memory.py` | Conversation memory (JSON file, MongoDB-compatible schema) |
| `chatbot_api.py` | FastAPI app with `/api/v1/chatbot/message` endpoint |
| `chatbot_streamlit_app.py` | Streamlit testing UI |
| `data/knowledge_documents.json` | Internal knowledge base for RAG |
| `.env` / `.env.example` | Environment configuration |
| `README_CHATBOT.md` | This documentation |

---

## ⚙️ Configuration (.env)

Copy `.env.example` to `.env` and configure your LLM provider:

### Option 1 — OpenAI
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
LLM_MODEL=gpt-4o-mini
```

### Option 2 — Google Gemini
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-key
LLM_MODEL=gemini-1.5-flash
```

### Option 3 — Mistral
```env
LLM_PROVIDER=mistral
MISTRAL_API_KEY=your-mistral-key
LLM_MODEL=mistral-small-latest
```

### Option 4 — Claude (Anthropic)
```env
LLM_PROVIDER=claude
CLAUDE_API_KEY=your-claude-key
LLM_MODEL=claude-sonnet-4-20250514
```

### Option 5 — No LLM (Fallback Mode)
```env
LLM_PROVIDER=none
```
The chatbot will use structured template responses based on API results.

---

## 🚀 How to Run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the main AI API (port 8001)

```bash
uvicorn business_validation_api:app --reload --port 8001
```

### 3. Start the chatbot API (port 8002)

```bash
uvicorn chatbot_api:app --reload --port 8002
```

### 4. (Optional) Start the Streamlit testing UI

```bash
streamlit run chatbot_streamlit_app.py
```

> **Note:** The main API (port 8001) must be running for the chatbot to call AI services. The chatbot still works without it but will report API errors.

---

## 📝 API Usage

### POST `/api/v1/chatbot/message`

**Request:**
```json
{
  "message": "Validate my business idea",
  "project_data": {
    "project_name": "NexusAI Business Validator",
    "project_description": "A SaaS platform that uses AI to validate startup ideas.",
    "sector": "SaaS",
    "country": "Morocco",
    "country_code": "MAR",
    "keyword": "business validation",
    "funding_rounds": 1,
    "founder_experience_years": 5,
    "team_size": 8,
    "market_size_billion": 25,
    "market_growth_rate_percent": 8,
    "product_traction_users": 12000,
    "burn_rate_million": 0.8,
    "revenue_million": 0.3,
    "investor_type": "angel",
    "founder_background": "first_time",
    "competition_level": "medium",
    "search_trend_score": 65,
    "use_world_bank": true,
    "opinions": [
      "Customers like the idea because validation is difficult.",
      "Some users complain that consulting is expensive."
    ]
  },
  "conversation_history": []
}
```

**Response:**
```json
{
  "intent": "business_validation",
  "answer": "## Business Validation Score\n\n**Summary** ...",
  "api_results": { ... },
  "api_errors": {},
  "rag_context": [
    { "title": "Business Validation Score", "source_type": "faq", "relevance_score": 0.42 }
  ],
  "recommendations": ["Focus on improving your weakest dimension score."],
  "sources_used": ["API: business_validation", "RAG: Business Validation Score", "LLM: openai"],
  "memory_saved": {},
  "fallback_mode": false
}
```

### GET `/api/v1/chatbot/status`

Returns LLM provider, model, configuration status, RAG status, and fallback mode.

### GET `/health`

Returns API health status.

---

## 🎯 Supported Intents

| Intent | Example Questions | APIs Called |
|--------|-------------------|-------------|
| `startup_analysis` | "Analyze my startup idea" | `/startup-success/predict` |
| `market_analysis` | "What is the market potential?" | `/market-analysis/score` |
| `sentiment_analysis` | "Analyze customer reviews" | `/sentiment/analyze` |
| `specialist_recommendation` | "Which specialist do I need?" | `/specialists/recommend` |
| `business_validation` | "Validate my business" | `/business-validation/score` |
| `business_recommendation` | "How can I improve my idea?" | `/business-validation/score` + RAG |
| `marketing_strategy` | "Give me a marketing strategy" | `/business-validation/score` + RAG + LLM |
| `business_plan` | "Generate a business plan" | `/business-validation/score` + RAG + LLM |
| `report_summary` | "Summarize the report" | RAG + API results |
| `general_question` | "Hello", "What can you do?" | RAG only |

---

## ⚡ Fallback Mode

When **no LLM API key** is configured (`LLM_PROVIDER=none` or empty keys):

- The chatbot still works fully — it detects intent, calls APIs, retrieves RAG context.
- Instead of LLM-generated prose, it returns **structured template responses** filled with API data.
- The response includes `"fallback_mode": true` so the frontend can display an appropriate notice.
- This ensures the platform is always functional, even without external API costs.

---

## 📚 RAG (Retrieval-Augmented Generation)

The RAG module searches internal knowledge documents before generating responses:

- **Source:** `data/knowledge_documents.json` (10 pre-built documents)
- **Method:** TF-IDF cosine similarity (scikit-learn), with keyword-overlap fallback
- **Top-K:** Returns the 3 most relevant chunks by default

### Adding Knowledge Documents

Edit `data/knowledge_documents.json` — each document follows the KnowledgeDocument schema:

```json
{
  "id": "doc_011",
  "title": "Your Document Title",
  "content": "Full text content...",
  "source_type": "faq",
  "metadata": { "module": "general" }
}
```

### Future Upgrade Path

The RAG engine is designed for easy migration to **MongoDB Atlas Vector Search**:
1. Store documents with embedding vectors in MongoDB
2. Create an Atlas Search index
3. Replace the `retrieve_context()` internals — all other code stays the same

---

## 🔗 Integration with Spring Boot + Angular

The chatbot API is designed for seamless integration:

### Spring Boot
```java
// Call from Spring Boot using RestTemplate or WebClient
WebClient client = WebClient.create("http://localhost:8002");
Mono<ChatResponse> response = client.post()
    .uri("/api/v1/chatbot/message")
    .bodyValue(chatRequest)
    .retrieve()
    .bodyToMono(ChatResponse.class);
```

### Angular
```typescript
// Call from Angular using HttpClient
this.http.post<ChatResponse>(
  'http://localhost:8002/api/v1/chatbot/message',
  { message: userInput, project_data: projectData }
).subscribe(response => {
  this.chatMessages.push(response);
});
```

### Data Compatibility

All response structures are compatible with the project class diagram:
- `Chat` — conversation sessions
- `Message` — individual messages with roles
- `AIRequest` — tracked API calls
- `AIResponse` — tracked AI responses with scores
- `KnowledgeDocument` — RAG documents
- `Report` — generated reports

---

## 📊 Memory

Conversation memory is stored locally in `data/chat_memory.json` and structured for future MongoDB migration:

- Each chat has a unique ID, project association, and message history
- Messages track role, content, timestamp, and sender type
- AI requests and responses are logged with model info and scores

---

## ⚠️ Important Notes

- **No local LLM / Ollama** — all LLM calls go to external cloud APIs
- **No model retraining** — the chatbot only _uses_ existing ML models via API calls
- **No score hallucination** — all numbers come from API results, never invented
- **Existing endpoints unchanged** — the chatbot is a new layer on top
- **CORS enabled** — both APIs accept cross-origin requests for frontend integration
