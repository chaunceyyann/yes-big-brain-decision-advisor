"""
API client functions for OpenAI GPT and xAI Grok APIs.
"""

import logging
from typing import Any, Dict, Optional

import requests

# Set up logging
logger = logging.getLogger(__name__)


def call_openai_gpt(
    api_key: str, prompt: str, system_prompt: str = None, model: str = "gpt-3.5-turbo"
) -> Optional[str]:
    """
    Call OpenAI GPT API for chat completion.

    Args:
        api_key: OpenAI API key
        prompt: User prompt
        system_prompt: System prompt (optional)
        model: Model to use (default: gpt-3.5-turbo)

    Returns:
        Generated text or None if error
    """
    try:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 150,
            },
            timeout=10,
        )

        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        else:
            logger.error(
                f"OpenAI API error: Status {response.status_code}, Response: {response.text}"
            )
            return None
    except Exception as e:
        logger.error(f"OpenAI API exception: {str(e)}", exc_info=True)
        return None


def call_xai_grok(
    api_key: str, prompt: str, system_prompt: str = None, model: str = "grok-3"
) -> Optional[str]:
    """
    Call xAI Grok API for chat completion.

    Args:
        api_key: xAI API key
        prompt: User prompt
        system_prompt: System prompt (optional)
        model: Model to use (default: grok-3)

    Returns:
        Generated text or None if error
    """
    try:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 150,
            },
            timeout=10,
        )

        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        else:
            logger.error(
                f"xAI API error: Status {response.status_code}, Response: {response.text}"
            )
            return None
    except Exception as e:
        logger.error(f"xAI API exception: {str(e)}", exc_info=True)
        return None


def get_available_apis(secrets: Dict[str, Any]) -> Dict[str, bool]:
    """
    Check which APIs are available from Streamlit secrets.

    Args:
        secrets: Streamlit secrets object

    Returns:
        Dictionary with API availability status
    """
    available = {
        "openai": False,
        "xai": False,
    }

    try:
        openai_key = secrets.get("openai", {}).get("api_key", "")
        if openai_key and openai_key not in [
            "your-openai-api-key-here",
            "",
            None,
        ]:
            available["openai"] = True
    except Exception:
        pass

    try:
        xai_key = secrets.get("xai", {}).get("api_key", "")
        if xai_key and xai_key not in ["your-xai-api-key-here", "", None]:
            available["xai"] = True
    except Exception:
        pass

    return available


def get_ai_criteria_suggestions(
    decision: str, options: list, api_key: str, api_type: str = "openai"
) -> Optional[list]:
    """
    Get AI suggestions for criteria based on decision and options.

    Args:
        decision: Decision question
        options: List of options
        api_key: API key (OpenAI or xAI)
        api_type: Type of API ('openai' or 'xai')

    Returns:
        List of suggested criteria or None if error
    """
    prompt = f"""
    Decision: {decision}
    Options: {', '.join(options)}

    Suggest 3-5 relevant criteria (factors) that someone should consider when making this decision.
    Return ONLY a comma-separated list of criteria names, nothing else.
    Example: Cost, Quality, Time, Risk, Flexibility
    """
    system_prompt = "You are a helpful decision advisor. Provide concise, relevant criteria for decision-making."

    try:
        if api_type == "openai":
            result = call_openai_gpt(api_key, prompt, system_prompt)
        else:
            result = call_xai_grok(api_key, prompt, system_prompt)

        if result:
            # Parse comma-separated list
            criteria = [c.strip() for c in result.split(",")]
            return criteria[:5]  # Limit to 5 criteria
        return None
    except Exception as e:
        logger.error(f"Error getting AI criteria suggestions: {str(e)}", exc_info=True)
        return None


def get_ai_weight_suggestions(
    decision: str, options: list, criteria: list, api_key: str, api_type: str = "openai"
) -> Optional[dict]:
    """
    Get AI suggestions for weights for each criterion.

    Args:
        decision: Decision question
        options: List of options
        criteria: List of criteria
        api_key: API key (OpenAI or xAI)
        api_type: Type of API ('openai' or 'xai')

    Returns:
        Dictionary mapping criteria to suggested weights (0.0-1.0) or None if error
    """
    prompt = f"""
    Decision: {decision}
    Options: {', '.join(options)}
    Criteria: {', '.join(criteria)}

    Suggest relative importance (weights) for each criterion as percentages that sum to 100%.
    Return ONLY a comma-separated list in format: Criterion1:XX%, Criterion2:YY%, etc.
    Example: Cost:40%, Quality:35%, Time:25%
    """
    system_prompt = "You are a helpful decision advisor. Provide relative importance weights for criteria."

    try:
        if api_type == "openai":
            result = call_openai_gpt(api_key, prompt, system_prompt)
        else:
            result = call_xai_grok(api_key, prompt, system_prompt)

        if result:
            # Parse the result
            weights_dict = {}
            parts = result.split(",")
            for part in parts:
                part = part.strip()
                if ":" in part:
                    criterion, weight_str = part.split(":", 1)
                    criterion = criterion.strip()
                    weight_str = weight_str.strip().replace("%", "")
                    try:
                        weight = float(weight_str) / 100.0  # Convert percentage to 0-1
                        weights_dict[criterion] = weight
                    except ValueError:
                        continue
            return weights_dict
        return None
    except Exception as e:
        logger.error(f"Error getting AI weight suggestions: {str(e)}", exc_info=True)
        return None
