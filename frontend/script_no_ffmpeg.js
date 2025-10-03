/**
 * Real-time Voice Chatbot WITHOUT ffmpeg dependency
 * Uses browser's Web Audio API for audio processing
 */

class NoFFmpegVoiceChatbot {
    constructor() {
        this.mediaRecorder = null;
        this.audioStream = null;
        this.websocket = null;
        this.sessionId = null;
        this.isConversationActive = false;
        this.isUserSpeaking = false;
        this.isAISpeaking = false;
        this.silenceTimeout = null;
        this.currentTranscript = '';
        
        // Audio processing
        this.audioContext = null;
        this.analyser = null;
        this.processor = null;
        this.microphone = null;
        
        // VAD Configuration
        this.vadConfig = {
            silenceThreshold: 0.01,
            silenceDuration: 1500,
            speechThreshold: 0.02,
            minSpeechDuration: 500,
            maxSpeechDuration: 10000,
            chunkSize: 100
        };
        
        // UI elements
        this.recordButton = document.getElementById('recordButton');
        this.chatContainer = document.getElementById('chatContainer');
        this.statusDiv = document.getElementById('status');
        this.conversationStatus = document.getElementById('conversationStatus');
        
        this.initializeUI();
        this.connectWebSocket();
    }
    
    initializeUI() {
        if (this.recordButton) {
            this.recordButton.addEventListener('click', () => this.toggleConversation());
        }
        
        this.updateConversationStatus('Ready to start conversation');
        this.createVADVisualization();
    }
    
    createVADVisualization() {
        const vadContainer = document.createElement('div');
        vadContainer.id = 'vadContainer';
        vadContainer.innerHTML = `
            <div class="vad-section">
                <h4>🎤 Voice Activity Detection (No FFmpeg)</h4>
                <div class="vad-indicators">
                    <div class="vad-indicator" id="userSpeaking">
                        <span class="indicator-dot"></span>
                        <span>You Speaking</span>
                    </div>
                    <div class="vad-indicator" id="aiSpeaking">
                        <span class="indicator-dot"></span>
                        <span>AI Speaking</span>
                    </div>
                    <div class="vad-indicator" id="processing">
                        <span class="indicator-dot"></span>
                        <span>Processing</span>
                    </div>
                </div>
                <div class="audio-level">
                    <div class="audio-level-bar" id="audioLevelBar"></div>
                    <span id="audioLevelText">Audio Level: 0%</span>
                </div>
                <div class="tech-info">
                    <small>🚀 Using Web Audio API - No server-side conversion needed!</small>
                </div>
            </div>
        `;
        
        const infoPanel = document.querySelector('.info-panel');
        if (infoPanel) {
            infoPanel.appendChild(vadContainer);
        }
    }
    
    async connectWebSocket() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/chat/test-user`;
            
            console.log('Connecting to WebSocket:', wsUrl);
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('✅ WebSocket connected');
                this.updateStatus('Connected - Ready for conversation', 'success');
            };
            
            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            };
            
            this.websocket.onclose = () => {
                console.log('❌ WebSocket disconnected');
                this.updateStatus('Disconnected', 'error');
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateStatus('WebSocket error', 'error');
            };
            
        } catch (error) {
            console.error('Failed to connect:', error);
            this.updateStatus('Connection failed', 'error');
        }
    }
    
    handleWebSocketMessage(data) {
        console.log('📨 Received:', data);
        
        switch (data.type) {
            case 'session_started':
                this.sessionId = data.session_id;
                this.updateStatus(`Session started (${data.language})`, 'success');
                break;
                
            case 'transcript':
                this.handleUserTranscript(data.data);
                break;
                
            case 'partial_transcript':
                this.handlePartialTranscript(data.data);
                break;
                
            case 'ai_response':
                this.handleAIResponse(data.data);
                break;
                
            case 'error':
                const errorMessage = data.data ? data.data.message : data.message || 'Unknown error';
                this.updateStatus(`Error: ${errorMessage}`, 'error');
                break;
                
            case 'session_stopped':
                this.updateStatus('Session stopped', 'info');
                break;
        }
    }
    
    handleUserTranscript(transcriptData) {
        // This is a FINAL transcript from Speechmatics - send to AI for back-and-forth conversation
        const finalTranscript = transcriptData.transcript.trim();
        
        if (finalTranscript.length > 0) {
            // Replace live transcript with final transcript
            this.replaceLiveTranscriptWithFinal(finalTranscript);
            
            this.updateVADIndicator('userSpeaking', false);
            this.updateVADIndicator('processing', true);
            this.updateStatus('Processing...', 'info');
            
            this.sendToChatbot(finalTranscript);
        }
    }
    
    handlePartialTranscript(partialData) {
        // This is a PARTIAL transcript from Speechmatics - show live transcription
        const partialTranscript = partialData.transcript.trim();
        
        if (partialTranscript.length > 0) {
            this.currentTranscript = partialTranscript;
            this.updateStatus(`Live: ${partialTranscript}`, 'recording');
            
            // Update or create live transcript message in chat
            this.updateLiveTranscriptMessage(partialTranscript);
        }
    }
    
    async handleAIResponse(responseData) {
        this.updateVADIndicator('processing', false);
        this.updateVADIndicator('aiSpeaking', true);
        
        this.addMessage('assistant', responseData.content, 'ai');
        this.updateStatus('AI speaking...', 'ai-speaking');
        
        if (responseData.audio_url) {
            await this.playAIAudio(responseData.audio_url);
        }
        
        this.updateVADIndicator('aiSpeaking', false);
        this.updateStatus('Listening...', 'listening');
    }
    
    updateLiveTranscriptMessage(transcript) {
        // Find or create live transcript message
        let liveMessage = document.getElementById('live-transcript-message');
        
        if (!liveMessage) {
            // Create new live transcript message
            liveMessage = document.createElement('div');
            liveMessage.id = 'live-transcript-message';
            liveMessage.classList.add('message', 'user', 'live-transcript');
            liveMessage.innerHTML = `
                <div class="message-header">
                    <span class="message-icon">🎤</span>
                    <span class="message-sender">You (Live)</span>
                    <span class="message-time">Now</span>
                    <span class="message-status">🔴 Live</span>
                </div>
                <div class="message-content"></div>
            `;
            this.chatContainer.appendChild(liveMessage);
        }
        
        // Update the content
        const content = liveMessage.querySelector('.message-content');
        content.textContent = transcript;
        
        // Scroll to bottom
        this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
    }
    
    replaceLiveTranscriptWithFinal(finalTranscript) {
        // Find the live transcript message
        const liveMessage = document.getElementById('live-transcript-message');
        
        if (liveMessage) {
            // Update to final transcript
            liveMessage.classList.remove('live-transcript');
            liveMessage.classList.add('final-transcript');
            
            const header = liveMessage.querySelector('.message-header');
            const status = liveMessage.querySelector('.message-status');
            const content = liveMessage.querySelector('.message-content');
            
            // Update header and status
            header.innerHTML = `
                <span class="message-icon">👤</span>
                <span class="message-sender">You</span>
                <span class="message-time">${new Date().toLocaleTimeString()}</span>
                <span class="message-status">✓ Final</span>
            `;
            
            // Update content
            content.textContent = finalTranscript;
            
            // Remove the ID so it becomes a regular message
            liveMessage.removeAttribute('id');
        } else {
            // If no live message found, create a new final message
            this.addMessage('user', finalTranscript, 'final');
        }
    }
    
    async toggleConversation() {
        if (this.isConversationActive) {
            await this.endConversation();
        } else {
            await this.startConversation();
        }
    }
    
    async startConversation() {
        try {
            if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
                this.updateStatus('WebSocket not connected', 'error');
                return;
            }
            
            // Get microphone access
            this.audioStream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                } 
            });
            
            // Set up Web Audio API for direct PCM processing
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 16000
            });
            
            this.analyser = this.audioContext.createAnalyser();
            this.microphone = this.audioContext.createMediaStreamSource(this.audioStream);
            
            // Create a ScriptProcessorNode for real-time audio processing
            this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);
            
            // Connect audio nodes
            this.microphone.connect(this.analyser);
            this.analyser.connect(this.processor);
            this.processor.connect(this.audioContext.destination);
            
            // Set up analyser for VAD
            this.analyser.fftSize = 256;
            this.bufferLength = this.analyser.frequencyBinCount;
            this.dataArray = new Uint8Array(this.bufferLength);
            
            // Process audio data in real-time
            this.processor.onaudioprocess = (event) => {
                if (this.isUserSpeaking) {
                    const inputBuffer = event.inputBuffer;
                    const inputData = inputBuffer.getChannelData(0);
                    
                    // Convert float32 to int16 PCM
                    const pcmData = this.float32ToInt16(inputData);
                    
                    // Send PCM data directly to WebSocket
                    this.sendPCMChunk(pcmData);
                }
            };
            
            // Start VAD monitoring
            this.startVADMonitoring();
            
            this.isConversationActive = true;
            this.isUserSpeaking = false;
            
            this.recordButton.textContent = '🛑 End Conversation';
            this.recordButton.style.backgroundColor = '#f44336';
            this.updateConversationStatus('Conversation Active - Speak naturally');
            this.updateStatus('Listening for your voice...', 'listening');
            
            this.addMessage('assistant', 'Hello! I\'m ready for our conversation. Just start speaking naturally - I\'ll detect when you\'re talking and respond automatically.', 'system');
            
        } catch (error) {
            console.error('Error starting conversation:', error);
            this.updateStatus('Failed to start conversation', 'error');
        }
    }
    
    async endConversation() {
        try {
            this.stopVADMonitoring();
            
            if (this.processor) {
                this.processor.disconnect();
            }
            
            if (this.audioStream) {
                this.audioStream.getTracks().forEach(track => track.stop());
            }
            
            if (this.audioContext) {
                await this.audioContext.close();
            }
            
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send(JSON.stringify({
                    type: 'stop_recording'
                }));
            }
            
            this.isConversationActive = false;
            this.isUserSpeaking = false;
            this.isAISpeaking = false;
            
            this.recordButton.textContent = '🎤 Start Conversation';
            this.recordButton.style.backgroundColor = '#4CAF50';
            this.updateConversationStatus('Conversation Ended');
            this.updateStatus('Conversation ended', 'info');
            
            this.updateVADIndicator('userSpeaking', false);
            this.updateVADIndicator('aiSpeaking', false);
            this.updateVADIndicator('processing', false);
            
        } catch (error) {
            console.error('Error ending conversation:', error);
        }
    }
    
    float32ToInt16(float32Array) {
        const int16Array = new Int16Array(float32Array.length);
        for (let i = 0; i < float32Array.length; i++) {
            // Convert from [-1, 1] to [-32768, 32767]
            const sample = Math.max(-1, Math.min(1, float32Array[i]));
            int16Array[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
        }
        return int16Array;
    }
    
    async sendPCMChunk(pcmData) {
        try {
            if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
                return;
            }
            
            // Send raw PCM data directly
            this.websocket.send(JSON.stringify({
                type: 'pcm_audio',
                audio_data: Array.from(pcmData) // Convert to regular array for JSON
            }));
            
        } catch (error) {
            console.error('Error sending PCM chunk:', error);
        }
    }
    
    startVADMonitoring() {
        this.vadInterval = setInterval(() => {
            this.analyser.getByteFrequencyData(this.dataArray);
            
            let sum = 0;
            for (let i = 0; i < this.bufferLength; i++) {
                sum += this.dataArray[i];
            }
            const average = sum / this.bufferLength;
            const volume = average / 255;
            
            this.updateAudioLevel(volume);
            
            if (volume > this.vadConfig.speechThreshold) {
                if (!this.isUserSpeaking && !this.isAISpeaking) {
                    this.startUserSpeech();
                }
                this.clearSilenceTimeout();
            } else {
                if (this.isUserSpeaking && !this.silenceTimeout) {
                    this.silenceTimeout = setTimeout(() => {
                        this.endUserSpeech();
                    }, this.vadConfig.silenceDuration);
                }
            }
        }, 50);
    }
    
    stopVADMonitoring() {
        if (this.vadInterval) {
            clearInterval(this.vadInterval);
        }
        this.clearSilenceTimeout();
    }
    
    clearSilenceTimeout() {
        if (this.silenceTimeout) {
            clearTimeout(this.silenceTimeout);
            this.silenceTimeout = null;
        }
    }
    
    startUserSpeech() {
        console.log('🎤 User started speaking');
        this.isUserSpeaking = true;
        this.updateVADIndicator('userSpeaking', true);
        this.updateStatus('You are speaking...', 'recording');
        this.currentTranscript = '';
    }
    
    endUserSpeech() {
        console.log('🔇 User stopped speaking');
        this.isUserSpeaking = false;
        this.updateVADIndicator('userSpeaking', false);
        
        // Speechmatics will handle final transcripts automatically
        // We just need to wait for the final transcript to come through
        this.updateStatus('Listening for your voice...', 'listening');
    }
    
    async sendFinalTranscript(transcript) {
        try {
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send(JSON.stringify({
                    type: 'final_transcript',
                    transcript: transcript
                }));
            }
        } catch (error) {
            console.error('Error sending final transcript:', error);
        }
    }
    
    async sendToChatbot(transcript) {
        try {
            this.updateVADIndicator('processing', true);
            this.updateStatus('Getting AI response...', 'processing');
            
            const response = await fetch('/api/v1/chat/message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: transcript,
                    user_id: 'test-user'
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            console.log('🤖 AI Response:', result);
            
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send(JSON.stringify({
                    type: 'ai_response',
                    content: result.content,
                    audio_url: result.audio_url
                }));
            }
            
        } catch (error) {
            console.error('Error sending message to chatbot:', error);
            this.updateStatus('Failed to get AI response', 'error');
            this.updateVADIndicator('processing', false);
        }
    }
    
    async playAIAudio(audioUrl) {
        try {
            const audio = new Audio(audioUrl);
            this.isAISpeaking = true;
            
            audio.onended = () => {
                this.isAISpeaking = false;
                this.updateVADIndicator('aiSpeaking', false);
                this.updateStatus('Listening for your response...', 'listening');
            };
            
            await audio.play();
            
        } catch (error) {
            console.error('Error playing AI audio:', error);
            this.isAISpeaking = false;
            this.updateVADIndicator('aiSpeaking', false);
        }
    }
    
    addMessage(sender, content, type = 'normal') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const icon = sender === 'user' ? '👤' : '🤖';
        const timestamp = new Date().toLocaleTimeString();
        
        let typeIndicator = '';
        if (type === 'final') {
            typeIndicator = ' <span style="color: #4CAF50; font-size: 0.8em;">✓ Final</span>';
        } else if (type === 'ai') {
            typeIndicator = ' <span style="color: #2196F3; font-size: 0.8em;">🤖 AI</span>';
        } else if (type === 'system') {
            typeIndicator = ' <span style="color: #FF9800; font-size: 0.8em;">ℹ️ System</span>';
        }
        
        messageDiv.innerHTML = `
            <div class="message-header">
                <span class="message-icon">${icon}</span>
                <span class="message-sender">${sender === 'user' ? 'You' : 'AI Assistant'}</span>
                <span class="message-time">${timestamp}</span>
                ${typeIndicator}
            </div>
            <div class="message-content">${content}</div>
        `;
        
        this.chatContainer.appendChild(messageDiv);
        this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
    }
    
    updateStatus(message, type = 'info') {
        if (this.statusDiv) {
            this.statusDiv.textContent = message;
            this.statusDiv.className = `status ${type}`;
        }
        console.log(`📊 Status [${type}]: ${message}`);
    }
    
    updateConversationStatus(message) {
        if (this.conversationStatus) {
            this.conversationStatus.textContent = message;
        }
    }
    
    updateVADIndicator(indicatorId, active) {
        const indicator = document.getElementById(indicatorId);
        if (indicator) {
            const dot = indicator.querySelector('.indicator-dot');
            if (active) {
                indicator.classList.add('active');
                if (dot) dot.style.backgroundColor = '#4CAF50';
            } else {
                indicator.classList.remove('active');
                if (dot) dot.style.backgroundColor = '#ccc';
            }
        }
    }
    
    updateAudioLevel(volume) {
        const levelBar = document.getElementById('audioLevelBar');
        const levelText = document.getElementById('audioLevelText');
        
        if (levelBar) {
            levelBar.style.width = `${volume * 100}%`;
        }
        
        if (levelText) {
            levelText.textContent = `Audio Level: ${Math.round(volume * 100)}%`;
        }
    }
}

// Initialize the no-ffmpeg chatbot when the page loads
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Initializing No-FFmpeg Voice Chatbot...');
    window.noFFmpegChatbot = new NoFFmpegVoiceChatbot();
});
