"""
AI Chatbot service with fallback hierarchy: Kong API -> Ollama -> OpenAI.
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
import httpx
import openai
from openai import AsyncOpenAI

from ..core.config import settings

logger = logging.getLogger(__name__)


class AIChatbotService:
    """AI Chatbot service with fallback hierarchy."""
    
    def __init__(self):
        self.fallback_order = settings.ai_fallback_order_list
        self.max_response_length = settings.ai_response_max_length
        self.response_timeout = settings.ai_response_timeout / 1000  # Convert to seconds
        
        # Initialize OpenAI client if API key is provided
        self.openai_client = None
        if settings.openai_api_key:
            self.openai_client = AsyncOpenAI(
                api_key=settings.openai_api_key,
                organization=settings.openai_organization
            )
        
        # HTTP client for Kong and Ollama
        self.http_client = httpx.AsyncClient(timeout=self.response_timeout)
    
    async def generate_response(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        language: str = "en",
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate AI response using fallback hierarchy.
        
        Args:
            message: User's message
            conversation_history: Previous conversation messages
            language: Language for the response
            user_id: User ID for personalization
            
        Returns:
            Dict containing response, provider used, and metadata
        """
        conversation_history = conversation_history or []
        
        # Try each provider in fallback order
        for provider in self.fallback_order:
            try:
                logger.info(f"Attempting to generate response using {provider}")
                
                if provider == "kong":
                    response = await self._generate_kong_response(
                        message, conversation_history, language, user_id
                    )
                elif provider == "ollama":
                    response = await self._generate_ollama_response(
                        message, conversation_history, language, user_id
                    )
                elif provider == "openai":
                    response = await self._generate_openai_response(
                        message, conversation_history, language, user_id
                    )
                else:
                    logger.warning(f"Unknown provider: {provider}")
                    continue
                
                if response and response.get("content"):
                    logger.info(f"Successfully generated response using {provider}")
                    return {
                        "content": response["content"],
                        "provider": provider,
                        "model": response.get("model", "unknown"),
                        "response_time_ms": response.get("response_time_ms", 0),
                        "tokens_used": response.get("tokens_used", 0),
                        "metadata": response.get("metadata", {})
                    }
                
            except Exception as e:
                logger.error(f"Error with {provider}: {e}")
                continue
        
        # If all providers fail, return a fallback response
        logger.error("All AI providers failed, returning fallback response")
        return {
            "content": "I apologize, but I'm currently unable to process your request. Please check your API configuration and try again later.",
            "provider": "fallback",
            "model": "none",
            "response_time_ms": 0,
            "tokens_used": 0,
            "metadata": {"error": "All providers failed - check API keys and service availability"}
        }
    
    async def _generate_kong_response(
        self,
        message: str,
        conversation_history: List[Dict[str, str]],
        language: str,
        user_id: Optional[int]
    ) -> Dict[str, Any]:
        """Generate response using Kong API Gateway (Local LLM)."""
        try:
            # Prepare messages for Kong API
            messages = self._prepare_messages(message, conversation_history, language)
            
            # Prepare request payload
            payload = {
                "model": settings.kong_default_model,
                "messages": messages,
                "max_tokens": settings.ollama_max_tokens,
                "temperature": settings.ollama_temperature,
                "stream": False
            }
            
            # Add user context if available
            if user_id:
                payload["user"] = str(user_id)
            
            # Make request to Kong API
            headers = {"Content-Type": "application/json"}
            if settings.kong_api_key:
                headers["Authorization"] = f"Bearer {settings.kong_api_key}"
            
            start_time = asyncio.get_event_loop().time()
            
            response = await self.http_client.post(
                f"{settings.kong_api_url}{settings.kong_model_endpoint}",
                json=payload,
                headers=headers
            )
            
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
            response.raise_for_status()
            
            result = response.json()
            
            return {
                "content": result["choices"][0]["message"]["content"],
                "model": result.get("model", settings.kong_default_model),
                "response_time_ms": int(response_time),
                "tokens_used": result.get("usage", {}).get("total_tokens", 0),
                "metadata": {
                    "provider": "kong",
                    "api_url": settings.kong_api_url
                }
            }
            
        except Exception as e:
            logger.error(f"Kong API error: {e}")
            raise
    
    async def _generate_ollama_response(
        self,
        message: str,
        conversation_history: List[Dict[str, str]],
        language: str,
        user_id: Optional[int]
    ) -> Dict[str, Any]:
        """Generate response using local Ollama."""
        try:
            # Prepare messages for Ollama
            messages = self._prepare_messages(message, conversation_history, language)
            
            # Prepare request payload
            payload = {
                "model": settings.ollama_default_model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": settings.ollama_temperature,
                    "num_predict": settings.ollama_max_tokens
                }
            }
            
            start_time = asyncio.get_event_loop().time()
            
            response = await self.http_client.post(
                f"{settings.ollama_base_url}/api/generate",
                json=payload
            )
            
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
            response.raise_for_status()
            
            result = response.json()
            
            return {
                "content": result["response"],
                "model": result.get("model", settings.ollama_default_model),
                "response_time_ms": int(response_time),
                "tokens_used": result.get("eval_count", 0),
                "metadata": {
                    "provider": "ollama",
                    "base_url": settings.ollama_base_url
                }
            }
            
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            raise
    
    async def _generate_openai_response(
        self,
        message: str,
        conversation_history: List[Dict[str, str]],
        language: str,
        user_id: Optional[int]
    ) -> Dict[str, Any]:
        """Generate response using OpenAI."""
        if not self.openai_client:
            raise RuntimeError("OpenAI client not initialized")
        
        try:
            # Prepare messages for OpenAI
            messages = self._prepare_messages(message, conversation_history, language)
            
            start_time = asyncio.get_event_loop().time()
            
            response = await self.openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                max_tokens=settings.openai_max_tokens,
                temperature=settings.openai_temperature,
                top_p=settings.openai_top_p,
                frequency_penalty=settings.openai_frequency_penalty,
                presence_penalty=settings.openai_presence_penalty,
                user=str(user_id) if user_id else None
            )
            
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            return {
                "content": response.choices[0].message.content,
                "model": response.model,
                "response_time_ms": int(response_time),
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "metadata": {
                    "provider": "openai",
                    "finish_reason": response.choices[0].finish_reason
                }
            }
            
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            raise
    
    def _prepare_messages(
        self,
        message: str,
        conversation_history: List[Dict[str, str]],
        language: str
    ) -> List[Dict[str, str]]:
        """Prepare messages for AI providers."""
        messages = []
        
        # Add system message with language context
        system_message = self._get_system_message(language)
        messages.append({"role": "system", "content": system_message})
        
        # Add conversation history
        for msg in conversation_history[-10:]:  # Limit to last 10 messages
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        return messages
    
    def _get_system_message(self, language: str) -> str:
        """Get system message based on language."""
        system_messages = {
            "en": "You are a helpful, friendly, and knowledgeable AI assistant. You can help with various tasks and answer questions. Keep your responses concise and helpful.",
            "es": "Eres un asistente de IA útil, amigable y conocedor. Puedes ayudar con varias tareas y responder preguntas. Mantén tus respuestas concisas y útiles.",
            "fr": "Vous êtes un assistant IA utile, amical et compétent. Vous pouvez aider avec diverses tâches et répondre aux questions. Gardez vos réponses concises et utiles.",
            "de": "Sie sind ein hilfreicher, freundlicher und sachkundiger KI-Assistent. Sie können bei verschiedenen Aufgaben helfen und Fragen beantworten. Halten Sie Ihre Antworten prägnant und hilfreich.",
            "it": "Sei un assistente AI utile, amichevole e competente. Puoi aiutare con varie attività e rispondere alle domande. Mantieni le tue risposte concise e utili.",
            "pt": "Você é um assistente de IA útil, amigável e conhecedor. Você pode ajudar com várias tarefas e responder perguntas. Mantenha suas respostas concisas e úteis.",
            "ru": "Вы полезный, дружелюбный и знающий ИИ-помощник. Вы можете помочь с различными задачами и ответить на вопросы. Держите свои ответы краткими и полезными.",
            "ja": "あなたは親切で、友好的で、知識豊富なAIアシスタントです。様々なタスクを手伝い、質問に答えることができます。回答は簡潔で有用なものにしてください。",
            "ko": "당신은 도움이 되고, 친근하며, 지식이 풍부한 AI 어시스턴트입니다. 다양한 작업을 도와주고 질문에 답할 수 있습니다. 답변을 간결하고 유용하게 유지하세요.",
            "zh": "你是一个有用、友好、知识渊博的AI助手。你可以帮助处理各种任务并回答问题。保持你的回答简洁有用。"
        }
        
        return system_messages.get(language, system_messages["en"])
    
    async def get_available_models(self) -> Dict[str, List[str]]:
        """Get available models from each provider."""
        models = {}
        
        # Kong models (if available)
        try:
            if settings.kong_api_key:
                response = await self.http_client.get(
                    f"{settings.kong_api_url}/v1/models",
                    headers={"Authorization": f"Bearer {settings.kong_api_key}"}
                )
                if response.status_code == 200:
                    result = response.json()
                    models["kong"] = [model["id"] for model in result.get("data", [])]
        except Exception as e:
            logger.warning(f"Could not fetch Kong models: {e}")
        
        # Ollama models
        try:
            response = await self.http_client.get(f"{settings.ollama_base_url}/api/tags")
            if response.status_code == 200:
                result = response.json()
                models["ollama"] = [model["name"] for model in result.get("models", [])]
        except Exception as e:
            logger.warning(f"Could not fetch Ollama models: {e}")
        
        # OpenAI models
        if self.openai_client:
            try:
                response = await self.openai_client.models.list()
                models["openai"] = [model.id for model in response.data if "gpt" in model.id]
            except Exception as e:
                logger.warning(f"Could not fetch OpenAI models: {e}")
        
        return models
    
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()


# Global instance
ai_chatbot_service = AIChatbotService()
