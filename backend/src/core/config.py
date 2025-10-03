"""
Configuration management for the voice chatbot backend.
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application Configuration
    app_name: str = Field(default="voice-chatbot", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    app_port: int = Field(default=3000, env="APP_PORT")
    app_host: str = Field(default="0.0.0.0", env="APP_HOST")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Speechmatics Configuration
    speechmatics_api_key: str = Field(..., env="SPEECHMATICS_API_KEY")
    speechmatics_rt_url: str = Field(
        default="wss://eu2.rt.speechmatics.com/v2", 
        env="SPEECHMATICS_RT_URL"
    )
    speechmatics_batch_url: str = Field(
        default="https://asr.api.speechmatics.com/v2", 
        env="SPEECHMATICS_BATCH_URL"
    )
    speechmatics_default_language: str = Field(default="en", env="SPEECHMATICS_DEFAULT_LANGUAGE")
    speechmatics_enable_partials: bool = Field(default=True, env="SPEECHMATICS_ENABLE_PARTIALS")
    speechmatics_max_delay: int = Field(default=5, env="SPEECHMATICS_MAX_DELAY")
    speechmatics_enable_entities: bool = Field(default=True, env="SPEECHMATICS_ENABLE_ENTITIES")
    speechmatics_enable_sentiment: bool = Field(default=True, env="SPEECHMATICS_ENABLE_SENTIMENT")
    speechmatics_enable_topics: bool = Field(default=True, env="SPEECHMATICS_ENABLE_TOPICS")
    
    # Speechmatics TTS Configuration
    speechmatics_tts_enabled: bool = Field(default=True, env="SPEECHMATICS_TTS_ENABLED")
    speechmatics_tts_voice: str = Field(default="default", env="SPEECHMATICS_TTS_VOICE")
    speechmatics_tts_speed: float = Field(default=1.0, env="SPEECHMATICS_TTS_SPEED")
    speechmatics_tts_pitch: float = Field(default=1.0, env="SPEECHMATICS_TTS_PITCH")
    
    # AI Chatbot Configuration (Fallback Hierarchy)
    # Primary: Kong API Gateway (Local LLM)
    kong_api_url: str = Field(default="http://kong-api:8000", env="KONG_API_URL")
    kong_api_key: Optional[str] = Field(default=None, env="KONG_API_KEY")
    kong_model_endpoint: str = Field(default="/v1/chat/completions", env="KONG_MODEL_ENDPOINT")
    kong_default_model: str = Field(default="local-llm", env="KONG_DEFAULT_MODEL")
    
    # Fallback 1: Local Ollama
    ollama_base_url: str = Field(default="http://ollama:11434", env="OLLAMA_BASE_URL")
    ollama_default_model: str = Field(default="llama2", env="OLLAMA_DEFAULT_MODEL")
    ollama_timeout: int = Field(default=30000, env="OLLAMA_TIMEOUT")
    ollama_max_tokens: int = Field(default=2000, env="OLLAMA_MAX_TOKENS")
    ollama_temperature: float = Field(default=0.7, env="OLLAMA_TEMPERATURE")
    
    # Fallback 2: OpenAI
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4", env="OPENAI_MODEL")
    openai_max_tokens: int = Field(default=2000, env="OPENAI_MAX_TOKENS")
    openai_temperature: float = Field(default=0.7, env="OPENAI_TEMPERATURE")
    openai_top_p: float = Field(default=1.0, env="OPENAI_TOP_P")
    openai_frequency_penalty: float = Field(default=0.0, env="OPENAI_FREQUENCY_PENALTY")
    openai_presence_penalty: float = Field(default=0.0, env="OPENAI_PRESENCE_PENALTY")
    openai_timeout: int = Field(default=30000, env="OPENAI_TIMEOUT")
    openai_organization: Optional[str] = Field(default=None, env="OPENAI_ORGANIZATION")
    
    # AI Response Configuration
    ai_response_max_length: int = Field(default=500, env="AI_RESPONSE_MAX_LENGTH")
    ai_response_timeout: int = Field(default=30000, env="AI_RESPONSE_TIMEOUT")
    ai_fallback_enabled: bool = Field(default=True, env="AI_FALLBACK_ENABLED")
    ai_fallback_order: str = Field(default="kong,ollama,openai", env="AI_FALLBACK_ORDER")
    
    # Text-to-Speech Configuration (Fallback Hierarchy)
    tts_primary_provider: str = Field(default="speechmatics", env="TTS_PRIMARY_PROVIDER")
    tts_speechmatics_enabled: bool = Field(default=True, env="TTS_SPEECHMATICS_ENABLED")
    tts_fallback_provider: str = Field(default="local", env="TTS_FALLBACK_PROVIDER")
    tts_local_enabled: bool = Field(default=True, env="TTS_LOCAL_ENABLED")
    tts_local_engine: str = Field(default="espeak", env="TTS_LOCAL_ENGINE")
    tts_local_voice: str = Field(default="en-us", env="TTS_LOCAL_VOICE")
    tts_local_speed: int = Field(default=150, env="TTS_LOCAL_SPEED")
    tts_local_pitch: int = Field(default=50, env="TTS_LOCAL_PITCH")
    tts_audio_format: str = Field(default="wav", env="TTS_AUDIO_FORMAT")
    tts_sample_rate: int = Field(default=22050, env="TTS_SAMPLE_RATE")
    tts_channels: int = Field(default=1, env="TTS_CHANNELS")
    tts_bit_depth: int = Field(default=16, env="TTS_BIT_DEPTH")
    
    # Database Configuration (PostgreSQL)
    db_host: str = Field(default="postgres", env="DB_HOST")
    db_port: int = Field(default=5432, env="DB_PORT")
    db_name: str = Field(default="voice_chatbot_db", env="DB_NAME")
    db_user: str = Field(default="postgres", env="DB_USER")
    db_password: str = Field(default="postgres_password", env="DB_PASSWORD")
    db_ssl: bool = Field(default=False, env="DB_SSL")
    db_pool_min: int = Field(default=2, env="DB_POOL_MIN")
    db_pool_max: int = Field(default=10, env="DB_POOL_MAX")
    db_connection_timeout: int = Field(default=60000, env="DB_CONNECTION_TIMEOUT")
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    
    # Redis Configuration
    redis_host: str = Field(default="redis", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    redis_pool_size: int = Field(default=10, env="REDIS_POOL_SIZE")
    redis_connect_timeout: int = Field(default=10000, env="REDIS_CONNECT_TIMEOUT")
    redis_command_timeout: int = Field(default=5000, env="REDIS_COMMAND_TIMEOUT")
    
    # WebSocket Configuration
    ws_enabled: bool = Field(default=True, env="WS_ENABLED")
    ws_port: int = Field(default=3001, env="WS_PORT")
    ws_cors_origin: str = Field(default="http://localhost:3000,http://localhost:3001", env="WS_CORS_ORIGIN")
    ws_heartbeat_interval: int = Field(default=30, env="WS_HEARTBEAT_INTERVAL")
    ws_max_connections: int = Field(default=100, env="WS_MAX_CONNECTIONS")
    
    # Voice Activity Detection (VAD)
    vad_enabled: bool = Field(default=True, env="VAD_ENABLED")
    vad_silence_threshold: float = Field(default=0.3, env="VAD_SILENCE_THRESHOLD")
    vad_speech_threshold: float = Field(default=0.5, env="VAD_SPEECH_THRESHOLD")
    vad_min_speech_duration: float = Field(default=0.5, env="VAD_MIN_SPEECH_DURATION")
    vad_max_silence_duration: float = Field(default=2.0, env="VAD_MAX_SILENCE_DURATION")
    vad_frame_size: int = Field(default=1024, env="VAD_FRAME_SIZE")
    vad_sample_rate: int = Field(default=16000, env="VAD_SAMPLE_RATE")
    
    # Audio Processing Configuration
    audio_sample_rate: int = Field(default=16000, env="AUDIO_SAMPLE_RATE")
    audio_channels: int = Field(default=1, env="AUDIO_CHANNELS")
    audio_bit_depth: int = Field(default=16, env="AUDIO_BIT_DEPTH")
    audio_format: str = Field(default="pcm_s16le", env="AUDIO_FORMAT")
    audio_chunk_size: int = Field(default=4096, env="AUDIO_CHUNK_SIZE")
    audio_buffer_size: int = Field(default=8192, env="AUDIO_BUFFER_SIZE")
    audio_upload_max_size: str = Field(default="50MB", env="AUDIO_UPLOAD_MAX_SIZE")
    audio_upload_allowed_formats: str = Field(default="wav,mp3,flac,m4a,ogg", env="AUDIO_UPLOAD_ALLOWED_FORMATS")
    audio_storage_path: str = Field(default="/app/audio_storage", env="AUDIO_STORAGE_PATH")
    audio_cleanup_interval: int = Field(default=3600, env="AUDIO_CLEANUP_INTERVAL")
    
    # Multi-Language Support
    supported_languages: str = Field(default="en,es,fr,de,it,pt,ru,ja,ko,zh", env="SUPPORTED_LANGUAGES")
    default_language: str = Field(default="en", env="DEFAULT_LANGUAGE")
    auto_detect_language: bool = Field(default=True, env="AUTO_DETECT_LANGUAGE")
    language_detection_confidence: float = Field(default=0.8, env="LANGUAGE_DETECTION_CONFIDENCE")
    
    # Conversation History Persistence
    conversation_history_enabled: bool = Field(default=True, env="CONVERSATION_HISTORY_ENABLED")
    conversation_history_retention_days: int = Field(default=30, env="CONVERSATION_HISTORY_RETENTION_DAYS")
    conversation_history_max_messages: int = Field(default=1000, env="CONVERSATION_HISTORY_MAX_MESSAGES")
    conversation_history_encryption: bool = Field(default=True, env="CONVERSATION_HISTORY_ENCRYPTION")
    conversation_history_backup_enabled: bool = Field(default=True, env="CONVERSATION_HISTORY_BACKUP_ENABLED")
    conversation_history_backup_interval: int = Field(default=24, env="CONVERSATION_HISTORY_BACKUP_INTERVAL")
    
    # Authentication & Security
    jwt_secret: str = Field(..., env="JWT_SECRET")
    jwt_expires_in: str = Field(default="7d", env="JWT_EXPIRES_IN")
    jwt_refresh_expires_in: str = Field(default="30d", env="JWT_REFRESH_EXPIRES_IN")
    encryption_key: str = Field(..., env="ENCRYPTION_KEY")
    hash_rounds: int = Field(default=12, env="HASH_ROUNDS")
    cors_origin: str = Field(default="http://localhost:3000,http://localhost:3001", env="CORS_ORIGIN")
    cors_credentials: bool = Field(default=True, env="CORS_CREDENTIALS")
    
    # Logging & Monitoring
    log_level: str = Field(default="info", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    log_file_enabled: bool = Field(default=True, env="LOG_FILE_ENABLED")
    log_file_path: str = Field(default="./logs/app.log", env="LOG_FILE_PATH")
    log_max_files: int = Field(default=5, env="LOG_MAX_FILES")
    log_max_size: str = Field(default="10m", env="LOG_MAX_SIZE")
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    sentry_environment: str = Field(default="development", env="SENTRY_ENVIRONMENT")
    
    # Rate Limiting
    rate_limit_window_ms: int = Field(default=900000, env="RATE_LIMIT_WINDOW_MS")
    rate_limit_max_requests: int = Field(default=100, env="RATE_LIMIT_MAX_REQUESTS")
    rate_limit_skip_successful_requests: bool = Field(default=False, env="RATE_LIMIT_SKIP_SUCCESSFUL_REQUESTS")
    rate_limit_voice_requests_per_minute: int = Field(default=20, env="RATE_LIMIT_VOICE_REQUESTS_PER_MINUTE")
    
    # Feature Flags
    feature_voice_chat: bool = Field(default=True, env="FEATURE_VOICE_CHAT")
    feature_file_upload: bool = Field(default=True, env="FEATURE_FILE_UPLOAD")
    feature_conversation_history: bool = Field(default=True, env="FEATURE_CONVERSATION_HISTORY")
    feature_multi_language: bool = Field(default=True, env="FEATURE_MULTI_LANGUAGE")
    feature_voice_activity_detection: bool = Field(default=True, env="FEATURE_VOICE_ACTIVITY_DETECTION")
    feature_real_time_transcription: bool = Field(default=True, env="FEATURE_REAL_TIME_TRANSCRIPTION")
    feature_text_to_speech: bool = Field(default=True, env="FEATURE_TEXT_TO_SPEECH")
    feature_ai_fallback: bool = Field(default=True, env="FEATURE_AI_FALLBACK")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def database_url_computed(self) -> str:
        """Compute database URL from components if not provided directly."""
        if self.database_url:
            return self.database_url
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def redis_url_computed(self) -> str:
        """Compute Redis URL from components if not provided directly."""
        if self.redis_url:
            return self.redis_url
        auth_part = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth_part}{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def supported_languages_list(self) -> List[str]:
        """Get supported languages as a list."""
        return [lang.strip() for lang in self.supported_languages.split(",")]
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origin.split(",")]
    
    @property
    def ai_fallback_order_list(self) -> List[str]:
        """Get AI fallback order as a list."""
        return [provider.strip() for provider in self.ai_fallback_order.split(",")]
    
    @property
    def audio_upload_allowed_formats_list(self) -> List[str]:
        """Get allowed audio formats as a list."""
        return [fmt.strip() for fmt in self.audio_upload_allowed_formats.split(",")]


# Global settings instance
settings = Settings()
