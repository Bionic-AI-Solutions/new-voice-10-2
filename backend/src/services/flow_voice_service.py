"""
Speechmatics Flow Voice API Service
Handles agent-based conversational voice interactions
"""

import asyncio
import json
import logging
import websockets
import struct
from typing import Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class FlowMessageType(Enum):
    """Flow API message types"""
    START_CONVERSATION = "StartConversation"
    CONVERSATION_STARTED = "ConversationStarted"
    ADD_AUDIO = "AddAudio"
    AUDIO_ADDED = "AudioAdded"
    AUDIO_RECEIVED = "AudioReceived"
    AUDIO_ENDED = "AudioEnded"
    ADD_PARTIAL_TRANSCRIPT = "AddPartialTranscript"
    ADD_TRANSCRIPT = "AddTranscript"
    RESPONSE_STARTED = "ResponseStarted"
    RESPONSE_COMPLETED = "ResponseCompleted"
    RESPONSE_INTERRUPTED = "ResponseInterrupted"
    TOOL_INVOKE = "ToolInvoke"
    TOOL_RESULT = "ToolResult"
    CONVERSATION_ENDING = "ConversationEnding"
    CONVERSATION_ENDED = "ConversationEnded"
    ERROR = "Error"
    WARNING = "Warning"
    INFO = "Info"

@dataclass
class FlowConversationConfig:
    """Configuration for Flow conversation"""
    language: str = "en"
    max_delay: int = 2
    enable_partials: bool = True
    enable_entities: bool = True
    enable_sentiment: bool = False
    enable_topics: bool = False

@dataclass
class FlowAudioFormat:
    """Audio format configuration"""
    type: str = "raw"
    encoding: str = "pcm_s16le"
    sample_rate: int = 16000

@dataclass
class FlowTool:
    """Tool definition for function calling"""
    name: str
    description: str
    parameters: Dict[str, Any]

class FlowVoiceService:
    """Service for handling Speechmatics Flow Voice API interactions"""
    
    def __init__(self, api_key: str, region: str = "us"):
        self.api_key = api_key
        self.region = region
        self.flow_url = f"wss://flow.api.speechmatics.com/"
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.sequence_numbers: Dict[str, int] = {}
        
    async def start_conversation_session(
        self,
        session_id: str,
        conversation_config: FlowConversationConfig,
        audio_format: FlowAudioFormat,
        tools: list[FlowTool] = None,
        on_transcript: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        on_partial_transcript: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        on_agent_response: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        on_tool_invoke: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        on_error: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
    ) -> bool:
        """Start a new Flow conversation session"""
        
        if session_id in self.active_sessions:
            logger.warning(f"Session {session_id} already exists")
            return False
        
        try:
            # Connect to Flow API
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            websocket = await websockets.connect(
                self.flow_url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10
            )
            
            # Initialize session
            self.active_sessions[session_id] = {
                "websocket": websocket,
                "conversation_config": conversation_config,
                "audio_format": audio_format,
                "tools": tools or [],
                "on_transcript": on_transcript,
                "on_partial_transcript": on_partial_transcript,
                "on_agent_response": on_agent_response,
                "on_tool_invoke": on_tool_invoke,
                "on_error": on_error,
                "started": False
            }
            self.sequence_numbers[session_id] = 0
            
            # Start conversation
            start_message = {
                "message": FlowMessageType.START_CONVERSATION.value,
                "audio_format": {
                    "type": audio_format.type,
                    "encoding": audio_format.encoding,
                    "sample_rate": audio_format.sample_rate
                },
                "conversation_config": {
                    "language": conversation_config.language,
                    "max_delay": conversation_config.max_delay,
                    "enable_partials": conversation_config.enable_partials,
                    "enable_entities": conversation_config.enable_entities,
                    "enable_sentiment": conversation_config.enable_sentiment,
                    "enable_topics": conversation_config.enable_topics
                },
                "tools": [self._tool_to_dict(tool) for tool in tools] if tools else [],
                "debug": {
                    "return_agent_thoughts": True
                }
            }
            
            await websocket.send(json.dumps(start_message))
            logger.info(f"📤 Sent StartConversation for session: {session_id}")
            
            # Start message handling task
            asyncio.create_task(self._handle_flow_messages(session_id))
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start Flow session {session_id}: {e}")
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            return False
    
    async def send_audio(self, session_id: str, audio_data: bytes) -> bool:
        """Send audio data to Flow API"""
        
        if session_id not in self.active_sessions:
            logger.error(f"Session {session_id} not found")
            return False
        
        try:
            session = self.active_sessions[session_id]
            websocket = session["websocket"]
            
            # Send binary audio data
            await websocket.send(audio_data)
            
            # Increment sequence number
            self.sequence_numbers[session_id] += 1
            
            logger.debug(f"📤 Sent audio data for session: {session_id} (seq: {self.sequence_numbers[session_id]})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send audio for session {session_id}: {e}")
            return False
    
    async def send_input(self, session_id: str, input_text: str, interrupt_response: bool = False, immediate: bool = False) -> bool:
        """Send text input to influence the conversation"""
        
        if session_id not in self.active_sessions:
            logger.error(f"Session {session_id} not found")
            return False
        
        try:
            session = self.active_sessions[session_id]
            websocket = session["websocket"]
            
            input_message = {
                "message": "AddInput",
                "input": input_text,
                "interrupt_response": interrupt_response,
                "immediate": immediate
            }
            
            await websocket.send(json.dumps(input_message))
            logger.info(f"📤 Sent input for session: {session_id}: {input_text}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send input for session {session_id}: {e}")
            return False
    
    async def send_tool_result(self, session_id: str, tool_id: str, status: str, content: str = None) -> bool:
        """Send tool execution result back to Flow API"""
        
        if session_id not in self.active_sessions:
            logger.error(f"Session {session_id} not found")
            return False
        
        try:
            session = self.active_sessions[session_id]
            websocket = session["websocket"]
            
            tool_result = {
                "message": "ToolResult",
                "id": tool_id,
                "status": status,
                "content": content
            }
            
            await websocket.send(json.dumps(tool_result))
            logger.info(f"📤 Sent tool result for session: {session_id}, tool: {tool_id}, status: {status}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send tool result for session {session_id}: {e}")
            return False
    
    async def end_conversation(self, session_id: str) -> bool:
        """End the Flow conversation session"""
        
        if session_id not in self.active_sessions:
            logger.error(f"Session {session_id} not found")
            return False
        
        try:
            session = self.active_sessions[session_id]
            websocket = session["websocket"]
            
            # Send AudioEnded message
            end_message = {
                "message": "AudioEnded",
                "last_seq_no": self.sequence_numbers.get(session_id, 0)
            }
            
            await websocket.send(json.dumps(end_message))
            logger.info(f"📤 Sent AudioEnded for session: {session_id}")
            
            # Wait for ConversationEnded or close after timeout
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                if data.get("message") == "ConversationEnded":
                    logger.info(f"✅ Conversation ended for session: {session_id}")
            except asyncio.TimeoutError:
                logger.warning(f"⏰ Timeout waiting for ConversationEnded for session: {session_id}")
            
            # Close websocket and cleanup
            await websocket.close()
            del self.active_sessions[session_id]
            if session_id in self.sequence_numbers:
                del self.sequence_numbers[session_id]
            
            logger.info(f"🔚 Session {session_id} ended and cleaned up")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to end session {session_id}: {e}")
            # Cleanup on error
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            if session_id in self.sequence_numbers:
                del self.sequence_numbers[session_id]
            return False
    
    async def _handle_flow_messages(self, session_id: str):
        """Handle incoming messages from Flow API"""
        
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        websocket = session["websocket"]
        
        try:
            while True:
                message = await websocket.recv()
                
                # Handle binary audio data
                if isinstance(message, bytes):
                    await self._handle_audio_data(session_id, message)
                    continue
                
                # Handle JSON messages
                try:
                    data = json.loads(message)
                    await self._process_flow_message(session_id, data)
                except json.JSONDecodeError:
                    logger.error(f"❌ Invalid JSON message from Flow API: {message}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"🔌 Flow API connection closed for session: {session_id}")
        except Exception as e:
            logger.error(f"❌ Error handling Flow messages for session {session_id}: {e}")
        finally:
            # Cleanup on disconnect
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            if session_id in self.sequence_numbers:
                del self.sequence_numbers[session_id]
    
    async def _process_flow_message(self, session_id: str, data: Dict[str, Any]):
        """Process a Flow API message"""
        
        message_type = data.get("message", "")
        session = self.active_sessions.get(session_id, {})
        
        logger.debug(f"📨 Flow message for {session_id}: {message_type}")
        
        try:
            if message_type == "ConversationStarted":
                session["started"] = True
                logger.info(f"✅ Flow conversation started for session: {session_id}")
                
            elif message_type == "AudioAdded":
                seq_no = data.get("seq_no", 0)
                logger.debug(f"✅ Audio added for session: {session_id} (seq: {seq_no})")
                
            elif message_type == "AddPartialTranscript":
                if session.get("on_partial_transcript"):
                    await session["on_partial_transcript"](data)
                    
            elif message_type == "AddTranscript":
                if session.get("on_transcript"):
                    await session["on_transcript"](data)
                    
            elif message_type == "ResponseStarted":
                if session.get("on_agent_response"):
                    await session["on_agent_response"]({
                        "type": "response_started",
                        "content": data.get("content", ""),
                        "start_time": data.get("start_time", 0.0)
                    })
                    
            elif message_type == "ResponseCompleted":
                if session.get("on_agent_response"):
                    await session["on_agent_response"]({
                        "type": "response_completed",
                        "content": data.get("content", ""),
                        "start_time": data.get("start_time", 0.0),
                        "end_time": data.get("end_time", 0.0)
                    })
                    
            elif message_type == "ResponseInterrupted":
                if session.get("on_agent_response"):
                    await session["on_agent_response"]({
                        "type": "response_interrupted",
                        "content": data.get("content", ""),
                        "start_time": data.get("start_time", 0.0),
                        "end_time": data.get("end_time", 0.0)
                    })
                    
            elif message_type == "ToolInvoke":
                if session.get("on_tool_invoke"):
                    await session["on_tool_invoke"](data)
                    
            elif message_type == "Error":
                logger.error(f"❌ Flow API error for session {session_id}: {data.get('reason', '')}")
                if session.get("on_error"):
                    await session["on_error"](data)
                    
            elif message_type == "Warning":
                logger.warning(f"⚠️ Flow API warning for session {session_id}: {data.get('reason', '')}")
                
            elif message_type == "Info":
                logger.info(f"ℹ️ Flow API info for session {session_id}: {data.get('reason', '')}")
                
            elif message_type == "ConversationEnding":
                logger.info(f"🔚 Flow conversation ending for session: {session_id}")
                
            elif message_type == "ConversationEnded":
                logger.info(f"✅ Flow conversation ended for session: {session_id}")
                
        except Exception as e:
            logger.error(f"❌ Error processing Flow message for session {session_id}: {e}")
    
    async def _handle_audio_data(self, session_id: str, audio_data: bytes):
        """Handle incoming audio data from Flow API"""
        
        # This would typically be sent to the client for playback
        logger.debug(f"🎵 Received audio data for session: {session_id} ({len(audio_data)} bytes)")
        
        # For now, just log the audio data
        # In a real implementation, this would be sent to the client via WebSocket
    
    def _tool_to_dict(self, tool: FlowTool) -> Dict[str, Any]:
        """Convert FlowTool to dictionary format"""
        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters
        }
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a session"""
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        return {
            "session_id": session_id,
            "started": session.get("started", False),
            "sequence_number": self.sequence_numbers.get(session_id, 0),
            "tools_count": len(session.get("tools", []))
        }
    
    def list_active_sessions(self) -> list[str]:
        """List all active session IDs"""
        return list(self.active_sessions.keys())
