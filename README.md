# Voice-Enabled Chatbot

A comprehensive voice-enabled chatbot application with real-time speech-to-text transcription, AI-powered responses, and text-to-speech capabilities. Built with FastAPI backend and React frontend, featuring multi-language support and conversation history persistence.

## Features

### 🎤 Real-time Voice Interaction
- Live speech-to-text transcription using Speechmatics API
- Voice activity detection for natural conversation flow
- Real-time partial and final transcript display
- Multi-language support (English, Spanish, French, German, Italian, Portuguese, Russian, Japanese, Korean, Chinese)

### 🤖 AI-Powered Responses
- Fallback hierarchy: Kong API (local LLM) → Ollama → OpenAI
- Context-aware conversation management
- Configurable AI models and parameters
- Response time optimization

### 🔊 Text-to-Speech
- Fallback hierarchy: Speechmatics → Local TTS (espeak)
- Multiple voice options and languages
- Real-time audio playback
- Audio format support (WAV, MP3, FLAC, M4A, OGG)

### 💬 Conversation Management
- Persistent conversation history
- User authentication and authorization
- Multi-user support
- Audio file upload and processing

### 🏗️ Modern Architecture
- Microservices architecture with Docker containerization
- WebSocket real-time communication
- PostgreSQL database with Redis caching
- RESTful API design
- Responsive React frontend with Material-UI

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Speechmatics API key
- OpenAI API key (optional, for fallback)

### Environment Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd voice-chatbot
   ```

2. **Configure environment variables**
   ```bash
   cp backend/env.example backend/.env
   # Edit backend/.env with your API keys and configuration
   ```

3. **Start the application**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:3000/api
   - API Documentation: http://localhost:3000/docs

### Default Login
- Username: `admin`
- Password: `admin123`

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Frontend │    │  FastAPI Backend │    │  External APIs  │
│                 │    │                 │    │                 │
│ • Voice Recording│◄──►│ • WebSocket API │◄──►│ • Speechmatics  │
│ • Chat Interface │    │ • REST API      │    │ • Kong/Ollama   │
│ • Audio Playback │    │ • Audio Processing│   │ • OpenAI        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Configuration

### Environment Variables

#### Speechmatics Configuration
```bash
SPEECHMATICS_API_KEY=your-speechmatics-api-key
SPEECHMATICS_RT_URL=wss://eu2.rt.speechmatics.com/v2
SPEECHMATICS_DEFAULT_LANGUAGE=en
```

#### AI Chatbot Configuration
```bash
# Primary: Kong API Gateway (Local LLM)
KONG_API_URL=http://kong-api:8000
KONG_API_KEY=your-kong-api-key

# Fallback 1: Local Ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_DEFAULT_MODEL=llama2

# Fallback 2: OpenAI
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-4
```

#### Database Configuration
```bash
DB_HOST=postgres
DB_NAME=voice_chatbot_db
DB_USER=postgres
DB_PASSWORD=postgres_password
```

## API Endpoints

### Chat API
- `POST /api/v1/chat/message` - Send text message
- `POST /api/v1/chat/tts` - Generate speech from text
- `GET /api/v1/chat/models` - Get available AI models
- `GET /api/v1/chat/voices` - Get available TTS voices

### Audio API
- `POST /api/v1/audio/transcribe` - Transcribe audio file
- `POST /api/v1/audio/detect-language` - Detect audio language
- `GET /api/v1/audio/audio-formats` - Get supported formats

### Conversation API
- `GET /api/v1/conversations` - Get user conversations
- `POST /api/v1/conversations` - Create new conversation
- `GET /api/v1/conversations/{id}/messages` - Get conversation messages

### WebSocket Endpoints
- `ws://localhost:3001/ws/transcription/{session_id}` - Real-time transcription
- `ws://localhost:3001/ws/chat/{user_id}` - Real-time chat

## Development

### Backend Development
```bash
cd backend
pip install -r requirements.txt
uvicorn src.main:app --reload --host 0.0.0.0 --port 3000
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

### Running Tests
```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## Docker Services

The application includes the following Docker services:

- **frontend**: React application with Nginx
- **backend**: FastAPI application
- **postgres**: PostgreSQL database
- **redis**: Redis cache
- **kong-api**: Kong API Gateway for local LLM
- **ollama**: Local LLM service

## Deployment

### Production Deployment
1. Configure production environment variables
2. Set up SSL certificates
3. Configure reverse proxy (Nginx)
4. Set up monitoring and logging
5. Configure backup strategies

### Kubernetes Deployment (Planned)
- Helm charts for easy deployment
- ArgoCD for GitOps
- Horizontal Pod Autoscaling
- Service mesh integration

## Monitoring

### Health Checks
- `GET /health` - Application health status
- `GET /ready` - Readiness check for Kubernetes

### Metrics
- Request/response times
- Error rates
- WebSocket connection counts
- Audio processing latency
- AI response generation time

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Check the documentation in `/docs`
- Review the API documentation at `/docs`

## Roadmap

### Phase 1: Core Features ✅
- [x] Real-time transcription
- [x] AI chatbot integration
- [x] Text-to-speech
- [x] Basic conversation management

### Phase 2: Advanced Features 🚧
- [ ] Voice activity detection optimization
- [ ] Advanced audio processing
- [ ] Multi-modal interactions
- [ ] Custom voice training

### Phase 3: Enterprise Features 📋
- [ ] Advanced analytics
- [ ] Custom AI model integration
- [ ] Enterprise SSO
- [ ] Advanced security features

## Acknowledgments

- [Speechmatics](https://www.speechmatics.com/) for speech-to-text and TTS services
- [FastAPI](https://fastapi.tiangolo.com/) for the backend framework
- [React](https://reactjs.org/) for the frontend framework
- [Material-UI](https://mui.com/) for the UI components
