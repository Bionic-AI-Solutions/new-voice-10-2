"""
Real-time streaming Speechmatics service for live audio transcription.
This handles audio streams directly to the Speechmatics Real-time WebSocket API.
"""

import asyncio
import json
import logging
import base64
import io
import websockets
from typing import Dict, Any, Optional, Callable, AsyncGenerator
from websockets.exceptions import ConnectionClosed
from websockets.server import WebSocketServerProtocol
from fastapi import WebSocketDisconnect

from ..core.config import settings

logger = logging.getLogger(__name__)


class SpeechmaticsStreamingService:
    """Service for real-time audio streaming to Speechmatics."""
    
    def __init__(self):
        self.api_key = settings.speechmatics_api_key
        self.rt_url = "wss://eu2.rt.speechmatics.com/v2"  # Working endpoint
        self.default_language = settings.speechmatics_default_language
        self.enable_partials = settings.speechmatics_enable_partials
        self.max_delay = settings.speechmatics_max_delay
        self.enable_entities = settings.speechmatics_enable_entities
        
        # Active streaming sessions
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.accumulated_transcripts: Dict[str, str] = {}  # Store accumulated transcripts per session
        
    async def start_streaming_session(
        self,
        session_id: str,
        language: Optional[str] = None,
        on_transcript: Optional[Callable] = None,
        on_partial: Optional[Callable] = None,
        on_error: Optional[Callable] = None
    ) -> bool:
        """Start a real-time streaming session."""
        try:
            logger.info(f"Starting streaming session: {session_id}")
            
            # Create WebSocket connection to Speechmatics
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Connection configuration - using correct Speechmatics format
            connection_config = {
                "message": "StartRecognition",
                "audio_format": {
                    "type": "raw",
                    "encoding": "pcm_s16le",
                    "sample_rate": 16000
                },
                "transcription_config": {
                    "language": language or self.default_language,
                    "enable_partials": True,
                    "max_delay": 2,
                    "enable_entities": True
                }
            }
            
            # Connect to Speechmatics WebSocket
            websocket = await websockets.connect(
                self.rt_url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10
            )
            
            # Send start recognition message
            await websocket.send(json.dumps(connection_config))
            logger.info(f"Sent start recognition config for session: {session_id}")
            
            # Store session info
            self.active_sessions[session_id] = {
                "websocket": websocket,
                "on_transcript": on_transcript,
                "on_partial": on_partial,
                "on_error": on_error,
                "language": language or self.default_language,
                "started": True
            }
            
            # Start message handler task
            asyncio.create_task(self._handle_speechmatics_messages(session_id))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start streaming session {session_id}: {e}")
            return False
    
    async def send_audio_chunk(
        self,
        session_id: str,
        audio_data: bytes
    ) -> bool:
        """Send audio chunk to streaming session."""
        try:
            if session_id not in self.active_sessions:
                logger.error(f"Session {session_id} not found")
                return False
            
            session = self.active_sessions[session_id]
            websocket = session["websocket"]
            
            # Send raw audio data
            await websocket.send(audio_data)
            return True
            
        except Exception as e:
            logger.error(f"Error sending audio chunk for session {session_id}: {e}")
            return False
    
    async def stop_streaming_session(self, session_id: str) -> bool:
        """Stop a streaming session."""
        try:
            if session_id not in self.active_sessions:
                logger.warning(f"Session {session_id} not found for stopping")
                return False
            
            session = self.active_sessions[session_id]
            websocket = session["websocket"]
            
            # Send end of stream message
            end_message = {"message": "EndOfStream"}
            await websocket.send(json.dumps(end_message))
            
            # Close WebSocket
            await websocket.close()
            
            # Remove from active sessions
            del self.active_sessions[session_id]
            if session_id in self.accumulated_transcripts:
                del self.accumulated_transcripts[session_id]
            
            logger.info(f"Stopped streaming session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping session {session_id}: {e}")
            # Clean up session even if there was an error
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            if session_id in self.accumulated_transcripts:
                del self.accumulated_transcripts[session_id]
            return False
    
    async def _handle_speechmatics_messages(self, session_id: str):
        """Handle incoming messages from Speechmatics WebSocket."""
        try:
            if session_id not in self.active_sessions:
                return
            
            session = self.active_sessions[session_id]
            websocket = session["websocket"]
            on_transcript = session["on_transcript"]
            on_partial = session["on_partial"]
            on_error = session["on_error"]
            
            async for message in websocket:
                try:
                    logger.info(f"Raw message from Speechmatics: {message}")
                    data = json.loads(message)
                    message_type = data.get("message", "")
                    logger.info(f"Parsed message type: {message_type}, data: {data}")
                    
                    if message_type == "AddPartialTranscript":
                        # Partial transcript - accumulate for live display and future AI processing
                        # Try to get transcript from metadata first, then from results
                        partial_text = data.get("metadata", {}).get("transcript", "").strip()
                        
                        # If metadata transcript is empty, try to extract from results
                        if not partial_text:
                            results = data.get("results", [])
                            if results:
                                # Get the latest result (most recent word/phrase)
                                latest_result = results[-1]
                                alternatives = latest_result.get("alternatives", [])
                                if alternatives:
                                    partial_text = alternatives[0].get("content", "").strip()
                        
                        # Debug logging to see what we're actually receiving
                        logger.info(f"🔍 DEBUG: AddPartialTranscript received - transcript: '{partial_text}', full data: {data}")
                        
                        if partial_text and len(partial_text.strip()) > 0:
                            # Accumulate the transcript for this session
                            if session_id not in self.accumulated_transcripts:
                                self.accumulated_transcripts[session_id] = ""
                            
                            # Update accumulated transcript with the latest partial
                            self.accumulated_transcripts[session_id] = partial_text
                            
                            # Send partial transcript for live display
                            partial_data = {
                                "transcript": partial_text,
                                "confidence": data.get("metadata", {}).get("confidence", 0.0),
                                "start_time": data.get("metadata", {}).get("start_time", 0.0),
                                "end_time": data.get("metadata", {}).get("end_time", 0.0),
                                "language": session["language"],
                                "is_final": False
                            }
                            if on_partial:
                                on_partial(partial_data)
                            logger.debug(f"📝 PARTIAL TRANSCRIPT (accumulated): '{partial_text}'")
                        else:
                            logger.debug(f"Skipping empty partial transcript: '{partial_text}'")
                    
                    elif message_type == "EndOfUtterance":
                        # Natural conversation break - this is our cue to send to AI!
                        logger.info(f"🗣️ End of utterance detected for session: {session_id}")
                        
                        # Get the accumulated transcript and send to AI
                        accumulated_text = self.accumulated_transcripts.get(session_id, "").strip()
                        
                        if accumulated_text and len(accumulated_text) > 0:
                            # Send the accumulated transcript to AI for back-and-forth conversation
                            transcript_data = {
                                "transcript": accumulated_text,
                                "confidence": 1.0,  # We'll use a default confidence
                                "start_time": 0.0,
                                "end_time": 0.0,
                                "language": session["language"],
                                "is_final": True
                            }
                            if on_transcript:
                                on_transcript(transcript_data)
                            logger.info(f"🎯 END OF UTTERANCE TRIGGER (AI response): '{accumulated_text}'")
                            
                            # Clear the accumulated transcript for next utterance
                            self.accumulated_transcripts[session_id] = ""
                        else:
                            logger.debug(f"No accumulated transcript to send for session: {session_id}")
                        
                    elif message_type == "AddTranscript":
                        # Final transcript - use as fallback when EndOfUtterance is not available
                        # Try to get transcript from metadata first, then from results
                        transcript_text = data.get("metadata", {}).get("transcript", "").strip()
                        
                        # If metadata transcript is empty, try to extract from results
                        if not transcript_text:
                            results = data.get("results", [])
                            if results:
                                # Get the latest result (most recent word/phrase)
                                latest_result = results[-1]
                                alternatives = latest_result.get("alternatives", [])
                                if alternatives:
                                    transcript_text = alternatives[0].get("content", "").strip()
                        
                        if transcript_text and len(transcript_text) > 0:
                            # Check if this is a meaningful transcript (not just punctuation)
                            meaningful_text = transcript_text.strip(".,!? ")
                            
                            # Only send to AI if it's a complete thought (has punctuation or is long enough)
                            is_complete_thought = (
                                # Must have meaningful content (not just punctuation)
                                len(meaningful_text) > 0 and
                                (
                                    # Ends with sentence punctuation AND has meaningful content
                                    (transcript_text.endswith(('.', '!', '?')) and len(meaningful_text) > 2) or
                                    # Long enough to be meaningful
                                    len(meaningful_text) > 10 or
                                    # Contains question/request words
                                    any(word in meaningful_text.lower() for word in ['hello', 'hi', 'how', 'what', 'where', 'when', 'why', 'can', 'could', 'would', 'should', 'please', 'thank', 'thanks'])
                                )
                            )
                            
                            if is_complete_thought:
                                # Use AddTranscript as fallback for AI responses
                                transcript_data = {
                                    "transcript": transcript_text,
                                    "confidence": 1.0,
                                    "start_time": data.get("metadata", {}).get("start_time", 0.0),
                                    "end_time": data.get("metadata", {}).get("end_time", 0.0),
                                    "language": session["language"],
                                    "is_final": True
                                }
                                if on_transcript:
                                    on_transcript(transcript_data)
                                logger.info(f"📄 FINAL TRANSCRIPT (AI fallback): '{transcript_text}'")
                            else:
                                logger.debug(f"📄 FINAL TRANSCRIPT (incomplete thought): '{transcript_text}'")
                        else:
                            logger.debug(f"📄 FINAL TRANSCRIPT (empty): '{transcript_text}'")
                    
                    elif message_type == "Error":
                        # Error message
                        error_data = {
                            "error": data.get("error", {}).get("type", "unknown"),
                            "message": data.get("error", {}).get("message", "Unknown error"),
                            "code": data.get("error", {}).get("code", 0)
                        }
                        if on_error:
                            on_error(error_data)
                        logger.error(f"Speechmatics error: {error_data}")
                    
                    elif message_type == "RecognitionStarted":
                        logger.info(f"Recognition started for session: {session_id}")
                    
                    elif message_type == "EndOfTranscript":
                        logger.info(f"End of transcript for session: {session_id}")
                    
                    elif message_type == "Info":
                        # Handle info messages (usage, quality, etc.)
                        info_type = data.get("type", "")
                        if info_type == "concurrent_session_usage":
                            logger.info(f"Session usage: {data.get('usage', 0)}/{data.get('quota', 0)}")
                        elif info_type == "recognition_quality":
                            logger.info(f"Recognition quality: {data.get('quality', 'unknown')}")
                        else:
                            logger.info(f"Info message: {data}")
                    
                    else:
                        logger.info(f"Unhandled message type: {message_type}")
                    
                except json.JSONDecodeError:
                    logger.error("Invalid JSON received from Speechmatics")
                except Exception as e:
                    logger.error(f"Error processing Speechmatics message: {e}")
                    
        except ConnectionClosed:
            logger.info(f"Speechmatics WebSocket closed for session: {session_id}")
        except Exception as e:
            logger.error(f"Error in message handler for session {session_id}: {e}")
        finally:
            # Clean up session
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            if session_id in self.accumulated_transcripts:
                del self.accumulated_transcripts[session_id]
    
    async def convert_webm_to_pcm_stream(
        self,
        webm_data: bytes
    ) -> AsyncGenerator[bytes, None]:
        """Convert WebM data to PCM stream for real-time processing."""
        import subprocess
        import tempfile
        
        try:
            # Create temporary files
            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_webm:
                temp_webm.write(webm_data)
                temp_webm_path = temp_webm.name
            
            # Use ffmpeg to convert WebM to raw PCM
            cmd = [
                'ffmpeg',
                '-i', temp_webm_path,
                '-f', 's16le',        # 16-bit signed little-endian PCM
                '-ar', '16000',       # 16kHz sample rate
                '-ac', '1',           # Mono
                '-t', '10',           # Max 10 seconds
                'pipe:1'              # Output to stdout
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Stream PCM data in chunks
            chunk_size = 1024  # 1KB chunks
            while True:
                chunk = await process.stdout.read(chunk_size)
                if not chunk:
                    break
                yield chunk
            
            # Wait for process to complete
            await process.wait()
            
        except Exception as e:
            logger.error(f"Error converting WebM to PCM stream: {e}")
        finally:
            # Clean up temporary file
            try:
                import os
                os.unlink(temp_webm_path)
            except:
                pass
    
    async def close_all_sessions(self):
        """Close all active streaming sessions."""
        for session_id in list(self.active_sessions.keys()):
            await self.stop_streaming_session(session_id)


# Global streaming service instance
speechmatics_streaming_service = SpeechmaticsStreamingService()


class StreamingWebSocketHandler:
    """WebSocket handler for real-time audio streaming."""
    
    def __init__(self):
        self.service = speechmatics_streaming_service
        self.last_transcript_time = {}  # Track last transcript time per session
        self.processing_transcripts = set()  # Track transcripts being processed
    
    async def handle_streaming_connection(
        self,
        websocket: WebSocketServerProtocol,
        session_id: str,
        language: str = "en"
    ):
        """Handle WebSocket connection for conversational voice chat."""
        try:
            logger.info(f"Starting conversational WebSocket session: {session_id}")
            
            # Callbacks for handling transcription results
            def on_transcript(transcript_data):
                asyncio.create_task(self._send_to_client(websocket, {
                    "type": "transcript",
                    "data": transcript_data
                }))
            
            def on_partial(partial_data):
                asyncio.create_task(self._send_to_client(websocket, {
                    "type": "partial_transcript",
                    "data": partial_data
                }))
            
            def on_error(error_data):
                # Handle both string and dict error data
                if isinstance(error_data, str):
                    error_message = error_data
                else:
                    error_message = error_data.get("message", str(error_data))
                
                asyncio.create_task(self._send_to_client(websocket, {
                    "type": "error",
                    "data": {"message": error_message}
                }))
            
            # Start streaming session
            success = await self.service.start_streaming_session(
                session_id=session_id,
                language=language,
                on_transcript=on_transcript,
                on_partial=on_partial,
                on_error=on_error
            )
            
            if not success:
                await websocket.send_json({
                    "type": "error",
                    "message": "Failed to start streaming session"
                })
                return
            
            # Send session started message
            await websocket.send_json({
                "type": "session_started",
                "session_id": session_id,
                "language": language
            })
            
            # Handle incoming messages
            while True:
                try:
                    message = await websocket.receive_text()
                    data = json.loads(message)
                    
                    if data.get("type") == "audio_chunk":
                        # Send audio chunk to Speechmatics
                        audio_data = base64.b64decode(data.get("audio_data", ""))
                        await self.service.send_audio_chunk(session_id, audio_data)
                    
                    elif data.get("type") == "pcm_audio":
                        # Direct PCM audio data (Int16 format from frontend)
                        pcm_data = data.get("audio_data", [])
                        # Convert Int16 array to bytes (little-endian)
                        import struct
                        pcm_bytes = b''.join(struct.pack('<h', int(sample)) for sample in pcm_data)
                        await self.service.send_audio_chunk(session_id, pcm_bytes)
                    
                    elif data.get("type") == "webm_audio":
                        # Fallback: Convert WebM to PCM stream and send
                        webm_data = base64.b64decode(data.get("audio_data", ""))
                        async for pcm_chunk in self.service.convert_webm_to_pcm_stream(webm_data):
                            await self.service.send_audio_chunk(session_id, pcm_chunk)
                    
                    elif data.get("type") == "final_transcript":
                        # Handle final transcript from user with debouncing
                        transcript = data.get("transcript", "").strip()
                        current_time = asyncio.get_event_loop().time()
                        
                        # Check if we're already processing this transcript or if it's too recent
                        transcript_key = f"{session_id}:{transcript}"
                        if (transcript_key in self.processing_transcripts or 
                            (session_id in self.last_transcript_time and 
                             current_time - self.last_transcript_time[session_id] < 2.0)):
                            logger.debug(f"Skipping duplicate/recent transcript: {transcript}")
                            continue
                        
                        # Mark as processing and update timestamp
                        self.processing_transcripts.add(transcript_key)
                        self.last_transcript_time[session_id] = current_time
                        
                        logger.info(f"Final transcript from user: {transcript}")
                        
                        try:
                            # Send to AI chatbot and get response
                            ai_response = await self._get_ai_response(transcript)
                            
                            # Send AI response back to client
                            await websocket.send_json({
                                "type": "ai_response",
                                "data": ai_response
                            })
                        finally:
                            # Remove from processing set
                            self.processing_transcripts.discard(transcript_key)
                    
                    elif data.get("type") == "ai_response":
                        # Forward AI response (already processed)
                        await websocket.send_json({
                            "type": "ai_response",
                            "data": data
                        })
                    
                    elif data.get("type") == "stop_recording":
                        # Stop the session
                        await self.service.stop_streaming_session(session_id)
                        await websocket.send_json({
                            "type": "session_stopped",
                            "session_id": session_id
                        })
                        break
                        
                except json.JSONDecodeError:
                    logger.error("Invalid JSON received from WebSocket")
                except Exception as e:
                    logger.error(f"Error processing WebSocket message: {e}")
                    break
                    
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for session: {session_id}")
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebSocket connection closed for session: {session_id}")
        except Exception as e:
            logger.error(f"Error in conversational WebSocket handler: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
        finally:
            try:
                await self.service.stop_streaming_session(session_id)
            except Exception as cleanup_error:
                logger.warning(f"Error during session cleanup: {cleanup_error}")
    
    async def _get_ai_response(self, transcript: str) -> Dict[str, Any]:
        """Get AI response for the transcript."""
        try:
            from ..services.ai_chatbot_service import ai_chatbot_service
            
            # Get AI response
            ai_result = await ai_chatbot_service.generate_response(
                message=transcript,
                user_id="test-user"
            )
            
            # Generate TTS audio if available
            audio_url = None
            if ai_result.get("content"):
                try:
                    from ..services.tts_service import tts_service
                    tts_result = await tts_service.generate_speech(
                        text=ai_result["content"],
                        voice="default"
                    )
                    audio_url = tts_result.get("audio_url")
                except Exception as tts_error:
                    logger.warning(f"TTS failed: {tts_error}")
            
            return {
                "content": ai_result.get("content", "I'm sorry, I couldn't process that."),
                "audio_url": audio_url,
                "provider": ai_result.get("provider", "unknown")
            }
            
        except Exception as e:
            logger.error(f"Error getting AI response: {e}")
            return {
                "content": "I'm sorry, I encountered an error processing your message.",
                "audio_url": None,
                "provider": "error"
            }
    
    async def _send_to_client(self, websocket: WebSocketServerProtocol, message: Dict[str, Any]):
        """Send message to client WebSocket."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message to client: {e}")


# Global streaming WebSocket handler instance
streaming_websocket_handler = StreamingWebSocketHandler()
