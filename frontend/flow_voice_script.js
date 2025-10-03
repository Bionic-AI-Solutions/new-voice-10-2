/**
 * Flow Voice AI Frontend Script
 * Handles agent-based conversational voice interface
 */

class FlowVoiceAI {
    constructor() {
        this.websocket = null;
        this.sessionId = null;
        this.isConnected = false;
        this.isRecording = false;
        this.audioContext = null;
        this.mediaStream = null;
        this.processor = null;
        this.audioLevel = 0;
        this.messageCount = 0;
        
        // DOM elements
        this.elements = {
            startFlowBtn: document.getElementById('startFlowBtn'),
            endFlowBtn: document.getElementById('endFlowBtn'),
            clearChatBtn: document.getElementById('clearChatBtn'),
            textInput: document.getElementById('textInput'),
            sendTextBtn: document.getElementById('sendTextBtn'),
            interruptResponse: document.getElementById('interruptResponse'),
            immediateInput: document.getElementById('immediateInput'),
            statusIndicator: document.getElementById('statusIndicator'),
            statusText: document.querySelector('.status-text'),
            sessionInfo: document.getElementById('sessionInfo'),
            sessionId: document.getElementById('sessionId'),
            chatMessages: document.getElementById('chatMessages'),
            toolPanel: document.getElementById('toolPanel'),
            toolContent: document.getElementById('toolContent'),
            audioIndicator: document.getElementById('audioIndicator'),
            audioText: document.getElementById('audioText'),
            levelFill: document.getElementById('levelFill'),
            debugToggle: document.getElementById('debugToggle'),
            debugContent: document.getElementById('debugContent'),
            connectionStatus: document.getElementById('connectionStatus'),
            sessionDebug: document.getElementById('sessionDebug'),
            messageLog: document.getElementById('messageLog')
        };
        
        this.initializeEventListeners();
        this.updateStatus('disconnected', 'Disconnected');
        this.logMessage('🚀 Flow Voice AI initialized');
    }
    
    initializeEventListeners() {
        // Button events
        this.elements.startFlowBtn.addEventListener('click', () => this.startFlowConversation());
        this.elements.endFlowBtn.addEventListener('click', () => this.endFlowConversation());
        this.elements.clearChatBtn.addEventListener('click', () => this.clearChat());
        this.elements.sendTextBtn.addEventListener('click', () => this.sendTextMessage());
        
        // Text input events
        this.elements.textInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendTextMessage();
            }
        });
        
        // Debug toggle
        this.elements.debugToggle.addEventListener('click', () => {
            const content = this.elements.debugContent;
            content.style.display = content.style.display === 'none' ? 'block' : 'none';
        });
        
        // Audio level monitoring
        this.startAudioLevelMonitoring();
    }
    
    async startFlowConversation() {
        try {
            this.logMessage('🚀 Starting Flow conversation...');
            this.updateStatus('connecting', 'Connecting...');
            
            // Generate session ID
            this.sessionId = `flow-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
            
            // Connect to WebSocket
            await this.connectWebSocket();
            
            // Initialize audio
            await this.initializeAudio();
            
            this.updateStatus('connected', 'Connected');
            this.elements.startFlowBtn.disabled = true;
            this.elements.endFlowBtn.disabled = false;
            this.elements.textInput.disabled = false;
            this.elements.sendTextBtn.disabled = false;
            
            this.elements.sessionId.textContent = this.sessionId;
            this.elements.sessionInfo.style.display = 'block';
            
            this.addMessage('system', 'Flow conversation started! You can now speak or type messages.');
            this.logMessage('✅ Flow conversation started successfully');
            
        } catch (error) {
            this.logMessage(`❌ Failed to start Flow conversation: ${error.message}`);
            this.updateStatus('error', 'Connection Failed');
            this.addMessage('error', `Failed to start conversation: ${error.message}`);
        }
    }
    
    async connectWebSocket() {
        return new Promise((resolve, reject) => {
            const wsUrl = `ws://localhost:8080/ws/flow/${this.sessionId}`;
            this.logMessage(`🔌 Connecting to: ${wsUrl}`);
            
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                this.logMessage('✅ WebSocket connected');
                this.isConnected = true;
                this.elements.connectionStatus.textContent = 'Connected';
                resolve();
            };
            
            this.websocket.onmessage = (event) => {
                this.handleWebSocketMessage(event);
            };
            
            this.websocket.onclose = () => {
                this.logMessage('🔌 WebSocket disconnected');
                this.isConnected = false;
                this.elements.connectionStatus.textContent = 'Disconnected';
                this.updateStatus('disconnected', 'Disconnected');
            };
            
            this.websocket.onerror = (error) => {
                this.logMessage(`❌ WebSocket error: ${error}`);
                this.elements.connectionStatus.textContent = 'Error';
                reject(new Error('WebSocket connection failed'));
            };
        });
    }
    
    async initializeAudio() {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.mediaStream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true
                } 
            });
            
            const source = this.audioContext.createMediaStreamSource(this.mediaStream);
            this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);
            
            this.processor.onaudioprocess = (event) => {
                this.processAudioData(event);
            };
            
            source.connect(this.processor);
            this.processor.connect(this.audioContext.destination);
            
            this.logMessage('🎤 Audio initialized successfully');
            this.updateAudioStatus('🎤', 'Ready to listen');
            
        } catch (error) {
            this.logMessage(`❌ Audio initialization failed: ${error.message}`);
            throw error;
        }
    }
    
    processAudioData(event) {
        if (!this.isConnected || !this.websocket) return;
        
        const inputBuffer = event.inputBuffer;
        const inputData = inputBuffer.getChannelData(0);
        
        // Calculate audio level
        let sum = 0;
        for (let i = 0; i < inputData.length; i++) {
            sum += Math.abs(inputData[i]);
        }
        this.audioLevel = sum / inputData.length;
        this.updateAudioLevel();
        
        // Convert to Int16 PCM
        const pcmData = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
            pcmData[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
        }
        
        // Send audio data to Flow API
        this.sendAudioData(Array.from(pcmData));
    }
    
    sendAudioData(audioData) {
        if (!this.isConnected || !this.websocket) return;
        
        try {
            this.websocket.send(JSON.stringify({
                type: 'audio_data',
                data: audioData
            }));
        } catch (error) {
            this.logMessage(`❌ Failed to send audio data: ${error.message}`);
        }
    }
    
    sendTextMessage() {
        const text = this.elements.textInput.value.trim();
        if (!text || !this.isConnected) return;
        
        try {
            this.websocket.send(JSON.stringify({
                type: 'text_input',
                text: text,
                interrupt_response: this.elements.interruptResponse.checked,
                immediate: this.elements.immediateInput.checked
            }));
            
            this.addMessage('user', text);
            this.elements.textInput.value = '';
            this.logMessage(`📤 Sent text input: ${text}`);
            
        } catch (error) {
            this.logMessage(`❌ Failed to send text message: ${error.message}`);
        }
    }
    
    handleWebSocketMessage(event) {
        try {
            const data = JSON.parse(event.data);
            this.logMessage(`📨 Received: ${data.type}`);
            
            switch (data.type) {
                case 'flow_connected':
                    this.logMessage('✅ Flow API connected');
                    break;
                    
                case 'flow_session_started':
                    this.logMessage('✅ Flow session started');
                    break;
                    
                case 'transcript':
                    this.handleTranscript(data.data);
                    break;
                    
                case 'partial_transcript':
                    this.handlePartialTranscript(data.data);
                    break;
                    
                case 'agent_response':
                    this.handleAgentResponse(data.data);
                    break;
                    
                case 'tool_invoke':
                    this.handleToolInvoke(data.data);
                    break;
                    
                case 'flow_error':
                    this.handleFlowError(data.data);
                    break;
                    
                case 'conversation_ended':
                    this.logMessage('🔚 Conversation ended');
                    this.addMessage('system', 'Conversation ended');
                    break;
                    
                case 'error':
                    this.logMessage(`❌ Error: ${data.message}`);
                    this.addMessage('error', data.message);
                    break;
                    
                default:
                    this.logMessage(`⚠️ Unknown message type: ${data.type}`);
            }
            
        } catch (error) {
            this.logMessage(`❌ Failed to parse WebSocket message: ${error.message}`);
        }
    }
    
    handleTranscript(data) {
        const transcript = data.transcript;
        if (transcript) {
            this.addMessage('user', transcript);
            this.logMessage(`📝 Final transcript: ${transcript}`);
        }
    }
    
    handlePartialTranscript(data) {
        const transcript = data.transcript;
        if (transcript) {
            this.updateAudioStatus('🎤', `Live: ${transcript}`);
            this.logMessage(`📝 Partial transcript: ${transcript}`);
        }
    }
    
    handleAgentResponse(data) {
        const responseType = data.response_type;
        const content = data.content;
        
        switch (responseType) {
            case 'response_started':
                this.addMessage('agent', `🤖 Agent: ${content}`);
                this.logMessage(`🤖 Agent response started: ${content}`);
                break;
                
            case 'response_completed':
                this.logMessage(`✅ Agent response completed: ${content}`);
                break;
                
            case 'response_interrupted':
                this.logMessage(`⏹️ Agent response interrupted: ${content}`);
                break;
        }
    }
    
    handleToolInvoke(data) {
        const toolId = data.tool_id;
        const function = data.function;
        
        this.elements.toolPanel.style.display = 'block';
        this.elements.toolContent.innerHTML = `
            <div class="tool-execution">
                <h4>🔧 Tool Invoked: ${function.name}</h4>
                <p><strong>Description:</strong> ${function.description || 'No description'}</p>
                <p><strong>Parameters:</strong></p>
                <pre>${JSON.stringify(function.parameters || {}, null, 2)}</pre>
                <div class="tool-actions">
                    <button onclick="flowVoiceAI.executeTool('${toolId}', 'ok', 'Tool executed successfully')" 
                            class="btn btn-primary">✅ Execute</button>
                    <button onclick="flowVoiceAI.executeTool('${toolId}', 'rejected', 'Tool execution rejected')" 
                            class="btn btn-secondary">❌ Reject</button>
                    <button onclick="flowVoiceAI.executeTool('${toolId}', 'failed', 'Tool execution failed')" 
                            class="btn btn-outline">⚠️ Fail</button>
                </div>
            </div>
        `;
        
        this.logMessage(`🔧 Tool invoked: ${function.name} (ID: ${toolId})`);
    }
    
    executeTool(toolId, status, content) {
        if (!this.isConnected || !this.websocket) return;
        
        try {
            this.websocket.send(JSON.stringify({
                type: 'tool_result',
                tool_id: toolId,
                status: status,
                content: content
            }));
            
            this.logMessage(`🔧 Tool result sent: ${toolId} - ${status}`);
            this.elements.toolPanel.style.display = 'none';
            
        } catch (error) {
            this.logMessage(`❌ Failed to send tool result: ${error.message}`);
        }
    }
    
    handleFlowError(data) {
        const errorType = data.error_type;
        const reason = data.reason;
        
        this.logMessage(`❌ Flow API error: ${errorType} - ${reason}`);
        this.addMessage('error', `Flow API Error: ${reason}`);
    }
    
    async endFlowConversation() {
        try {
            if (this.websocket && this.isConnected) {
                this.websocket.send(JSON.stringify({
                    type: 'end_conversation'
                }));
            }
            
            await this.cleanup();
            this.logMessage('🔚 Flow conversation ended');
            
        } catch (error) {
            this.logMessage(`❌ Error ending conversation: ${error.message}`);
        }
    }
    
    async cleanup() {
        // Close WebSocket
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        
        // Stop audio
        if (this.processor) {
            this.processor.disconnect();
            this.processor = null;
        }
        
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }
        
        if (this.audioContext) {
            await this.audioContext.close();
            this.audioContext = null;
        }
        
        // Reset UI
        this.isConnected = false;
        this.isRecording = false;
        this.sessionId = null;
        
        this.elements.startFlowBtn.disabled = false;
        this.elements.endFlowBtn.disabled = true;
        this.elements.textInput.disabled = true;
        this.elements.sendTextBtn.disabled = true;
        
        this.elements.sessionInfo.style.display = 'none';
        this.elements.toolPanel.style.display = 'none';
        
        this.updateStatus('disconnected', 'Disconnected');
        this.updateAudioStatus('🎤', 'Ready to listen');
        this.elements.connectionStatus.textContent = 'Disconnected';
    }
    
    clearChat() {
        this.elements.chatMessages.innerHTML = `
            <div class="message system">
                <div class="message-content">
                    <strong>System:</strong> Chat cleared. Ready for new conversation.
                </div>
            </div>
        `;
        this.logMessage('🗑️ Chat cleared');
    }
    
    addMessage(type, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        const time = new Date().toLocaleTimeString();
        messageDiv.innerHTML = `
            <div class="message-content">${content}</div>
            <div class="message-time">${time}</div>
        `;
        
        this.elements.chatMessages.appendChild(messageDiv);
        this.elements.chatMessages.scrollTop = this.elements.chatMessages.scrollHeight;
        
        this.messageCount++;
    }
    
    updateStatus(status, text) {
        const statusDot = this.elements.statusIndicator.querySelector('.status-dot');
        statusDot.className = `status-dot ${status}`;
        this.elements.statusText.textContent = text;
    }
    
    updateAudioStatus(icon, text) {
        this.elements.audioIndicator.textContent = icon;
        this.elements.audioText.textContent = text;
    }
    
    updateAudioLevel() {
        const percentage = Math.min(100, this.audioLevel * 1000);
        this.elements.levelFill.style.width = `${percentage}%`;
    }
    
    startAudioLevelMonitoring() {
        setInterval(() => {
            if (!this.isConnected) {
                this.elements.levelFill.style.width = '0%';
            }
        }, 100);
    }
    
    logMessage(message) {
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = `[${timestamp}] ${message}`;
        
        console.log(logEntry);
        
        // Update debug panel
        if (this.elements.messageLog) {
            const logDiv = document.createElement('div');
            logDiv.textContent = logEntry;
            this.elements.messageLog.appendChild(logDiv);
            this.elements.messageLog.scrollTop = this.elements.messageLog.scrollHeight;
            
            // Keep only last 50 messages
            while (this.elements.messageLog.children.length > 50) {
                this.elements.messageLog.removeChild(this.elements.messageLog.firstChild);
            }
        }
        
        // Update session debug
        if (this.elements.sessionDebug) {
            this.elements.sessionDebug.innerHTML = `
                <div>Session ID: ${this.sessionId || 'None'}</div>
                <div>Connected: ${this.isConnected ? 'Yes' : 'No'}</div>
                <div>Recording: ${this.isRecording ? 'Yes' : 'No'}</div>
                <div>Messages: ${this.messageCount}</div>
                <div>Audio Level: ${(this.audioLevel * 100).toFixed(1)}%</div>
            `;
        }
    }
}

// Initialize the Flow Voice AI when the page loads
let flowVoiceAI;
document.addEventListener('DOMContentLoaded', () => {
    flowVoiceAI = new FlowVoiceAI();
});
