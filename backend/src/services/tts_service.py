"""
Text-to-Speech service with fallback hierarchy: Speechmatics -> Local TTS.
"""
import asyncio
import io
import logging
import os
import tempfile
from typing import Dict, Any, Optional, BinaryIO, List
import pyttsx3
from gtts import gTTS
import soundfile as sf
import numpy as np

from ..core.config import settings

logger = logging.getLogger(__name__)


class TTSService:
    """Text-to-Speech service with fallback hierarchy."""
    
    def __init__(self):
        self.primary_provider = settings.tts_primary_provider
        self.fallback_provider = settings.tts_fallback_provider
        self.speechmatics_enabled = settings.tts_speechmatics_enabled
        self.local_enabled = settings.tts_local_enabled
        
        # Audio settings
        self.audio_format = settings.tts_audio_format
        self.sample_rate = settings.tts_sample_rate
        self.channels = settings.tts_channels
        self.bit_depth = settings.tts_bit_depth
        
        # Local TTS settings
        self.local_engine = settings.tts_local_engine
        self.local_voice = settings.tts_local_voice
        self.local_speed = settings.tts_local_speed
        self.local_pitch = settings.tts_local_pitch
        
        # Initialize local TTS engine
        self.local_engine_instance = None
        if self.local_enabled:
            self._initialize_local_engine()
    
    def _initialize_local_engine(self):
        """Initialize local TTS engine."""
        try:
            if self.local_engine == "pyttsx3":
                self.local_engine_instance = pyttsx3.init()
                
                # Set voice properties
                voices = self.local_engine_instance.getProperty('voices')
                if voices:
                    # Try to find a voice matching the preferred language
                    for voice in voices:
                        if self.local_voice in voice.id.lower():
                            self.local_engine_instance.setProperty('voice', voice.id)
                            break
                
                # Set speech rate and volume
                self.local_engine_instance.setProperty('rate', self.local_speed)
                self.local_engine_instance.setProperty('volume', 0.9)
                
                logger.info("Local TTS engine (pyttsx3) initialized successfully")
            else:
                logger.warning(f"Unsupported local TTS engine: {self.local_engine}")
                
        except Exception as e:
            logger.error(f"Failed to initialize local TTS engine: {e}")
            self.local_engine_instance = None
    
    async def generate_speech(
        self,
        text: str,
        language: str = "en",
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        pitch: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Generate speech from text using fallback hierarchy.
        
        Args:
            text: Text to convert to speech
            language: Language code (e.g., 'en', 'es', 'fr')
            voice: Voice to use (provider-specific)
            speed: Speech speed (1.0 = normal)
            pitch: Voice pitch (1.0 = normal)
            
        Returns:
            Dict containing audio data, format info, and metadata
        """
        # Try primary provider first
        if self.primary_provider == "speechmatics" and self.speechmatics_enabled:
            try:
                result = await self._generate_speechmatics_speech(
                    text, language, voice, speed, pitch
                )
                if result:
                    return result
            except Exception as e:
                logger.error(f"Speechmatics TTS failed: {e}")
        
        # Try fallback provider
        if self.fallback_provider == "local" and self.local_enabled:
            try:
                result = await self._generate_local_speech(
                    text, language, voice, speed, pitch
                )
                if result:
                    return result
            except Exception as e:
                logger.error(f"Local TTS failed: {e}")
        
        # If all providers fail, return error
        logger.error("All TTS providers failed")
        return {
            "audio_data": None,
            "format": self.audio_format,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "duration": 0,
            "provider": "none",
            "error": "All TTS providers failed"
        }
    
    async def _generate_speechmatics_speech(
        self,
        text: str,
        language: str,
        voice: Optional[str],
        speed: Optional[float],
        pitch: Optional[float]
    ) -> Optional[Dict[str, Any]]:
        """Generate speech using Speechmatics TTS."""
        try:
            # Note: Speechmatics TTS API integration would go here
            # For now, we'll implement a placeholder that falls back to local TTS
            logger.info("Speechmatics TTS not yet implemented, falling back to local TTS")
            return None
            
        except Exception as e:
            logger.error(f"Speechmatics TTS error: {e}")
            return None
    
    async def _generate_local_speech(
        self,
        text: str,
        language: str,
        voice: Optional[str],
        speed: Optional[float],
        pitch: Optional[float]
    ) -> Optional[Dict[str, Any]]:
        """Generate speech using local TTS engine."""
        try:
            if not self.local_engine_instance:
                return None
            
            # Create temporary file for audio output
            with tempfile.NamedTemporaryFile(suffix=f".{self.audio_format}", delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                # Generate speech using pyttsx3
                if self.local_engine == "pyttsx3":
                    # Save to temporary file
                    self.local_engine_instance.save_to_file(text, temp_path)
                    self.local_engine_instance.runAndWait()
                    
                    # Read the generated audio file
                    with open(temp_path, 'rb') as f:
                        audio_data = f.read()
                    
                    # Get audio properties
                    try:
                        audio_info = sf.info(temp_path)
                        duration = audio_info.duration
                        sample_rate = audio_info.samplerate
                        channels = audio_info.channels
                    except Exception:
                        # Fallback values if we can't read audio info
                        duration = len(text) * 0.1  # Rough estimate
                        sample_rate = self.sample_rate
                        channels = self.channels
                
                # Generate speech using gTTS (Google Text-to-Speech)
                elif self.local_engine == "gtts":
                    tts = gTTS(text=text, lang=language, slow=False)
                    tts.save(temp_path)
                    
                    with open(temp_path, 'rb') as f:
                        audio_data = f.read()
                    
                    # gTTS generates MP3, we need to convert to WAV
                    duration = len(text) * 0.1  # Rough estimate
                    sample_rate = 22050  # gTTS default
                    channels = 1
                
                else:
                    logger.error(f"Unsupported local TTS engine: {self.local_engine}")
                    return None
                
                return {
                    "audio_data": audio_data,
                    "format": self.audio_format,
                    "sample_rate": sample_rate,
                    "channels": channels,
                    "duration": duration,
                    "provider": "local",
                    "engine": self.local_engine,
                    "voice": voice or self.local_voice,
                    "language": language
                }
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"Local TTS error: {e}")
            return None
    
    async def get_available_voices(self, language: str = "en") -> Dict[str, Any]:
        """Get available voices for each provider."""
        voices = {}
        
        # Local voices
        if self.local_enabled and self.local_engine_instance:
            try:
                if self.local_engine == "pyttsx3":
                    local_voices = []
                    for voice in self.local_engine_instance.getProperty('voices'):
                        local_voices.append({
                            "id": voice.id,
                            "name": voice.name,
                            "language": getattr(voice, 'languages', ['en'])[0] if hasattr(voice, 'languages') else 'en',
                            "gender": getattr(voice, 'gender', 'unknown')
                        })
                    voices["local"] = local_voices
            except Exception as e:
                logger.error(f"Error getting local voices: {e}")
        
        # Speechmatics voices (placeholder)
        if self.speechmatics_enabled:
            voices["speechmatics"] = [
                {
                    "id": "default",
                    "name": "Default Voice",
                    "language": language,
                    "gender": "neutral"
                }
            ]
        
        return voices
    
    async def get_supported_languages(self) -> Dict[str, List[str]]:
        """Get supported languages for each provider."""
        languages = {}
        
        # Local TTS languages
        if self.local_enabled:
            if self.local_engine == "pyttsx3":
                # pyttsx3 supports multiple languages depending on system voices
                languages["local"] = ["en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh"]
            elif self.local_engine == "gtts":
                # gTTS supports many languages
                languages["local"] = [
                    "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh",
                    "ar", "hi", "th", "vi", "pl", "tr", "nl", "sv", "da", "no"
                ]
        
        # Speechmatics languages
        if self.speechmatics_enabled:
            languages["speechmatics"] = settings.supported_languages_list
        
        return languages
    
    def get_audio_format_info(self) -> Dict[str, Any]:
        """Get supported audio formats and their properties."""
        return {
            "supported_formats": ["wav", "mp3", "ogg"],
            "default_format": self.audio_format,
            "default_sample_rate": self.sample_rate,
            "default_channels": self.channels,
            "default_bit_depth": self.bit_depth
        }
    
    async def convert_audio_format(
        self,
        audio_data: bytes,
        input_format: str,
        output_format: str,
        target_sample_rate: Optional[int] = None
    ) -> bytes:
        """Convert audio from one format to another."""
        try:
            # Create temporary files for input and output
            with tempfile.NamedTemporaryFile(suffix=f".{input_format}", delete=False) as input_file:
                input_file.write(audio_data)
                input_path = input_file.name
            
            with tempfile.NamedTemporaryFile(suffix=f".{output_format}", delete=False) as output_file:
                output_path = output_file.name
            
            try:
                # Read audio data
                data, sample_rate = sf.read(input_path)
                
                # Resample if needed
                if target_sample_rate and target_sample_rate != sample_rate:
                    import librosa
                    data = librosa.resample(data, orig_sr=sample_rate, target_sr=target_sample_rate)
                    sample_rate = target_sample_rate
                
                # Write to output format
                sf.write(output_path, data, sample_rate, format=output_format.upper())
                
                # Read converted audio
                with open(output_path, 'rb') as f:
                    converted_data = f.read()
                
                return converted_data
                
            finally:
                # Clean up temporary files
                for path in [input_path, output_path]:
                    if os.path.exists(path):
                        os.unlink(path)
                        
        except Exception as e:
            logger.error(f"Audio format conversion error: {e}")
            raise


# Global instance
tts_service = TTSService()
