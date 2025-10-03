# Technical Architecture: Voice-Enabled Chatbot

## Architecture Overview

The voice-enabled chatbot follows a microservices architecture with clear separation of concerns between the frontend, backend API, and external services. The system is designed for scalability, reliability, and maintainability.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Frontend │    │  FastAPI Backend │    │  External APIs  │
│                 │    │                 │    │                 │
│ • Voice Recording│◄──►│ • WebSocket API │◄──►│ • Speechmatics  │
│ • Chat Interface │    │ • REST API      │    │ • Kong/Ollama   │
│ • Audio Playback │    │ • Audio Processing│   │ • OpenAI        │
│ • State Management│   │ • AI Integration │    │ • PostgreSQL    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   WebSocket     │    │   Database      │    │   Cache Layer   │
│   Real-time     │    │   PostgreSQL    │    │   Redis         │
│   Communication │    │   Persistence   │    │   Sessions      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Components

### Frontend (React + TypeScript)
**Purpose**: User interface for voice interaction and chat
**Technologies**: React 18, TypeScript, Material-UI, Zustand, Vite
**Key Features**:
- Real-time voice recording and transcription
- Chat interface with message history
- Audio playback for AI responses
- Multi-language support
- Responsive design

**Interfaces**:
- WebSocket connection to backend
- REST API calls for data management
- Browser Audio API for recording/playback

### Backend API (FastAPI + Python)
**Purpose**: Core business logic and service orchestration
**Technologies**: FastAPI, SQLAlchemy, WebSockets, Pydantic
**Key Features**:
- Real-time WebSocket communication
- Audio processing and transcription
- AI response generation with fallbacks
- Text-to-speech synthesis
- User and conversation management

**Interfaces**:
- REST API endpoints
- WebSocket connections
- Database connections (PostgreSQL)
- Cache connections (Redis)
- External service integrations

### Database Layer (PostgreSQL)
**Purpose**: Data persistence and transaction management
**Schema**:
- Users: Authentication and user preferences
- Conversations: Chat sessions and metadata
- Messages: Individual chat messages with audio references
- Audio Files: Uploaded and generated audio files

**Features**:
- ACID transactions
- Full-text search
- JSON metadata storage
- Automated backups

### Cache Layer (Redis)
**Purpose**: Session management and performance optimization
**Features**:
- WebSocket session storage
- API response caching
- Rate limiting
- Temporary data storage

## Data Flow

### Voice Input Flow
1. User starts voice recording in browser
2. Audio data captured via MediaRecorder API
3. Audio chunks sent via WebSocket to backend
4. Backend forwards audio to Speechmatics API
5. Transcription results streamed back to frontend
6. Partial transcripts displayed in real-time
7. Final transcript processed for AI response

### AI Response Flow
1. Transcribed text sent to AI service
2. Fallback hierarchy: Kong → Ollama → OpenAI
3. AI generates response with context
4. Response sent back to frontend
5. Optional TTS generation for audio response
6. Message stored in database

### Audio Processing Flow
1. Audio file uploaded via REST API
2. File validated and stored temporarily
3. Batch transcription via Speechmatics
4. Results processed and stored
5. Audio file metadata updated
6. Cleanup of temporary files

## Database Design

### Core Tables
```sql
-- Users table
users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(50) UNIQUE NOT NULL,
  email VARCHAR(100) UNIQUE NOT NULL,
  hashed_password VARCHAR(255) NOT NULL,
  preferred_language VARCHAR(10) DEFAULT 'en',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Conversations table
conversations (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  title VARCHAR(200),
  language VARCHAR(10) DEFAULT 'en',
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Messages table
messages (
  id SERIAL PRIMARY KEY,
  conversation_id INTEGER REFERENCES conversations(id),
  role VARCHAR(20) CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  content_type VARCHAR(20) DEFAULT 'text',
  audio_file_id INTEGER REFERENCES audio_files(id),
  transcription TEXT,
  ai_provider VARCHAR(20),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Audio files table
audio_files (
  id SERIAL PRIMARY KEY,
  filename VARCHAR(255) NOT NULL,
  file_path VARCHAR(500) NOT NULL,
  file_type VARCHAR(20) CHECK (file_type IN ('upload', 'tts_response', 'transcription')),
  transcription TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Indexes and Performance
- Composite indexes on conversation_id and created_at
- Full-text search indexes on message content
- JSON indexes on metadata fields
- Partitioning by date for large message tables

## Security Considerations

### Authentication & Authorization
- JWT tokens for API authentication
- WebSocket authentication via token validation
- Role-based access control
- Session management with Redis

### Data Protection
- Password hashing with bcrypt
- Encrypted sensitive data storage
- HTTPS/WSS for all communications
- Input validation and sanitization

### Network Security
- CORS configuration for cross-origin requests
- Rate limiting to prevent abuse
- Request size limits
- SQL injection prevention

## Performance Considerations

### Scalability
- Horizontal scaling with load balancers
- Database connection pooling
- Redis clustering for cache
- CDN for static assets

### Caching Strategy
- API response caching
- Database query result caching
- Static asset caching
- WebSocket session caching

### Load Balancing
- Round-robin for API requests
- Sticky sessions for WebSocket connections
- Health checks for service discovery
- Auto-scaling based on metrics

## Technology Stack

### Backend Technologies
- **Framework**: FastAPI (async Python web framework)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Cache**: Redis with aioredis
- **WebSockets**: Native FastAPI WebSocket support
- **Audio Processing**: librosa, pydub, soundfile
- **AI Integration**: httpx for HTTP clients, OpenAI SDK

### Frontend Technologies
- **Framework**: React 18 with TypeScript
- **UI Library**: Material-UI (MUI)
- **State Management**: Zustand
- **Build Tool**: Vite
- **Audio**: Web Audio API, MediaRecorder API
- **WebSockets**: Native WebSocket API

### Infrastructure Technologies
- **Containerization**: Docker with multi-stage builds
- **Orchestration**: Docker Compose for development
- **Reverse Proxy**: Nginx
- **Monitoring**: Built-in health checks
- **Deployment**: Kubernetes with ArgoCD (planned)

## External Services

### Speechmatics API
- **Purpose**: Speech-to-text and text-to-speech
- **Integration**: WebSocket for real-time, REST for batch
- **Fallback**: Local TTS (espeak) for text-to-speech
- **Rate Limits**: Handled with queuing and retry logic

### AI Services
- **Primary**: Kong API Gateway (local LLM)
- **Fallback 1**: Ollama (local LLM)
- **Fallback 2**: OpenAI API
- **Load Balancing**: Automatic failover with health checks

### Database Services
- **Primary**: PostgreSQL with connection pooling
- **Backup**: Automated daily backups
- **Monitoring**: Query performance tracking
- **Scaling**: Read replicas for read-heavy workloads

## Deployment Architecture

### Development Environment
```
┌─────────────────┐
│   Docker Compose│
│                 │
│ • Frontend      │
│ • Backend       │
│ • PostgreSQL    │
│ • Redis         │
│ • Kong          │
│ • Ollama        │
└─────────────────┘
```

### Production Environment (Planned)
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │   Kubernetes    │    │   External      │
│   (Nginx)       │    │   Cluster       │    │   Services      │
│                 │    │                 │    │                 │
│ • SSL Termination│   │ • Frontend Pods │    │ • Speechmatics  │
│ • Rate Limiting │    │ • Backend Pods  │    │ • OpenAI        │
│ • Health Checks │    │ • Database      │    │ • Monitoring    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Monitoring and Observability

### Application Metrics
- Request/response times
- Error rates and types
- WebSocket connection counts
- Audio processing latency
- AI response generation time

### Infrastructure Metrics
- CPU and memory usage
- Database connection pools
- Redis cache hit rates
- Network throughput
- Disk I/O performance

### Business Metrics
- Active users and sessions
- Conversation completion rates
- Transcription accuracy
- Feature usage statistics
- User satisfaction scores

## Error Handling and Resilience

### Circuit Breakers
- External API failure detection
- Automatic service degradation
- Graceful fallback mechanisms
- Health check integration

### Retry Logic
- Exponential backoff for transient failures
- Maximum retry limits
- Dead letter queues for failed messages
- User notification for persistent failures

### Data Consistency
- Database transactions for critical operations
- Eventual consistency for non-critical data
- Conflict resolution strategies
- Data validation and sanitization
