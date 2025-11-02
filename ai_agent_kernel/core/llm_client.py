import json
import asyncio
from typing import Optional, Dict, Any, List
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
import groq
import httpx
from config.settings import settings
from config.logger import logger


class BaseLLMHandler:
    """Base class for LLM API handlers"""
    
    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        raise NotImplementedError
        
    async def count_tokens(self, text: str) -> int:
        """Approximate token count"""
        return len(text.split()) * 1.3  # Rough approximation


class OpenAIHandler(BaseLLMHandler):
    """Handler for OpenAI-compatible APIs"""
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        
    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        try:
            response = await self.client.chat.completions.create(
                model=kwargs.get("model"),
                messages=messages,
                max_tokens=kwargs.get("max_tokens", settings.max_tokens),
                temperature=kwargs.get("temperature", settings.temperature),
                stream=kwargs.get("stream", False)
            )
            
            if kwargs.get("stream", False):
                return response
            else:
                return {
                    "content": response.choices[0].message.content,
                    "tokens_used": response.usage.total_tokens if response.usage else 0,
                    "model": response.model
                }
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise


class AnthropicHandler(BaseLLMHandler):
    """Handler for Anthropic Claude API"""
    
    def __init__(self, api_key: str):
        self.client = AsyncAnthropic(api_key=api_key)
        
    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        try:
            # Convert OpenAI format to Anthropic format
            system_message = ""
            user_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    user_messages.append({"role": msg["role"], "content": msg["content"]})
            
            response = await self.client.messages.create(
                model=kwargs.get("model"),
                max_tokens=kwargs.get("max_tokens", settings.max_tokens),
                temperature=kwargs.get("temperature", settings.temperature),
                system=system_message,
                messages=user_messages
            )
            
            return {
                "content": response.content[0].text,
                "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
                "model": response.model
            }
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise


class GroqHandler(BaseLLMHandler):
    """Handler for Groq API"""
    
    def __init__(self, api_key: str):
        self.client = groq.AsyncGroq(api_key=api_key)
        
    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        try:
            response = await self.client.chat.completions.create(
                model=kwargs.get("model"),
                messages=messages,
                max_tokens=kwargs.get("max_tokens", settings.max_tokens),
                temperature=kwargs.get("temperature", settings.temperature),
                stream=kwargs.get("stream", False)
            )
            
            if kwargs.get("stream", False):
                return response
            else:
                return {
                    "content": response.choices[0].message.content,
                    "tokens_used": response.usage.total_tokens if response.usage else 0,
                    "model": response.model
                }
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise


class LLMClient:
    """Dynamic LLM client that supports multiple providers"""
    
    def __init__(self):
        self.handlers = {}
        self._initialize_handlers()
        
    def _initialize_handlers(self):
        """Initialize handlers for each API provider"""
        
        # OpenAI Handler
        if settings.openai_api_key:
            self.handlers["openai"] = OpenAIHandler(settings.openai_api_key)
            
        # Anthropic Handler
        if settings.anthropic_api_key:
            self.handlers["anthropic"] = AnthropicHandler(settings.anthropic_api_key)
            
        # Groq Handler (OpenAI-compatible)
        if settings.groq_api_key:
            self.handlers["groq"] = GroqHandler(settings.groq_api_key)
            
        logger.info(f"Initialized LLM handlers for: {list(self.handlers.keys())}")
    
    def get_handler(self, api_standard: str) -> Optional[BaseLLMHandler]:
        """Get handler for specific API standard"""
        return self.handlers.get(api_standard)
    
    async def call_model(self, model_config: Dict[str, Any], messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Call model with configuration from database"""
        handler = self.get_handler(model_config["api_standard"])
        
        if not handler:
            raise ValueError(f"No handler available for API standard: {model_config['api_standard']}")
        
        # Override defaults with model config
        final_kwargs = {
            "model": model_config["name"],
            "max_tokens": model_config.get("max_tokens", settings.max_tokens),
            "temperature": float(model_config.get("temperature", settings.temperature)),
            **kwargs
        }
        
        return await handler.generate(messages, **final_kwargs)
    
    async def stream_model(self, model_config: Dict[str, Any], messages: List[Dict[str, str]], **kwargs):
        """Stream response from model"""
        handler = self.get_handler(model_config["api_standard"])
        
        if not handler:
            raise ValueError(f"No handler available for API standard: {model_config['api_standard']}")
        
        final_kwargs = {
            "model": model_config["name"],
            "max_tokens": model_config.get("max_tokens", settings.max_tokens),
            "temperature": float(model_config.get("temperature", settings.temperature)),
            "stream": True,
            **kwargs
        }
        
        return await handler.generate(messages, **final_kwargs)


# Global LLM client instance
llm_client = LLMClient()