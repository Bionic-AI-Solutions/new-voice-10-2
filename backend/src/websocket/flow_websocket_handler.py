"""
WebSocket handler for Flow Voice API
Handles client connections and manages Flow conversation sessions
"""

import asyncio
import json
import logging
import struct
from typing import Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from ..services.flow_voice_service import FlowVoiceService, FlowConversationConfig, FlowAudioFormat, FlowTool

logger = logging.getLogger(__name__)

class FlowWebSocketHandler:
    """WebSocket handler for Flow Voice API conversations"""
    
    def __init__(self, flow_service: FlowVoiceService):
        self.flow_service = flow_service
        self.active_connections: Dict[str, WebSocket] = {}
        
    async def handle_flow_connection(self, websocket: WebSocket, session_id: str):
        """Handle a new Flow Voice API WebSocket connection"""
        
        await websocket.accept()
        self.active_connections[session_id] = websocket
        
        logger.info(f"🔌 Flow WebSocket connected: {session_id}")
        
        try:
            # Send connection confirmation
            await websocket.send_json({
                "type": "flow_connected",
                "session_id": session_id,
                "message": "Connected to Flow Voice API"
            })
            
            # Start Flow conversation session
            conversation_config = FlowConversationConfig(
                language="en",
                max_delay=2,
                enable_partials=True,
                enable_entities=True
            )
            
            audio_format = FlowAudioFormat(
                type="raw",
                encoding="pcm_s16le",
                sample_rate=16000
            )
            
            # Define tools for the agent
            tools = [
                FlowTool(
                    name="get_weather",
                    description="Get current weather information for a location",
                    parameters={
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The city and state/country"
                            }
                        },
                        "required": ["location"]
                    }
                ),
                FlowTool(
                    name="calculate",
                    description="Perform mathematical calculations",
                    parameters={
                        "type": "object",
                        "properties": {
                            "expression": {
                                "type": "string",
                                "description": "Mathematical expression to evaluate"
                            }
                        },
                        "required": ["expression"]
                    }
                )
            ]
            
            # Start Flow conversation
            success = await self.flow_service.start_conversation_session(
                session_id=session_id,
                conversation_config=conversation_config,
                audio_format=audio_format,
                tools=tools,
                on_transcript=self._on_transcript,
                on_partial_transcript=self._on_partial_transcript,
                on_agent_response=self._on_agent_response,
                on_tool_invoke=self._on_tool_invoke,
                on_error=self._on_error
            )
            
            if not success:
                await websocket.send_json({
                    "type": "error",
                    "message": "Failed to start Flow conversation"
                })
                return
            
            # Send session started confirmation
            await websocket.send_json({
                "type": "flow_session_started",
                "session_id": session_id,
                "message": "Flow conversation session started"
            })
            
            # Handle incoming messages
            while True:
                try:
                    message = await websocket.receive_text()
                    data = json.loads(message)
                    await self._handle_client_message(session_id, data)
                    
                except WebSocketDisconnect:
                    logger.info(f"🔌 Flow WebSocket disconnected: {session_id}")
                    break
                except json.JSONDecodeError:
                    logger.error(f"❌ Invalid JSON from client {session_id}: {message}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid JSON message"
                    })
                except Exception as e:
                    logger.error(f"❌ Error handling client message for {session_id}: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Error processing message: {str(e)}"
                    })
                    
        except Exception as e:
            logger.error(f"❌ Error in Flow WebSocket handler for {session_id}: {e}")
        finally:
            # Cleanup
            await self._cleanup_session(session_id)
    
    async def _handle_client_message(self, session_id: str, data: Dict[str, Any]):
        """Handle incoming message from client"""
        
        message_type = data.get("type", "")
        
        try:
            if message_type == "audio_data":
                # Handle audio data
                audio_data = data.get("data", [])
                if audio_data:
                    # Convert Int16 array to bytes
                    audio_bytes = b''.join(struct.pack('<h', int(sample)) for sample in audio_data)
                    await self.flow_service.send_audio(session_id, audio_bytes)
                    
            elif message_type == "text_input":
                # Handle text input
                input_text = data.get("text", "")
                interrupt_response = data.get("interrupt_response", False)
                immediate = data.get("immediate", False)
                
                if input_text:
                    await self.flow_service.send_input(
                        session_id, 
                        input_text, 
                        interrupt_response, 
                        immediate
                    )
                    
            elif message_type == "tool_result":
                # Handle tool execution result
                tool_id = data.get("tool_id", "")
                status = data.get("status", "ok")
                content = data.get("content", "")
                
                if tool_id:
                    await self.flow_service.send_tool_result(session_id, tool_id, status, content)
                    
            elif message_type == "end_conversation":
                # Handle conversation end
                await self.flow_service.end_conversation(session_id)
                await self.active_connections[session_id].send_json({
                    "type": "conversation_ended",
                    "message": "Conversation ended"
                })
                
            else:
                logger.warning(f"⚠️ Unknown message type from client {session_id}: {message_type}")
                
        except Exception as e:
            logger.error(f"❌ Error handling client message for {session_id}: {e}")
            await self.active_connections[session_id].send_json({
                "type": "error",
                "message": f"Error processing {message_type}: {str(e)}"
            })
    
    async def _on_transcript(self, data: Dict[str, Any]):
        """Handle final transcript from Flow API"""
        
        # Extract transcript text
        transcript = ""
        if "metadata" in data and "transcript" in data["metadata"]:
            transcript = data["metadata"]["transcript"]
        elif "results" in data and len(data["results"]) > 0:
            result = data["results"][-1]
            if "alternatives" in result and len(result["alternatives"]) > 0:
                transcript = result["alternatives"][0].get("content", "")
        
        if transcript:
            # Find the session ID for this transcript
            for session_id in self.flow_service.list_active_sessions():
                if session_id in self.active_connections:
                    await self.active_connections[session_id].send_json({
                        "type": "transcript",
                        "data": {
                            "transcript": transcript,
                            "metadata": data.get("metadata", {}),
                            "results": data.get("results", [])
                        }
                    })
                    break
    
    async def _on_partial_transcript(self, data: Dict[str, Any]):
        """Handle partial transcript from Flow API"""
        
        # Extract partial transcript text
        partial_transcript = ""
        if "metadata" in data and "transcript" in data["metadata"]:
            partial_transcript = data["metadata"]["transcript"]
        elif "results" in data and len(data["results"]) > 0:
            result = data["results"][-1]
            if "alternatives" in result and len(result["alternatives"]) > 0:
                partial_transcript = result["alternatives"][0].get("content", "")
        
        if partial_transcript:
            # Find the session ID for this partial transcript
            for session_id in self.flow_service.list_active_sessions():
                if session_id in self.active_connections:
                    await self.active_connections[session_id].send_json({
                        "type": "partial_transcript",
                        "data": {
                            "transcript": partial_transcript,
                            "metadata": data.get("metadata", {}),
                            "results": data.get("results", [])
                        }
                    })
                    break
    
    async def _on_agent_response(self, data: Dict[str, Any]):
        """Handle agent response from Flow API"""
        
        response_type = data.get("type", "")
        content = data.get("content", "")
        
        # Find the session ID for this response
        for session_id in self.flow_service.list_active_sessions():
            if session_id in self.active_connections:
                await self.active_connections[session_id].send_json({
                    "type": "agent_response",
                    "data": {
                        "response_type": response_type,
                        "content": content,
                        "start_time": data.get("start_time", 0.0),
                        "end_time": data.get("end_time", 0.0)
                    }
                })
                break
    
    async def _on_tool_invoke(self, data: Dict[str, Any]):
        """Handle tool invocation from Flow API"""
        
        tool_id = data.get("id", "")
        function_data = data.get("function", {})
        
        # Find the session ID for this tool invoke
        for session_id in self.flow_service.list_active_sessions():
            if session_id in self.active_connections:
                await self.active_connections[session_id].send_json({
                    "type": "tool_invoke",
                    "data": {
                        "tool_id": tool_id,
                        "function": function_data
                    }
                })
                break
    
    async def _on_error(self, data: Dict[str, Any]):
        """Handle error from Flow API"""
        
        error_type = data.get("type", "unknown_error")
        reason = data.get("reason", "Unknown error")
        code = data.get("code", 0)
        
        # Find the session ID for this error
        for session_id in self.flow_service.list_active_sessions():
            if session_id in self.active_connections:
                await self.active_connections[session_id].send_json({
                    "type": "flow_error",
                    "data": {
                        "error_type": error_type,
                        "reason": reason,
                        "code": code
                    }
                })
                break
    
    async def _cleanup_session(self, session_id: str):
        """Clean up session resources"""
        
        try:
            # End Flow conversation
            await self.flow_service.end_conversation(session_id)
            
            # Remove from active connections
            if session_id in self.active_connections:
                del self.active_connections[session_id]
                
            logger.info(f"🧹 Cleaned up Flow session: {session_id}")
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up Flow session {session_id}: {e}")
    
    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)
    
    def get_active_sessions(self) -> list[str]:
        """Get list of active session IDs"""
        return list(self.active_connections.keys())
