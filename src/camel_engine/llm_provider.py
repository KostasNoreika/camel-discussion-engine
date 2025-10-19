"""
OpenRouter LLM Provider
Unified access to multiple LLMs through OpenRouter API
"""
import httpx
from typing import Dict, List, Optional
from loguru import logger


class OpenRouterClient:
    """
    Client for OpenRouter API to access multiple LLMs

    Supports:
    - OpenAI models (GPT-4, GPT-4 Turbo)
    - Anthropic models (Claude 3 Opus, Sonnet)
    - Google models (Gemini Pro, Ultra)
    - Mistral models
    """

    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.http_referer = "https://chat.noreika.lt"
        self.app_name = "CAMEL Discussion Engine"

    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Call LLM through OpenRouter

        Args:
            model: Model identifier (e.g., "openai/gpt-4", "anthropic/claude-3-opus")
            messages: List of message dicts with "role" and "content"
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters for the API

        Returns:
            Generated text content

        Raises:
            httpx.HTTPError: If API request fails
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "HTTP-Referer": self.http_referer,
                        "X-Title": self.app_name,
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        **({"max_tokens": max_tokens} if max_tokens else {}),
                        **kwargs
                    }
                )

                response.raise_for_status()
                result = response.json()

                # Log usage stats
                if "usage" in result:
                    usage = result["usage"]
                    logger.debug(
                        f"LLM call: {model} | "
                        f"Tokens: {usage.get('total_tokens', 0)} | "
                        f"Cost: ${usage.get('total_cost', 0):.4f}"
                    )

                content = result["choices"][0]["message"]["content"]

                # Warn if empty response
                if not content or not content.strip():
                    logger.warning(
                        f"EMPTY RESPONSE from {model} | "
                        f"Messages: {len(messages)} | "
                        f"Full response: {result}"
                    )

                return content

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter API error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"OpenRouter request error: {str(e)}")
            raise
        except KeyError as e:
            logger.error(f"Unexpected API response format: {e}")
            raise

    async def chat_completion_structured(
        self,
        model: str,
        messages: List[Dict[str, str]],
        response_format: Dict = {"type": "json_object"},
        **kwargs
    ) -> Dict:
        """
        Call LLM with structured JSON output

        Args:
            model: Model identifier
            messages: Message history
            response_format: Desired response format
            **kwargs: Additional parameters

        Returns:
            Parsed JSON response as dict
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "HTTP-Referer": self.http_referer,
                        "X-Title": self.app_name,
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "response_format": response_format,
                        **kwargs
                    }
                )

                response.raise_for_status()
                result = response.json()

                content = result["choices"][0]["message"]["content"]

                # Parse JSON response
                import json
                return json.loads(content)

        except (httpx.HTTPError, json.JSONDecodeError) as e:
            logger.error(f"Structured completion error: {str(e)}")
            raise

    async def get_available_models(self) -> List[Dict]:
        """
        Get list of available models from OpenRouter

        Returns:
            List of model information dicts
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "HTTP-Referer": self.http_referer
                    }
                )

                response.raise_for_status()
                data = response.json()

                return data.get("data", [])

        except httpx.HTTPError as e:
            logger.error(f"Error fetching models: {str(e)}")
            return []

    def normalize_model_name(self, model_preference: str) -> str:
        """
        Normalize common model names to OpenRouter format

        Args:
            model_preference: User-friendly model name

        Returns:
            OpenRouter-compatible model identifier
        """
        # Latest 2025 model mappings (user-friendly names → OpenRouter IDs)
        model_mapping = {
            # OpenAI (latest 2025)
            # IMPORTANT: gpt-5 = o1-preview (reasoning mode, empty output)
            # Use gpt-5-chat for normal chat completions
            "gpt-4": "openai/gpt-5-chat",
            "gpt-4o": "openai/gpt-5-chat",
            "gpt-4-turbo": "openai/gpt-5-chat",
            "gpt-5": "openai/gpt-5-chat",
            "gpt-5-chat": "openai/gpt-5-chat",

            # Anthropic (latest 2025)
            "claude-3-opus": "anthropic/claude-sonnet-4.5",
            "claude-3-sonnet": "anthropic/claude-sonnet-4.5",
            "claude-3.5-sonnet": "anthropic/claude-sonnet-4.5",
            "claude-4.5": "anthropic/claude-sonnet-4.5",
            "claude-sonnet-4.5": "anthropic/claude-sonnet-4.5",

            # Google (latest 2025)
            "gemini-pro": "google/gemini-2.5-pro",
            "gemini-1.5-pro": "google/gemini-2.5-pro",
            "gemini-2.5-pro": "google/gemini-2.5-pro",
            "gemini-ultra": "google/gemini-2.5-pro",

            # DeepSeek (latest 2025)
            "deepseek": "deepseek/deepseek-v3.2-exp",
            "deepseek-chat": "deepseek/deepseek-v3.2-exp",
            "deepseek-v3.2": "deepseek/deepseek-v3.2-exp",

            # Others
            "mistral-large": "mistralai/mistral-large",
        }

        return model_mapping.get(model_preference.lower(), model_preference)


class LLMProviderFactory:
    """Factory for creating LLM provider instances"""

    @staticmethod
    def create_openrouter_client(api_key: str) -> OpenRouterClient:
        """Create OpenRouter client instance"""
        if not api_key:
            raise ValueError("OpenRouter API key is required")
        return OpenRouterClient(api_key=api_key)
