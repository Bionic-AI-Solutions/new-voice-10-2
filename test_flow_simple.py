#!/usr/bin/env python3
"""
Simple test script for Speechmatics Flow Voice API
Tests basic connection and message exchange
"""

import asyncio
import json
import websockets

async def test_flow_connection():
    """Test basic connection to Flow API"""
    api_key = "your-speechmatics-api-key-here"
    flow_url = "wss://flow.api.speechmatics.com/"
    
    print("Testing Flow Voice API connection...")
    print(f"URL: {flow_url}")
    print(f"API Key: {api_key[:20]}...")
    
    try:
        # Connect to Flow API
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        async with websockets.connect(
            flow_url,
            additional_headers=headers,
            ping_interval=20,
            ping_timeout=10
        ) as websocket:
            print("Connected to Flow API successfully!")
            
            # Test StartConversation message
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
            
            await websocket.send(json.dumps(start_message))
            print("Sent StartConversation message")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                data = json.loads(response)
                
                if data.get("message") == "ConversationStarted":
                    print("SUCCESS: Conversation started!")
                    print(f"Session ID: {data.get('id')}")
                    print(f"Orchestrator Version: {data.get('orchestrator_version')}")
                    return True
                else:
                    print(f"Unexpected response: {data}")
                    return False
                    
            except asyncio.TimeoutError:
                print("ERROR: Timeout waiting for ConversationStarted")
                return False
                
    except Exception as e:
        print(f"ERROR: Connection failed: {e}")
        return False

async def main():
    """Main test function"""
    print("Speechmatics Flow Voice API Test")
    print("=" * 50)
    
    success = await test_flow_connection()
    
    if success:
        print("\nAll tests passed!")
    else:
        print("\nSome tests failed!")

if __name__ == "__main__":
    asyncio.run(main())
