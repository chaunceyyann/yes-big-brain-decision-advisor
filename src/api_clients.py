"""
API client functions for OpenAI GPT and xAI Grok APIs.
"""

import logging
from typing import Any, Dict, Optional

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

# Set up logging
logger = logging.getLogger(__name__)

# Timeout constants (in seconds)
TIMEOUT_SHORT = 15  # For criteria and weights (smaller responses)
TIMEOUT_LONG = 30  # For scores (larger responses, more tokens)


def call_openai_gpt(
    api_key: str,
    prompt: str,
    system_prompt: str = None,
    model: str = "gpt-3.5-turbo",
    max_tokens: int = 150,
    timeout: int = None,
) -> Optional[str]:
    """
    Call OpenAI GPT API for chat completion.

    Args:
        api_key: OpenAI API key
        prompt: User prompt
        system_prompt: System prompt (optional)
        model: Model to use (default: gpt-3.5-turbo)
        max_tokens: Maximum tokens to generate
        timeout: Request timeout in seconds (default: TIMEOUT_SHORT for small, TIMEOUT_LONG for large)

    Returns:
        Generated text or None if error
    """
    # Auto-determine timeout based on max_tokens if not provided
    if timeout is None:
        timeout = TIMEOUT_LONG if max_tokens > 300 else TIMEOUT_SHORT

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
                "max_tokens": max_tokens,
            },
            timeout=timeout,
        )

        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        else:
            error_msg = f"OpenAI API error: Status {response.status_code}"
            try:
                error_detail = (
                    response.json().get("error", {}).get("message", response.text)
                )
                error_msg += f", Message: {error_detail}"
            except:
                error_msg += f", Response: {response.text[:200]}"
            logger.error(error_msg)
            return None
    except Timeout:
        logger.error(
            f"OpenAI API timeout after {timeout}s. The request took too long. Try reducing max_tokens or check your connection."
        )
        return None
    except ConnectionError as e:
        logger.error(
            f"OpenAI API connection error: {str(e)}. Check your internet connection."
        )
        return None
    except RequestException as e:
        logger.error(f"OpenAI API request error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"OpenAI API unexpected error: {str(e)}", exc_info=True)
        return None


def call_xai_grok(
    api_key: str,
    prompt: str,
    system_prompt: str = None,
    model: str = "grok-3",
    max_tokens: int = 150,
    timeout: int = None,
) -> Optional[str]:
    """
    Call xAI Grok API for chat completion.

    Args:
        api_key: xAI API key
        prompt: User prompt
        system_prompt: System prompt (optional)
        model: Model to use (default: grok-3)
        max_tokens: Maximum tokens to generate
        timeout: Request timeout in seconds (default: TIMEOUT_SHORT for small, TIMEOUT_LONG for large)

    Returns:
        Generated text or None if error
    """
    # Auto-determine timeout based on max_tokens if not provided
    if timeout is None:
        timeout = TIMEOUT_LONG if max_tokens > 300 else TIMEOUT_SHORT

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
                "max_tokens": max_tokens,
            },
            timeout=timeout,
        )

        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        else:
            error_msg = f"xAI API error: Status {response.status_code}"
            try:
                error_detail = (
                    response.json().get("error", {}).get("message", response.text)
                )
                error_msg += f", Message: {error_detail}"
            except:
                error_msg += f", Response: {response.text[:200]}"
            logger.error(error_msg)
            return None
    except Timeout:
        logger.error(
            f"xAI API timeout after {timeout}s. The request took too long. Try reducing max_tokens or check your connection."
        )
        return None
    except ConnectionError as e:
        logger.error(
            f"xAI API connection error: {str(e)}. Check your internet connection."
        )
        return None
    except RequestException as e:
        logger.error(f"xAI API request error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"xAI API unexpected error: {str(e)}", exc_info=True)
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
    # Improved prompt with clearer instructions
    prompt = f"""Given this decision scenario:

Decision: {decision}
Options: {', '.join(options)}

Suggest 3-6 relevant criteria (factors) that someone should consider when making this decision.

IMPORTANT: Return ONLY a comma-separated list of criteria names, nothing else.

Example: Cost, Quality, Time, Risk, Flexibility

Do not include any explanation, just the list."""

    system_prompt = "You are a decision analysis expert. Provide concise, relevant criteria for decision-making."

    logger.info(f"[CRITERIA] Prompt: {prompt}")
    logger.info(f"[CRITERIA] Options: {options}")

    try:
        if api_type == "openai":
            result = call_openai_gpt(api_key, prompt, system_prompt, max_tokens=150)
        else:
            result = call_xai_grok(api_key, prompt, system_prompt, max_tokens=150)

        logger.info(f"[CRITERIA] Raw API response: {result}")

        if result:
            # Clean the result - remove any markdown formatting or extra text
            result = result.strip()
            # Remove markdown code blocks if present
            if result.startswith("```"):
                lines = result.split("\n")
                result = "\n".join(
                    [l for l in lines if not l.strip().startswith("```")]
                )

            # Parse comma-separated list
            criteria = [c.strip() for c in result.split(",") if c.strip()]
            criteria = criteria[:5]  # Limit to 5 criteria
            logger.info(f"[CRITERIA] Parsed criteria: {criteria}")
            return criteria if criteria else None
        logger.warning("[CRITERIA] No result from API")
        return None
    except Exception as e:
        logger.error(f"Error getting AI criteria suggestions: {str(e)}", exc_info=True)
        return None


def get_ai_criteria_and_weights_suggestions(
    decision: str, options: list, api_key: str, api_type: str = "openai"
) -> Optional[tuple]:
    """
    Get AI suggestions for both criteria and their weights in a single call.

    Args:
        decision: Decision question
        options: List of options
        api_key: API key (OpenAI or xAI)
        api_type: Type of API ('openai' or 'xai')

    Returns:
        Tuple of (criteria_list, weights_dict) or None if error
        - criteria_list: List of criterion names
        - weights_dict: Dictionary mapping criterion -> weight (0.0-1.0)
    """
    # Combined prompt for criteria and weights
    prompt = f"""Given this decision scenario:

Decision: {decision}
Options: {', '.join(options)}

Suggest 3-6 relevant criteria (factors) that someone should consider when making this decision, along with their importance weights.

IMPORTANT: Return ONLY a comma-separated list in this exact format:
CriterionName1:0.XX,CriterionName2:0.YY,CriterionName3:0.ZZ

Where:
- CriterionName1, CriterionName2, etc. are the criteria names
- 0.XX, 0.YY, 0.ZZ are importance weights as decimal numbers between 0.0 and 1.0
- Each weight represents how important that criterion is (0.0 = not important, 1.0 = very important)
- Weights do NOT need to sum to 1.0 - each is independent

Example: Cost:0.8,Quality:0.9,Time:0.6

Do not include any explanation, just the list."""

    system_prompt = "You are a decision analysis expert. Provide criteria and their importance weights (0.0-1.0) in the exact format requested. Each weight is independent and represents importance level."

    logger.info(f"[CRITERIA+WEIGHT] Prompt: {prompt}")
    logger.info(f"[CRITERIA+WEIGHT] Options: {options}")

    try:
        if api_type == "openai":
            result = call_openai_gpt(api_key, prompt, system_prompt, max_tokens=250)
        else:
            result = call_xai_grok(api_key, prompt, system_prompt, max_tokens=250)

        logger.info(f"[CRITERIA+WEIGHT] Raw API response: {result}")

        if result:
            # Clean the result - remove any markdown formatting or extra text
            result = result.strip()
            # Remove markdown code blocks if present
            if result.startswith("```"):
                lines = result.split("\n")
                result = "\n".join(
                    [l for l in lines if not l.strip().startswith("```")]
                )

            # Parse the result
            criteria = []
            weights_dict = {}
            parts = result.split(",")
            logger.info(f"[CRITERIA+WEIGHT] Parsed parts: {parts}")

            for part in parts:
                part = part.strip()
                if ":" in part:
                    criterion, weight_str = part.split(":", 1)
                    criterion = criterion.strip()
                    weight_str = weight_str.strip()
                    try:
                        weight = float(weight_str)
                        # Clamp to 0-1 range
                        weight = max(0.0, min(1.0, weight))
                        criteria.append(criterion)
                        weights_dict[criterion] = weight
                        logger.info(f"[CRITERIA+WEIGHT] Parsed: {criterion} = {weight}")
                    except ValueError as e:
                        logger.warning(
                            f"[CRITERIA+WEIGHT] Failed to parse weight for {criterion}: {weight_str} - {e}"
                        )
                        continue

            logger.info(f"[CRITERIA+WEIGHT] Final criteria: {criteria}")
            logger.info(f"[CRITERIA+WEIGHT] Final weights_dict: {weights_dict}")

            if criteria and weights_dict:
                return (criteria, weights_dict)
            return None
        logger.warning("[CRITERIA+WEIGHT] No result from API")
        return None
    except Exception as e:
        logger.error(
            f"Error getting AI criteria and weight suggestions: {str(e)}", exc_info=True
        )
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
    # Improved prompt with clearer instructions
    prompt = f"""Given this decision scenario:

Decision: {decision}
Options: {', '.join(options)}
Criteria: {', '.join(criteria)}

Provide importance weights for each criterion as decimal numbers between 0.0 and 1.0.

IMPORTANT: Return ONLY a comma-separated list in this exact format:
CriterionName1:0.XX,CriterionName2:0.YY,CriterionName3:0.ZZ

Where:
- 0.XX, 0.YY, 0.ZZ are decimal numbers between 0.0 and 1.0
- Each weight represents how important that criterion is (0.0 = not important, 1.0 = very important)
- Weights do NOT need to sum to 1.0 - each is independent

Example: Cost:0.8,Quality:0.9,Time:0.6

Do not include any explanation, just the list."""

    system_prompt = "You are a decision analysis expert. Provide importance weights (0.0-1.0) for criteria in the exact format requested. Each weight is independent and represents importance level."

    logger.info(f"[WEIGHT] Prompt: {prompt}")
    logger.info(f"[WEIGHT] Criteria: {criteria}")

    try:
        if api_type == "openai":
            result = call_openai_gpt(api_key, prompt, system_prompt, max_tokens=200)
        else:
            result = call_xai_grok(api_key, prompt, system_prompt, max_tokens=200)

        logger.info(f"[WEIGHT] Raw API response: {result}")

        if result:
            # Clean the result - remove any markdown formatting or extra text
            result = result.strip()
            # Remove markdown code blocks if present
            if result.startswith("```"):
                lines = result.split("\n")
                result = "\n".join(
                    [l for l in lines if not l.strip().startswith("```")]
                )

            # Parse the result
            weights_dict = {}
            parts = result.split(",")
            logger.info(f"[WEIGHT] Parsed parts: {parts}")

            for part in parts:
                part = part.strip()
                if ":" in part:
                    criterion, weight_str = part.split(":", 1)
                    criterion = criterion.strip()
                    weight_str = weight_str.strip()
                    try:
                        weight = float(weight_str)
                        # Clamp to 0-1 range
                        weight = max(0.0, min(1.0, weight))
                        weights_dict[criterion] = weight
                        logger.info(f"[WEIGHT] Parsed: {criterion} = {weight}")
                    except ValueError as e:
                        logger.warning(
                            f"[WEIGHT] Failed to parse weight for {criterion}: {weight_str} - {e}"
                        )
                        continue

            logger.info(f"[WEIGHT] Final weights_dict: {weights_dict}")

            # Check if we got weights for all criteria
            if len(weights_dict) < len(criteria):
                logger.warning(
                    f"[WEIGHT] Only got {len(weights_dict)} weights for {len(criteria)} criteria"
                )

            return weights_dict if weights_dict else None
        logger.warning("[WEIGHT] No result from API")
        return None
    except Exception as e:
        logger.error(f"Error getting AI weight suggestions: {str(e)}", exc_info=True)
        return None


def get_ai_score_suggestions(
    decision: str, options: list, criteria: list, api_key: str, api_type: str = "openai"
) -> Optional[dict]:
    """
    Get AI suggestions for scores for each option on each criterion.

    Args:
        decision: Decision question
        options: List of options
        criteria: List of criteria
        api_key: API key (OpenAI or xAI)
        api_type: Type of API ('openai' or 'xai')

    Returns:
        Dictionary mapping option -> criterion -> score (1-10) or None if error
    """
    # Improved prompt with clearer instructions and exact option names
    prompt = f"""Given this decision scenario:

Decision: {decision}
Options: {', '.join(options)}
Criteria: {', '.join(criteria)}

Rate each option on each criterion using a 1-10 scale where:
- 1-3 = Poor
- 4-6 = Average
- 7-10 = Excellent

IMPORTANT: Return ONLY in this exact format (one option per line, separated by semicolons):
OptionName1|Criterion1:score,Criterion2:score,Criterion3:score;OptionName2|Criterion1:score,Criterion2:score,Criterion3:score

Use the EXACT option names as provided: {', '.join(options)}
Use the EXACT criterion names as provided: {', '.join(criteria)}

Example:
Stay at current job|Cost:7,Quality:8,Time:6;Switch to remote role|Cost:5,Quality:7,Time:9

Do not include any explanation, just the structured data."""

    system_prompt = "You are a decision analysis expert. Provide precise scores for each option on each criterion in the exact format requested."

    logger.info(f"[SCORE] Prompt: {prompt}")
    logger.info(f"[SCORE] Options: {options}")
    logger.info(f"[SCORE] Criteria: {criteria}")

    try:
        if api_type == "openai":
            result = call_openai_gpt(api_key, prompt, system_prompt, max_tokens=500)
        else:
            result = call_xai_grok(api_key, prompt, system_prompt, max_tokens=500)

        logger.info(f"[SCORE] Raw API response: {result}")

        if result:
            # Clean the result - remove any markdown formatting or extra text
            result = result.strip()
            # Remove markdown code blocks if present
            if result.startswith("```"):
                lines = result.split("\n")
                result = "\n".join(
                    [l for l in lines if not l.strip().startswith("```")]
                )

            # Parse the result
            scores_dict = {}
            # Split by semicolon to get each option
            option_parts = result.split(";")
            logger.info(f"[SCORE] Parsed option_parts: {option_parts}")

            for option_part in option_parts:
                option_part = option_part.strip()
                if not option_part:
                    continue

                if "|" in option_part:
                    option_name, scores_str = option_part.split("|", 1)
                    option_name = option_name.strip()
                    scores_dict[option_name] = {}
                    logger.info(f"[SCORE] Processing option: {option_name}")

                    # Parse scores for this option
                    score_parts = scores_str.split(",")
                    for score_part in score_parts:
                        score_part = score_part.strip()
                        if ":" in score_part:
                            criterion, score_str = score_part.split(":", 1)
                            criterion = criterion.strip()
                            score_str = score_str.strip()
                            try:
                                score = float(score_str)
                                # Clamp to 1-10 range
                                score = max(1, min(10, int(score)))
                                scores_dict[option_name][criterion] = score
                                logger.info(
                                    f"[SCORE] Parsed: {option_name} -> {criterion} = {score}"
                                )
                            except ValueError as e:
                                logger.warning(
                                    f"[SCORE] Failed to parse score for {option_name}/{criterion}: {score_str} - {e}"
                                )
                                continue
                else:
                    logger.warning(
                        f"[SCORE] Option part missing '|' separator: {option_part}"
                    )

            logger.info(f"[SCORE] Final scores_dict: {scores_dict}")

            # Check if we got scores for all options
            if len(scores_dict) < len(options):
                logger.warning(
                    f"[SCORE] Only got scores for {len(scores_dict)} out of {len(options)} options"
                )

            return scores_dict if scores_dict else None
        logger.warning("[SCORE] No result from API")
        return None
    except Exception as e:
        logger.error(f"Error getting AI score suggestions: {str(e)}", exc_info=True)
        return None
