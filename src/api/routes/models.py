"""
Models API Routes
Handles model-related endpoints (listing available LLMs, model info)
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel
from loguru import logger

from ...camel_engine.llm_provider import OpenRouterClient
from ...utils.config import settings


router = APIRouter()
llm_client = OpenRouterClient(api_key=settings.OPENROUTER_API_KEY)


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class ModelInfo(BaseModel):
    """LLM model information"""
    id: str
    name: str
    provider: str
    context_length: int
    pricing: Dict[str, Any]
    capabilities: List[str]


class ModelsListResponse(BaseModel):
    """Response for listing models"""
    models: List[ModelInfo]
    count: int


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get("/", response_model=ModelsListResponse)
async def list_models():
    """
    List all available LLM models

    Returns a list of models available through OpenRouter, including:
    - Model ID and name
    - Provider (OpenAI, Anthropic, Google, etc.)
    - Context length
    - Pricing information
    - Capabilities

    This helps users choose appropriate models for their discussions.
    """
    try:
        logger.info("Fetching available models")

        # Predefined list of supported models
        # In production, this could be fetched from OpenRouter API
        models = [
            ModelInfo(
                id="openai/gpt-4",
                name="GPT-4",
                provider="OpenAI",
                context_length=8192,
                pricing={"prompt": "0.03", "completion": "0.06"},
                capabilities=["chat", "reasoning", "structured_output"]
            ),
            ModelInfo(
                id="openai/gpt-4-turbo",
                name="GPT-4 Turbo",
                provider="OpenAI",
                context_length=128000,
                pricing={"prompt": "0.01", "completion": "0.03"},
                capabilities=["chat", "reasoning", "structured_output", "vision"]
            ),
            ModelInfo(
                id="openai/gpt-3.5-turbo",
                name="GPT-3.5 Turbo",
                provider="OpenAI",
                context_length=16385,
                pricing={"prompt": "0.0005", "completion": "0.0015"},
                capabilities=["chat", "reasoning", "fast"]
            ),
            ModelInfo(
                id="anthropic/claude-3-opus",
                name="Claude 3 Opus",
                provider="Anthropic",
                context_length=200000,
                pricing={"prompt": "0.015", "completion": "0.075"},
                capabilities=["chat", "reasoning", "structured_output", "long_context"]
            ),
            ModelInfo(
                id="anthropic/claude-3-sonnet",
                name="Claude 3 Sonnet",
                provider="Anthropic",
                context_length=200000,
                pricing={"prompt": "0.003", "completion": "0.015"},
                capabilities=["chat", "reasoning", "structured_output", "long_context"]
            ),
            ModelInfo(
                id="anthropic/claude-3-haiku",
                name="Claude 3 Haiku",
                provider="Anthropic",
                context_length=200000,
                pricing={"prompt": "0.00025", "completion": "0.00125"},
                capabilities=["chat", "reasoning", "fast"]
            ),
            ModelInfo(
                id="google/gemini-pro-1.5",
                name="Gemini 1.5 Pro",
                provider="Google",
                context_length=1000000,
                pricing={"prompt": "0.0025", "completion": "0.0075"},
                capabilities=["chat", "reasoning", "vision", "long_context"]
            ),
            ModelInfo(
                id="google/gemini-flash-1.5",
                name="Gemini 1.5 Flash",
                provider="Google",
                context_length=1000000,
                pricing={"prompt": "0.000075", "completion": "0.0003"},
                capabilities=["chat", "reasoning", "fast", "long_context"]
            ),
            ModelInfo(
                id="meta-llama/llama-3-70b-instruct",
                name="Llama 3 70B Instruct",
                provider="Meta",
                context_length=8192,
                pricing={"prompt": "0.00059", "completion": "0.00079"},
                capabilities=["chat", "reasoning", "open_source"]
            ),
            ModelInfo(
                id="mistralai/mistral-large",
                name="Mistral Large",
                provider="Mistral AI",
                context_length=32000,
                pricing={"prompt": "0.004", "completion": "0.012"},
                capabilities=["chat", "reasoning", "multilingual"]
            )
        ]

        logger.info(f"Returning {len(models)} available models")
        return ModelsListResponse(
            models=models,
            count=len(models)
        )

    except Exception as e:
        logger.error(f"Failed to list models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")


@router.get("/{model_id}", response_model=ModelInfo)
async def get_model_info(model_id: str):
    """
    Get detailed information about a specific model

    Path Parameters:
    - model_id: Model identifier (e.g., "openai/gpt-4")

    Returns detailed model information including pricing and capabilities.
    """
    try:
        logger.info(f"Getting info for model: {model_id}")

        # Get all models and find the requested one
        models_response = await list_models()
        model = next((m for m in models_response.models if m.id == model_id), None)

        if not model:
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

        return model

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get model info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/normalize/{model_preference}")
async def normalize_model_name(model_preference: str):
    """
    Normalize model preference to OpenRouter format

    Path Parameters:
    - model_preference: User-friendly model name (e.g., "gpt-4", "claude-opus")

    Returns:
    - Normalized OpenRouter model ID (e.g., "openai/gpt-4")

    This endpoint helps convert user-friendly model names to the format
    required by OpenRouter API.
    """
    try:
        logger.info(f"Normalizing model name: {model_preference}")

        normalized = llm_client.normalize_model_name(model_preference)

        return {
            "input": model_preference,
            "normalized": normalized,
            "valid": True
        }

    except Exception as e:
        logger.error(f"Failed to normalize model name: {e}", exc_info=True)
        return {
            "input": model_preference,
            "normalized": model_preference,
            "valid": False,
            "error": str(e)
        }


@router.get("/providers/list")
async def list_providers():
    """
    List all available LLM providers

    Returns a list of providers with their available models.
    Useful for filtering models by provider.
    """
    try:
        logger.info("Listing providers")

        # Get all models
        models_response = await list_models()

        # Group by provider
        providers = {}
        for model in models_response.models:
            if model.provider not in providers:
                providers[model.provider] = {
                    "name": model.provider,
                    "models": [],
                    "count": 0
                }

            providers[model.provider]["models"].append({
                "id": model.id,
                "name": model.name
            })
            providers[model.provider]["count"] += 1

        return {
            "providers": list(providers.values()),
            "total_providers": len(providers)
        }

    except Exception as e:
        logger.error(f"Failed to list providers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def test_model(model_id: str, prompt: str = "Hello, how are you?"):
    """
    Test a model with a simple prompt

    Query Parameters:
    - model_id: Model to test (e.g., "openai/gpt-4")
    - prompt: Test prompt (default: "Hello, how are you?")

    Returns the model's response and timing information.
    Useful for verifying model availability and response quality.
    """
    try:
        logger.info(f"Testing model {model_id} with prompt: {prompt[:50]}...")

        import time
        start_time = time.time()

        # Test the model
        response = await llm_client.chat_completion(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        elapsed_time = (time.time() - start_time) * 1000  # Convert to ms

        return {
            "model": model_id,
            "prompt": prompt,
            "response": response,
            "response_time_ms": round(elapsed_time, 2),
            "success": True
        }

    except Exception as e:
        logger.error(f"Model test failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Model test failed: {str(e)}")
