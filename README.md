# Financial Advisor AI Assistant

A production-ready AI assistant for financial advisors that integrates with Gmail, Google Calendar, and HubSpot CRM. The assistant provides intelligent responses using RAG (Retrieval-Augmented Generation) and can perform actions through tool calling.

## Features

- **Authentication**: Google OAuth (Gmail + Calendar) and HubSpot OAuth
- **RAG Pipeline**: Vector embeddings of emails and CRM data for intelligent responses
- **Tool Calling**: Automated actions across Gmail, Calendar, and HubSpot
- **Proactive Agent**: Memory-based instructions and event-driven actions
- **Chat Interface**: ChatGPT-like streaming interface with responsive design

## Tech Stack

- **Frontend**: React + TailwindCSS
- **Backend**: Python + FastAPI
- **Database**: PostgreSQL + pgvector
- **AI**: OpenAI API with embeddings and tool calling
- **Auth**: OAuth 2.0 (Google, HubSpot)
- **Deployment**: Docker + Docker Compose

## Project Structure

```
advisor-ai/
├── frontend/          # React frontend
├── backend/           # FastAPI backend
├── database/          # Database migrations and schemas
├── docker-compose.yml # Local development setup
├── Dockerfile         # Production Docker configuration
└── README.md          # This file
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Google Cloud Console project with OAuth credentials
- HubSpot developer account
- OpenAI API key

### Environment Variables

Create `.env` files in both `frontend/` and `backend/` directories:

**Backend `.env`:**
```env
DATABASE_URL=postgresql://user:password@localhost:5432/advisor_ai
OPENAI_API_KEY=your_openai_api_key
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
HUBSPOT_CLIENT_ID=your_hubspot_client_id
HUBSPOT_CLIENT_SECRET=your_hubspot_client_secret
SECRET_KEY=your_secret_key_for_jwt
```

**Frontend `.env`:**
```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_GOOGLE_CLIENT_ID=your_google_client_id
REACT_APP_HUBSPOT_CLIENT_ID=your_hubspot_client_id
```

### Development Setup

1. Clone the repository
2. Set up environment variables
3. Start the development environment:

```bash
docker-compose up -d
```

4. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Production Deployment

The application is configured for deployment on Render or Fly.io with Docker support.

## Architecture

### RAG Pipeline
1. **Data Ingestion**: Gmail emails + HubSpot contacts/notes → embeddings → pgvector
2. **Query Processing**: User question → embedding → similarity search → context retrieval
3. **Response Generation**: Context + question → LLM → answer or action JSON

### Tool Calling System
1. **Action Parsing**: LLM outputs structured JSON
2. **Validation**: Check contact existence, time availability, etc.
3. **Execution**: Call Gmail, Calendar, HubSpot APIs
4. **Memory**: Store tasks with status for continuation

### Proactive Agent
- **Memory System**: Persistent storage of ongoing instructions
- **Event Triggers**: Webhooks/polling from Gmail, Calendar, HubSpot
- **Action Execution**: Automatic responses to events based on instructions

## API Endpoints

### Authentication
- `POST /auth/google` - Google OAuth callback
- `POST /auth/hubspot` - HubSpot OAuth callback
- `GET /auth/me` - Get current user info

### Chat
- `POST /chat/message` - Send message to AI assistant
- `GET /chat/history` - Get chat history
- `POST /chat/stream` - Streaming chat endpoint

### Actions
- `POST /actions/execute` - Execute tool calling action
- `GET /actions/tasks` - Get pending tasks
- `PUT /actions/tasks/{task_id}` - Update task status

### RAG
- `POST /rag/ingest` - Ingest new data (emails, contacts)
- `GET /rag/search` - Search vector database
- `POST /rag/query` - Query with context retrieval

## Development Standards

- **Code Quality**: TypeScript for frontend, Python + Pydantic for backend
- **Error Handling**: Graceful error handling with structured logging
- **Testing**: Unit and integration tests where appropriate
- **Security**: OAuth 2.0, JWT tokens, secure credential storage
- **Performance**: Async/await, connection pooling, efficient queries

## Contributing

1. Follow the established code style and patterns
2. Write tests for new features
3. Update documentation as needed
4. Ensure all CI/CD checks pass

## License

Private - All rights reserved