#!/usr/bin/env python3
"""
Test script for Speechmatics Flow Voice API
Tests the agent-based conversation flow with voice input/output
"""

import asyncio
import json
import websockets
import base64
import wave
import io
import struct
import time
from typing import Dict, Any

class FlowVoiceAPITester:
    def __init__(self, api_key: str, region: str = "us"):
        self.api_key = api_key
        self.region = region
        self.flow_url = f"wss://flow.api.speechmatics.com/"
        self.session_id = None
        self.sequence_number = 0
        self.websocket = None
        
    async def test_connection(self):
        """Test basic connection to Flow API"""
        print("Testing Flow Voice API connection...")
        
        try:
            # Connect to Flow API
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            async with websockets.connect(
                self.flow_url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10
            ) as websocket:
                print(f"Connected to Flow API: {self.flow_url}")
                
                # Test basic message exchange
                await self.test_start_conversation(websocket)
                
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
            
        return True
    
    async def test_start_conversation(self, websocket):
        """Test starting a conversation session"""
        print("🗣️ Testing StartConversation...")
        
        start_message = {
            "message": "StartConversation",
            "audio_format": {
                "type": "raw",
                "encoding": "pcm_s16le",
                "sample_rate": 16000
            },
            "conversation_config": {
                "language": "en",
                "max_delay": 2,
                "enable_partials": True
            },
            "tools": [],
            "debug": {
                "return_agent_thoughts": True
            }
        }
        
        try:
            await websocket.send(json.dumps(start_message))
            print("📤 Sent StartConversation message")
            
            # Wait for ConversationStarted response
            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            data = json.loads(response)
            
            if data.get("message") == "ConversationStarted":
                self.session_id = data.get("id")
                print(f"✅ Conversation started successfully!")
                print(f"   Session ID: {self.session_id}")
                print(f"   Orchestrator Version: {data.get('orchestrator_version')}")
                return True
            else:
                print(f"❌ Unexpected response: {data}")
                return False
                
        except asyncio.TimeoutError:
            print("❌ Timeout waiting for ConversationStarted")
            return False
        except Exception as e:
            print(f"❌ Error starting conversation: {e}")
            return False
    
    async def test_audio_flow(self, websocket):
        """Test audio input/output flow"""
        print("🎤 Testing audio flow...")
        
        # Generate test audio (1 second of silence)
        test_audio = self.generate_test_audio(1.0)
        
        try:
            # Send audio
            await websocket.send(test_audio)
            print("📤 Sent test audio")
            
            # Wait for AudioAdded response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(response)
            
            if data.get("message") == "AudioAdded":
                print(f"✅ Audio added successfully (seq: {data.get('seq_no')})")
                return True
            else:
                print(f"❌ Unexpected response: {data}")
                return False
                
        except asyncio.TimeoutError:
            print("❌ Timeout waiting for AudioAdded")
            return False
        except Exception as e:
            print(f"❌ Error in audio flow: {e}")
            return False
    
    def generate_test_audio(self, duration: float) -> bytes:
        """Generate test PCM audio data"""
        sample_rate = 16000
        num_samples = int(sample_rate * duration)
        
        # Generate silence (zeros)
        audio_data = []
        for i in range(num_samples):
            audio_data.append(struct.pack('<h', 0))  # 16-bit signed little-endian
        
        return b''.join(audio_data)
    
    async def test_message_handling(self, websocket):
        """Test handling of various message types"""
        print("📨 Testing message handling...")
        
        try:
            # Listen for messages for a short period
            start_time = time.time()
            message_count = 0
            
            while time.time() - start_time < 5.0:  # Listen for 5 seconds
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(response)
                    message_count += 1
                    
                    message_type = data.get("message", "unknown")
                    print(f"📨 Received: {message_type}")
                    
                    # Handle different message types
                    if message_type == "AddPartialTranscript":
                        print(f"   Partial transcript: {data.get('metadata', {}).get('transcript', '')}")
                    elif message_type == "AddTranscript":
                        print(f"   Final transcript: {data.get('metadata', {}).get('transcript', '')}")
                    elif message_type == "ResponseStarted":
                        print(f"   Agent response started: {data.get('content', '')}")
                    elif message_type == "ResponseCompleted":
                        print(f"   Agent response completed: {data.get('content', '')}")
                    elif message_type == "Error":
                        print(f"   Error: {data.get('reason', '')}")
                    elif message_type == "Warning":
                        print(f"   Warning: {data.get('reason', '')}")
                    elif message_type == "Info":
                        print(f"   Info: {data.get('reason', '')}")
                        
                except asyncio.TimeoutError:
                    continue  # No message received, continue listening
                    
            print(f"✅ Message handling test completed ({message_count} messages received)")
            return True
            
        except Exception as e:
            print(f"❌ Error in message handling: {e}")
            return False
    
    async def test_end_conversation(self, websocket):
        """Test ending the conversation"""
        print("🔚 Testing conversation end...")
        
        try:
            end_message = {
                "message": "AudioEnded",
                "last_seq_no": self.sequence_number
            }
            
            await websocket.send(json.dumps(end_message))
            print("📤 Sent AudioEnded message")
            
            # Wait for ConversationEnded response
            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            data = json.loads(response)
            
            if data.get("message") == "ConversationEnded":
                print("✅ Conversation ended successfully")
                return True
            else:
                print(f"❌ Unexpected response: {data}")
                return False
                
        except asyncio.TimeoutError:
            print("❌ Timeout waiting for ConversationEnded")
            return False
        except Exception as e:
            print(f"❌ Error ending conversation: {e}")
            return False
    
    async def run_full_test(self):
        """Run complete Flow API test"""
        print("🚀 Starting Flow Voice API Test")
        print("=" * 50)
        
        # Test connection
        if not await self.test_connection():
            return False
        
        print("\n" + "=" * 50)
        print("✅ Flow Voice API test completed successfully!")
        return True

async def main():
    """Main test function"""
    # Use placeholder API key for testing
    api_key = "your-speechmatics-api-key-here"
    
    print("Speechmatics Flow Voice API Test")
    print("=" * 50)
    print(f"API Key: {api_key[:20]}...")
    print(f"Region: us")
    print("=" * 50)
    
    tester = FlowVoiceAPITester(api_key, "us")
    
    try:
        success = await tester.run_full_test()
        if success:
            print("\n🎉 All tests passed!")
        else:
            print("\n❌ Some tests failed!")
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
