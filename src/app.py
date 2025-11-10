# app.py
import logging
import re
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

from api_clients import (
    call_openai_gpt,
    call_xai_grok,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_XAI_MODEL,
    get_ai_criteria_and_weights_suggestions,
    get_ai_criteria_suggestions,
    get_ai_options_suggestions,
    get_ai_score_suggestions,
    get_ai_weight_suggestions,
    get_available_apis,
)
from database import authenticate_user, create_user
from database import delete_decision as db_delete_decision
from database import get_decision_by_id, get_user_decisions, init_database
from database import save_decision as db_save_decision

# === CONFIG ===
st.set_page_config(
    page_title="Yes? AI Decision Guide", page_icon="✅", layout="centered"
)

# Initialize database
init_database()


def process_options(options: list) -> list:
    """
    Process and clean options before sending to AI.

    Args:
        options: List of raw option strings

    Returns:
        List of processed options with formatting, deduplication, and capitalization
    """
    if not options:
        return []

    processed = []
    seen = set()

    # Simple emoji mapping for common options (fast lookup, no API calls)
    emoji_map = {
        "job": "💼",
        "work": "💼",
        "career": "💼",
        "home": "🏠",
        "house": "🏠",
        "move": "🚚",
        "car": "🚗",
        "vehicle": "🚗",
        "tesla": "🚗",
        "travel": "✈️",
        "trip": "✈️",
        "vacation": "✈️",
        "food": "🍔",
        "restaurant": "🍔",
        "eat": "🍔",
        "health": "💪",
        "fitness": "💪",
        "gym": "💪",
        "money": "💰",
        "cost": "💰",
        "price": "💰",
        "time": "⏰",
        "schedule": "⏰",
        "family": "👨‍👩‍👧‍👦",
        "kids": "👨‍👩‍👧‍👦",
        "education": "📚",
        "school": "📚",
        "learn": "📚",
        "tech": "💻",
        "computer": "💻",
        "software": "💻",
    }

    for option in options:
        # 1. Check formatting - remove extra whitespace, normalize
        option = option.strip()
        # Remove multiple spaces
        option = re.sub(r"\s+", " ", option)
        # Remove leading/trailing punctuation that shouldn't be there
        option = option.strip(".,;:!?")

        # Skip empty options
        if not option:
            continue

        # 2. Deduplicate - case-insensitive comparison
        option_lower = option.lower()
        if option_lower in seen:
            continue
        seen.add(option_lower)

        # 3. Capitalize text - smart title case
        # Split into words and capitalize each word properly
        words = option.split()
        capitalized_words = []
        for word in words:
            # Handle special cases (all caps acronyms, etc.)
            if word.isupper() and len(word) > 1:
                # Keep acronyms as-is if they're all caps
                capitalized_words.append(word)
            elif word.lower() in ["ai", "api", "ui", "ux", "id", "url"]:
                # Keep common acronyms uppercase
                capitalized_words.append(word.upper())
            else:
                # Normal title case
                capitalized_words.append(word.capitalize())

        option = " ".join(capitalized_words)

        # 4. Optional: Add emoji if found (fast lookup, skip if not found)
        # Check if any keyword in the option matches emoji map
        option_lower_words = option_lower.split()
        emoji_found = None
        for word in option_lower_words:
            if word in emoji_map:
                emoji_found = emoji_map[word]
                break

        # Add emoji prefix if found
        if emoji_found:
            option = f"{emoji_found} {option}"

        processed.append(option)

    return processed


OPENAI_MODEL_OPTIONS = [
    {"id": "gpt-4o-mini", "label": "GPT-4o mini (fast & cost-efficient)"},
    {"id": "gpt-4o", "label": "GPT-4o (balanced quality)"},
    {"id": "gpt-4.1", "label": "GPT-4.1 (latest model)"},
    {"id": "gpt-3.5-turbo", "label": "GPT-3.5 Turbo (legacy)"},
]

XAI_MODEL_OPTIONS = [
    {"id": "grok-4", "label": "Grok-4 (best quality)"},
    {"id": "grok-3", "label": "Grok-3 (faster)"},
]


def get_model_display(model_id: str, options: list[dict]) -> str:
    for option in options:
        if option["id"] == model_id:
            return option["label"]
    return model_id


def get_model_index(model_id: str, options: list[dict], fallback_id: str) -> int:
    for idx, option in enumerate(options):
        if option["id"] == model_id:
            return idx
    for idx, option in enumerate(options):
        if option["id"] == fallback_id:
            return idx
    return 0


# Ensure defaults from API client constants always appear in option lists
if DEFAULT_OPENAI_MODEL not in [opt["id"] for opt in OPENAI_MODEL_OPTIONS]:
    OPENAI_MODEL_OPTIONS.append(
        {"id": DEFAULT_OPENAI_MODEL, "label": DEFAULT_OPENAI_MODEL}
    )

if DEFAULT_XAI_MODEL not in [opt["id"] for opt in XAI_MODEL_OPTIONS]:
    XAI_MODEL_OPTIONS.append({"id": DEFAULT_XAI_MODEL, "label": DEFAULT_XAI_MODEL})


# === AI INITIAL DECISION (Question + Options Only) ===
def get_ai_initial_decision(
    decision,
    options,
    custom_prompt=None,
    preferred_api=None,
    preferred_model=None,
):
    """
    Get AI's initial decision based on just question and options, before any scoring.

    Args:
        decision: Decision question
        options: List of options
        custom_prompt: Optional custom prompt/context from user
        preferred_api: Preferred API to use ('openai', 'xai', or None for auto-select)
        preferred_model: Preferred model to use when an API is selected

    Returns:
        AI initial decision string
    """
    prompt = f"""
Decision: {decision}
Options: {', '.join(options)}
"""
    if custom_prompt:
        prompt += f"\nAdditional context: {custom_prompt}"

    prompt += "\n\nBased on just the decision question and options, which option would you recommend and why? Give a confident, concise recommendation in 2-3 sentences."

    system_prompt = "You are a confident, helpful decision advisor. Give an initial recommendation based on the decision question and options alone, without any structured analysis."

    # Check available APIs
    try:
        available_apis = get_available_apis(st.secrets)
    except Exception:
        available_apis = {"openai": False, "xai": False}

    # Determine which API to use
    api_to_use = None
    if preferred_api and available_apis.get(preferred_api, False):
        api_to_use = preferred_api
    elif available_apis.get("openai", False):
        api_to_use = "openai"
    elif available_apis.get("xai", False):
        api_to_use = "xai"

    recommendation = None

    # Try OpenAI GPT first (if selected or auto-selected)
    if api_to_use == "openai":
        try:
            openai_key = st.secrets.get("openai", {}).get("api_key")
            openai_model = preferred_model or st.session_state.get(
                "openai_model", DEFAULT_OPENAI_MODEL
            )
            recommendation = call_openai_gpt(
                openai_key,
                prompt,
                system_prompt,
                model=openai_model,
                max_tokens=200,
            )
            if recommendation:
                return f"**Yes? (GPT) initial take:** {recommendation}"
        except Exception as e:
            logging.error(f"OpenAI initial decision error: {str(e)}", exc_info=True)

    # Try xAI Grok (if selected or OpenAI failed)
    if api_to_use == "xai" or (api_to_use == "openai" and not recommendation):
        try:
            xai_key = st.secrets.get("xai", {}).get("api_key")
            xai_model = preferred_model or st.session_state.get(
                "xai_model", DEFAULT_XAI_MODEL
            )
            recommendation = call_xai_grok(
                xai_key,
                prompt,
                system_prompt,
                model=xai_model,
                max_tokens=200,
            )
            if recommendation:
                return f"**Yes? (Grok) initial take:** {recommendation}"
        except Exception as e:
            logging.error(f"xAI initial decision error: {str(e)}", exc_info=True)

    # Fallback
    return f"**Yes? initial take:** Based on your decision '{decision}', I'd lean toward **{options[0] if options else 'the first option'}**. But let's see what the numbers say after you score everything!"


# === AI RECOMMENDATION (OpenAI GPT / xAI Grok) ===
def get_ai_recommendation(
    decision,
    options,
    df,
    params,
    weights,
    custom_prompt=None,
    preferred_api=None,
    preferred_model=None,
):
    """
    Get AI recommendation using OpenAI GPT or xAI Grok API, with fallback to mock.

    Args:
        decision: Decision question
        options: List of options
        df: DataFrame with scores
        params: List of criteria
        weights: List of weights
        preferred_api: Preferred API to use ('openai', 'xai', or None for auto-select)
        preferred_model: Preferred model to use when an API is selected

    Returns:
        AI recommendation string
    """
    top = df.iloc[0]
    prompt = f"""
    Decision: {decision}
    Options: {', '.join(options)}
    Criteria: {', '.join([f'{p} ({w*100:.0f}%)' for p, w in zip(params, weights)])}
    Winner: {top['Option']} with score {top['Total Score']:.2f}
"""
    if custom_prompt:
        prompt += f"\nAdditional context: {custom_prompt}"

    prompt += (
        "\n\nGive a confident, concise, human-sounding recommendation in 2-3 sentences."
    )

    system_prompt = "You are a confident, helpful decision advisor. Give concise, actionable recommendations in 2-3 sentences."

    # Check available APIs
    try:
        available_apis = get_available_apis(st.secrets)
    except Exception:
        available_apis = {"openai": False, "xai": False}

    # Determine which API to use
    api_to_use = None
    if preferred_api and available_apis.get(preferred_api, False):
        api_to_use = preferred_api
    elif available_apis.get("openai", False):
        api_to_use = "openai"
    elif available_apis.get("xai", False):
        api_to_use = "xai"

    recommendation = None

    # Try OpenAI GPT first (if selected or auto-selected)
    if api_to_use == "openai":
        try:
            # Get OpenAI API key from Streamlit secrets
            # Local: reads from .streamlit/secrets.toml
            # Cloud: reads from Streamlit Cloud dashboard secrets
            openai_key = st.secrets.get("openai", {}).get("api_key")
            openai_model = preferred_model or st.session_state.get(
                "openai_model", DEFAULT_OPENAI_MODEL
            )
            recommendation = call_openai_gpt(
                openai_key,
                prompt,
                system_prompt,
                model=openai_model,
            )
            if recommendation:
                return f"**Yes? (GPT) says:** {recommendation}"
            else:
                st.warning("⚠️ OpenAI API error, trying fallback...")
                logging.error("OpenAI API call failed - check logs for details")
        except Exception as e:
            st.warning(f"⚠️ OpenAI API error: {str(e)}, trying fallback...")
            logging.error(f"OpenAI API exception: {str(e)}", exc_info=True)

    # Try xAI Grok (if selected or OpenAI failed)
    if api_to_use == "xai" or (api_to_use == "openai" and not recommendation):
        try:
            # Get xAI API key from Streamlit secrets
            # Local: reads from .streamlit/secrets.toml
            # Cloud: reads from Streamlit Cloud dashboard secrets
            xai_key = st.secrets.get("xai", {}).get("api_key")
            xai_model = preferred_model or st.session_state.get(
                "xai_model", DEFAULT_XAI_MODEL
            )
            recommendation = call_xai_grok(
                xai_key,
                prompt,
                system_prompt,
                model=xai_model,
            )
            if recommendation:
                return f"**Yes? (Grok) says:** {recommendation}"
            else:
                st.warning("⚠️ xAI API error, using fallback recommendation")
                logging.error("xAI API call failed - check logs for details")
        except Exception as e:
            st.warning(f"⚠️ xAI API error: {str(e)}, using fallback recommendation")
            logging.error(f"xAI API exception: {str(e)}", exc_info=True)

    # Fallback to mock recommendation
    return f"**Yes? says:** Go with **{top['Option']}**. It crushes on your top priorities — {params[0]} and {params[1] if len(params)>1 else ''}. The numbers don't lie."


# === APP ===
st.title("✅ Yes?")
st.markdown(
    "*The AI that turns 'maybe' into 'hell yes' — with math, visuals, and zero fluff.*"
)

# Welcome section for new users
if "has_seen_welcome" not in st.session_state:
    st.session_state["has_seen_welcome"] = False

with st.expander(
    "👋 Welcome! How does this work?", expanded=not st.session_state["has_seen_welcome"]
):
    st.markdown(
        """
    **Yes? helps you make better decisions in 4 simple steps:**

    1. **Define your decision** - What are you trying to decide?
    2. **List your options** - What are your choices?
    3. **Set criteria & weights** - What matters most? (e.g., Cost, Quality, Time)
    4. **Score each option** - Rate how well each option performs (1-10 scale)

    The app will calculate weighted scores, rank your options, and give you an AI recommendation!

    💡 **Tip:** Be honest with your scores and adjust weights to match your true priorities.
    """
    )
    # Button to collapse welcome section - only show if not dismissed yet
    if not st.session_state["has_seen_welcome"]:
        if st.button("Got it! Let's start", key="dismiss_welcome"):
            st.session_state["has_seen_welcome"] = True
            st.rerun()

# Sidebar: User Authentication + History
with st.sidebar:
    st.header("👤 Account")

    # Initialize user session state
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = None
    if "username" not in st.session_state:
        st.session_state["username"] = None
    if "show_login" not in st.session_state:
        st.session_state["show_login"] = True
    if "show_signup" not in st.session_state:
        st.session_state["show_signup"] = False
    # Initialize temporary decisions storage
    if "temp_decisions" not in st.session_state:
        st.session_state["temp_decisions"] = []

    # User authentication UI
    if st.session_state["user_id"] is None:
        # Not logged in - show login/signup
        if st.session_state["show_signup"]:
            st.subheader("📝 Sign Up")
            new_username = st.text_input("Username", key="signup_username")
            new_password = st.text_input(
                "Password", type="password", key="signup_password"
            )
            confirm_password = st.text_input(
                "Confirm Password", type="password", key="signup_confirm"
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Sign Up", type="primary", width="stretch"):
                    if not new_username or not new_password:
                        st.error("Please enter username and password")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match")
                    else:
                        user_id = create_user(new_username, new_password)
                        if user_id:
                            st.session_state["user_id"] = user_id
                            st.session_state["username"] = new_username
                            st.session_state["show_signup"] = False
                            # Migrate temporary decisions to database if any exist
                            temp_decisions = st.session_state.get("temp_decisions", [])
                            if temp_decisions:
                                migrated_count = 0
                                for temp_decision in temp_decisions:
                                    try:
                                        db_save_decision(
                                            user_id=user_id,
                                            decision=temp_decision["decision"],
                                            options=temp_decision["options"],
                                            criteria=temp_decision["criteria"],
                                            weights=temp_decision["weights"],
                                            scores=temp_decision["scores"],
                                            winner=temp_decision["winner"],
                                            winner_score=temp_decision["winner_score"],
                                        )
                                        migrated_count += 1
                                    except Exception:
                                        pass  # Skip failed migrations
                                if migrated_count > 0:
                                    st.session_state["temp_decisions"] = []
                                    st.success(
                                        f"Welcome, {new_username}! Migrated {migrated_count} temporary decision(s)."
                                    )
                                else:
                                    st.success(f"Welcome, {new_username}!")
                            else:
                                st.success(f"Welcome, {new_username}!")
                            st.rerun()
                        else:
                            st.error("Username already exists")
            with col2:
                if st.button("Back to Login", width="stretch"):
                    st.session_state["show_signup"] = False
                    st.rerun()
        else:
            st.subheader("🔐 Login")
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Login", type="primary", width="stretch"):
                    if not username or not password:
                        st.error("Please enter username and password")
                    else:
                        user_id = authenticate_user(username, password)
                        if user_id:
                            st.session_state["user_id"] = user_id
                            st.session_state["username"] = username
                            # Migrate temporary decisions to database if any exist
                            temp_decisions = st.session_state.get("temp_decisions", [])
                            if temp_decisions:
                                migrated_count = 0
                                for temp_decision in temp_decisions:
                                    try:
                                        db_save_decision(
                                            user_id=user_id,
                                            decision=temp_decision["decision"],
                                            options=temp_decision["options"],
                                            criteria=temp_decision["criteria"],
                                            weights=temp_decision["weights"],
                                            scores=temp_decision["scores"],
                                            winner=temp_decision["winner"],
                                            winner_score=temp_decision["winner_score"],
                                        )
                                        migrated_count += 1
                                    except Exception:
                                        pass  # Skip failed migrations
                                if migrated_count > 0:
                                    st.session_state["temp_decisions"] = []
                                    st.success(
                                        f"Welcome back, {username}! Migrated {migrated_count} temporary decision(s)."
                                    )
                                else:
                                    st.success(f"Welcome back, {username}!")
                            else:
                                st.success(f"Welcome back, {username}!")
                            st.rerun()
                        else:
                            st.error("Invalid username or password")
            with col2:
                if st.button("Sign Up", width="stretch"):
                    st.session_state["show_signup"] = True
                    st.rerun()
    else:
        # Logged in - show user info and logout
        st.success(f"✅ Logged in as **{st.session_state['username']}**")
        if st.button("🚪 Logout", width="stretch"):
            st.session_state["user_id"] = None
            st.session_state["username"] = None
            # Clear any loaded decision data
            for key in ["load_decision", "decision_to_load", "show_load_confirm"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    st.header("📜 Past Decisions")

    # Load decisions from database for logged-in user
    if st.session_state["user_id"] is not None:
        user_decisions = get_user_decisions(st.session_state["user_id"], limit=10)
        if user_decisions:
            for idx, decision_data in enumerate(user_decisions):
                entry = f"{decision_data['decision']} → **{decision_data['winner']}** ({decision_data['winner_score']:.1f})"
                # Create a button that covers both emoji and text
                col1, col2 = st.columns([4, 1])
                with col1:
                    if st.button(
                        f"📋 {entry}",
                        key=f"load_{decision_data['id']}",
                        help=f"Load this decision",
                        width="stretch",
                    ):
                        # Store the decision to load in session state
                        st.session_state["decision_to_load"] = decision_data
                        st.session_state["show_load_confirm"] = True
                with col2:
                    if st.button(
                        "🗑️",
                        key=f"delete_{decision_data['id']}",
                        help="Delete this decision",
                    ):
                        if db_delete_decision(
                            decision_data["id"], st.session_state["user_id"]
                        ):
                            st.success("Decision deleted")
                            st.rerun()
                        else:
                            st.error("Failed to delete decision")
        else:
            st.write("• No decisions saved yet")
    else:
        # Show temporary decisions for non-logged-in users
        temp_decisions = st.session_state.get("temp_decisions", [])
        if temp_decisions:
            st.caption(
                "💡 *Temporary decisions (lost on refresh). Log in to save permanently.*"
            )
            for idx, decision_data in enumerate(temp_decisions):
                entry = f"{decision_data['decision']} → **{decision_data['winner']}** ({decision_data['winner_score']:.1f})"
                col1, col2 = st.columns([4, 1])
                with col1:
                    if st.button(
                        f"📋 {entry}",
                        key=f"load_temp_{idx}",
                        help=f"Load this temporary decision",
                        width="stretch",
                    ):
                        # Store the decision to load in session state
                        st.session_state["decision_to_load"] = decision_data
                        st.session_state["show_load_confirm"] = True
                with col2:
                    if st.button(
                        "🗑️",
                        key=f"delete_temp_{idx}",
                        help="Delete this temporary decision",
                    ):
                        st.session_state["temp_decisions"].pop(idx)
                        st.success("Decision deleted")
                        st.rerun()
        else:
            st.info("👆 Log in to save permanently, or save temporarily below")

# === CONFIRMATION DIALOG ===
# Confirmation dialog for loading a decision (in main area)
if (
    st.session_state.get("show_load_confirm", False)
    and "decision_to_load" in st.session_state
):
    decision_to_load = st.session_state["decision_to_load"]
    st.warning(f"⚠️ **Load this decision?** This will replace your current inputs.")
    with st.container():
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write(f"**Decision:** {decision_to_load['decision']}")
            st.write(f"**Options:** {', '.join(decision_to_load['options'])}")
            st.write(
                f"**Winner:** {decision_to_load['winner']} ({decision_to_load['winner_score']:.1f})"
            )
        with col2:
            st.write("")
            if st.button("✅ Yes, Load It", key="confirm_load", type="primary"):
                st.session_state["load_decision"] = decision_to_load
                st.session_state["show_load_confirm"] = False
                st.rerun()
            if st.button("❌ Cancel", key="cancel_load"):
                st.session_state["show_load_confirm"] = False
                if "decision_to_load" in st.session_state:
                    del st.session_state["decision_to_load"]
                st.rerun()
    st.markdown("---")

# === STEP 1: Decision & Options ===
with st.container(border=True):
    st.markdown("### 📝 Step 1: Define Your Decision & Options")

    if "step1_complete" not in st.session_state:
        st.session_state["step1_complete"] = False

    # Check if we need to load a decision
    if "load_decision" in st.session_state:
        load_data = st.session_state["load_decision"]
        loaded_decision = load_data["decision"]
        loaded_options = "\n".join(load_data["options"])
        loaded_criteria = load_data["criteria"]
        loaded_weights = load_data["weights"]
        loaded_scores = {}  # Extract scores from full_results
        for result in load_data["full_results"]:
            option = result["Option"]
            loaded_scores[option] = {}
            for param in loaded_criteria:
                loaded_scores[option][param] = result.get(f"{param} (1-10)", 5)

        # Set session state values for all widgets to prevent rerun issues
        # Set criteria text inputs
        for i, criterion in enumerate(loaded_criteria):
            st.session_state[f"p{i}"] = criterion
        # Set weight sliders
        for i, weight in enumerate(loaded_weights):
            st.session_state[f"w{i}"] = float(weight)
        # Set score sliders - use option index to ensure unique keys
        for opt_idx, option in enumerate(load_data["options"]):
            for param_idx, param in enumerate(loaded_criteria):
                score = loaded_scores.get(option, {}).get(param, 5)
                st.session_state[f"score_{opt_idx}_{param_idx}"] = (
                    int(score) if isinstance(score, (int, float)) else 5
                )

        # Also set num_criteria to match loaded criteria count
        st.session_state["num_criteria"] = len(loaded_criteria)
        st.session_state["step1_complete"] = True

        del st.session_state["load_decision"]
    else:
        loaded_decision = ""
        loaded_options = ""
        loaded_criteria = []
        loaded_weights = []
        loaded_scores = {}

    # Check for AI suggested options in session state
    ai_suggested_options = st.session_state.get("ai_suggested_options", "")
    pending_options_update = st.session_state.pop("pending_options_update", None)
    if pending_options_update is not None:
        st.session_state["options_text_area"] = pending_options_update
        ai_suggested_options = pending_options_update

    # Determine initial value for options text area
    # Priority: loaded_options (from saved decision) > ai_suggested_options > empty
    initial_options_value = loaded_options if loaded_options else ai_suggested_options

    # Check API availability once for Step 1 actions
    try:
        available_apis = get_available_apis(st.secrets)
    except Exception:
        available_apis = {"openai": False, "xai": False}
    has_openai = available_apis.get("openai", False)
    has_xai = available_apis.get("xai", False)
    has_any_api = has_openai or has_xai

    if "openai_model" not in st.session_state:
        st.session_state["openai_model"] = DEFAULT_OPENAI_MODEL
    if "xai_model" not in st.session_state:
        st.session_state["xai_model"] = DEFAULT_XAI_MODEL

    decision = ""
    options_text = initial_options_value

    col1, col2 = st.columns(2)
    with col1:
        decision = st.text_area(
            "What are you deciding?",
            value=loaded_decision,
            placeholder="e.g., Quit job? Move cities? Buy Tesla?",
            help="Enter a clear question about what you're trying to decide",
            height=120,
            key="decision_input",
        )
        if not decision:
            st.info("👆 Enter your decision question to start")
        # Store decision in session state for button access
        st.session_state["current_decision"] = decision
    with col2:
        options_text = st.text_area(
            "List your options (one per line):",
            value=initial_options_value,
            placeholder="Stay at current job\nSwitch to remote role\nStart freelance",
            height=120,
            help="Enter all possible options, one per line. Be comprehensive but realistic.",
            key="options_text_area",
        )
        if not options_text.strip():
            st.info("👆 List all your options above, one per line")

    # Buttons at the top
    col_reset, col_ai_suggest, col_initial_take, col_continue = st.columns(4)
    with col_reset:
        if st.button(
            "🧠 New Decision (reset)",
            help="Clear all fields and start fresh",
            use_container_width=True,
        ):
            # Clear all session state related to loading and AI generation
            for key in [
                "load_decision",
                "decision_to_load",
                "show_load_confirm",
                "ai_generated_for",
                "ai_suggested_options",
                "current_decision",
                "trigger_initial_decision",
                "ai_final_verdict",
                "ai_final_verdict_key",
                "ai_comparison_result",
                "custom_ai_prompt",
            ]:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state["step1_complete"] = False
            st.success("Fresh start!")
            st.rerun()
    with col_ai_suggest:
        if st.button(
            "🤖 AI Suggest Options",
            help="Use AI to suggest options based on your decision question",
            use_container_width=True,
            disabled=not has_any_api,
        ):
            # Get decision from session state (set above)
            current_decision = st.session_state.get("current_decision", "")
            if not current_decision or not current_decision.strip():
                st.warning("⚠️ Please enter a decision question first")
            else:
                # Determine which API to use
                preferred_api = None
                preferred_model = None

                # Use preferred API from session state if set, otherwise auto-select
                if st.session_state.get("preferred_ai_api") and available_apis.get(
                    st.session_state.get("preferred_ai_api"), False
                ):
                    preferred_api = st.session_state.get("preferred_ai_api")
                elif has_xai:
                    preferred_api = "xai"
                elif has_openai:
                    preferred_api = "openai"

                if preferred_api == "openai":
                    preferred_model = st.session_state.get(
                        "openai_model", DEFAULT_OPENAI_MODEL
                    )
                elif preferred_api == "xai":
                    preferred_model = st.session_state.get(
                        "xai_model", DEFAULT_XAI_MODEL
                    )

                if preferred_api:
                    with st.spinner("🤖 AI is suggesting options..."):
                        try:
                            api_key = (
                                st.secrets.get("openai", {}).get("api_key")
                                if preferred_api == "openai"
                                else st.secrets.get("xai", {}).get("api_key")
                            )

                            suggested_options = get_ai_options_suggestions(
                                current_decision,
                                api_key,
                                preferred_api,
                                model=preferred_model,
                            )

                            if suggested_options:
                                # Store suggested options in session state
                                joined_options = "\n".join(suggested_options)
                                st.session_state["ai_suggested_options"] = (
                                    joined_options
                                )
                                st.session_state["pending_options_update"] = (
                                    joined_options
                                )
                                st.session_state["trigger_initial_decision"] = True
                                st.session_state["step1_complete"] = True
                                st.session_state["use_ai"] = True
                                st.session_state.pop("ai_generated_for", None)
                                st.success(
                                    f"✨ AI suggested {len(suggested_options)} options!"
                                )
                                st.rerun()
                            else:
                                st.error(
                                    "⚠️ Could not generate AI suggestions. Please try again."
                                )
                        except Exception as e:
                            st.error(f"⚠️ Error generating AI suggestions: {str(e)}")
                            logging.error(
                                f"AI options suggestion error: {str(e)}", exc_info=True
                            )
                else:
                    st.warning("⚠️ No API available for suggestions")
        if not has_any_api:
            st.caption("💡 Configure API keys to use AI suggestions")

    with col_initial_take:
        if st.button(
            "💭 AI Initial Take",
            help="Get AI's gut feeling based on just your question and options",
            use_container_width=True,
            disabled=(not has_any_api) or (not options_text.strip()),
        ):
            if not decision or not decision.strip() or not options_text.strip():
                st.warning("⚠️ Please enter your decision and options first")
            else:
                st.session_state["trigger_initial_decision"] = True
                st.rerun()

    with col_continue:
        if st.button(
            "➡️ Continue to Step 2",
            help="Proceed to set criteria and weights",
            use_container_width=True,
            disabled=not options_text.strip(),
        ):
            if not decision or not decision.strip():
                st.warning("⚠️ Please enter your decision first")
            elif not options_text.strip():
                st.warning("⚠️ Please enter at least one option before continuing")
            else:
                st.session_state["step1_complete"] = True
                st.rerun()

    # AI checkbox - only show if API is available
    if has_any_api:
        use_ai = st.checkbox(
            "🤖 Use AI to generate criteria, weights, and scores",
            value=st.session_state.get("use_ai", True),  # Default to True
            help="Let AI automatically suggest criteria, weights, and initial scores based on your decision and options",
            key="use_ai_checkbox",
        )
        st.session_state["use_ai"] = use_ai

        # API selection checkboxes for auto-generation
        has_openai_api = available_apis.get("openai", False)
        has_xai_api = available_apis.get("xai", False)

        if has_openai_api or has_xai_api:
            col_openai, col_xai = st.columns(2)

            with col_openai:
                use_openai = st.checkbox(
                    "🤖 OpenAI GPT",
                    value=st.session_state.get("use_openai_ai", has_openai_api),
                    disabled=not has_openai_api,
                    help=(
                        "Use OpenAI GPT for AI generation"
                        if has_openai_api
                        else "OpenAI API key not configured"
                    ),
                    key="use_openai_ai_checkbox",
                )
                st.session_state["use_openai_ai"] = (
                    use_openai if has_openai_api else False
                )

                if use_openai and has_openai_api:
                    openai_model_default = st.session_state.get(
                        "openai_model", DEFAULT_OPENAI_MODEL
                    )
                    openai_model = st.selectbox(
                        "Model",
                        options=[opt["id"] for opt in OPENAI_MODEL_OPTIONS],
                        index=get_model_index(
                            openai_model_default,
                            OPENAI_MODEL_OPTIONS,
                            DEFAULT_OPENAI_MODEL,
                        ),
                        format_func=lambda m: get_model_display(
                            m, OPENAI_MODEL_OPTIONS
                        ),
                        key="openai_ai_model_select",
                    )
                    st.session_state["openai_model"] = openai_model

            with col_xai:
                use_xai = st.checkbox(
                    "🤖 xAI Grok",
                    value=st.session_state.get("use_xai_ai", has_xai_api),
                    disabled=not has_xai_api,
                    help=(
                        "Use xAI Grok for AI generation"
                        if has_xai_api
                        else "xAI API key not configured"
                    ),
                    key="use_xai_ai_checkbox",
                )
                st.session_state["use_xai_ai"] = use_xai if has_xai_api else False

                if use_xai and has_xai_api:
                    xai_model_default = st.session_state.get(
                        "xai_model", DEFAULT_XAI_MODEL
                    )
                    xai_model = st.selectbox(
                        "Model",
                        options=[opt["id"] for opt in XAI_MODEL_OPTIONS],
                        index=get_model_index(
                            xai_model_default,
                            XAI_MODEL_OPTIONS,
                            DEFAULT_XAI_MODEL,
                        ),
                        format_func=lambda m: get_model_display(m, XAI_MODEL_OPTIONS),
                        key="xai_ai_model_select",
                    )
                    st.session_state["xai_model"] = xai_model

            # Determine which API to use based on checkboxes
            # Priority: xAI if both checked, then OpenAI, then fallback
            if st.session_state.get("use_xai_ai", False) and has_xai_api:
                st.session_state["preferred_ai_api"] = "xai"
                st.session_state["preferred_ai_model"] = st.session_state.get(
                    "xai_model", DEFAULT_XAI_MODEL
                )
            elif st.session_state.get("use_openai_ai", False) and has_openai_api:
                st.session_state["preferred_ai_api"] = "openai"
                st.session_state["preferred_ai_model"] = st.session_state.get(
                    "openai_model", DEFAULT_OPENAI_MODEL
                )
            else:
                st.session_state["preferred_ai_api"] = None  # Fallback
                st.session_state["preferred_ai_model"] = None
        else:
            st.session_state["preferred_ai_api"] = None
            st.session_state["preferred_ai_model"] = None
    else:
        st.session_state["use_ai"] = False
        st.session_state["preferred_ai_api"] = None

# Parse and process options
raw_options = options_text.strip().splitlines()
raw_options = [o.strip() for o in raw_options if o.strip()]

if not raw_options:
    st.stop()

# Process options: format, deduplicate, capitalize
options = process_options(raw_options)

# Show processing info if options were changed
if len(options) != len(raw_options):
    removed_count = len(raw_options) - len(options)
    if removed_count > 0:
        st.info(
            f"ℹ️ Processed {len(raw_options)} options: removed {removed_count} duplicate(s), formatted and capitalized."
        )

if not options:
    st.error("⚠️ No valid options after processing. Please enter at least one option.")
    st.stop()

# === INITIAL AI DECISION (Step 1.5) ===
# Show initial AI decision based on just question and options (triggered by button)
if decision and options:
    # Check available APIs
    try:
        available_apis = get_available_apis(st.secrets)
        has_openai = available_apis.get("openai", False)
        has_xai = available_apis.get("xai", False)
        has_any_api = has_openai or has_xai
    except Exception:
        has_any_api = False
        has_openai = False
        has_xai = False

    if has_any_api and st.session_state.get("use_ai", False):
        # Determine which API to use for initial decision
        preferred_api = None
        preferred_model = None
        if st.session_state.get("use_xai_ai", False) and has_xai:
            preferred_api = "xai"
        elif st.session_state.get("use_openai_ai", False) and has_openai:
            preferred_api = "openai"
        elif has_xai:
            preferred_api = "xai"
        elif has_openai:
            preferred_api = "openai"

        if preferred_api == "xai":
            preferred_model = st.session_state.get("xai_model", DEFAULT_XAI_MODEL)
        elif preferred_api == "openai":
            preferred_model = st.session_state.get("openai_model", DEFAULT_OPENAI_MODEL)

        # Check if user triggered initial decision
        decision_hash = f"{decision}_{','.join(options)}"
        initial_decision_key = f"initial_decision_{decision_hash}"

        # Generate initial decision if button was clicked
        if st.session_state.get("trigger_initial_decision", False):
            if initial_decision_key not in st.session_state:
                with st.spinner("🤖 Getting AI's initial take..."):
                    try:
                        # Initial decision doesn't use custom prompt (just question + options)
                        initial_decision = get_ai_initial_decision(
                            decision,
                            options,
                            None,
                            preferred_api,
                            preferred_model,
                        )
                        st.session_state[initial_decision_key] = initial_decision
                    except Exception as e:
                        logging.error(
                            f"Error getting initial decision: {str(e)}", exc_info=True
                        )
                        st.session_state[initial_decision_key] = None
            # Clear trigger
            if "trigger_initial_decision" in st.session_state:
                del st.session_state["trigger_initial_decision"]

        # Display initial decision if available
        if st.session_state.get(initial_decision_key):
            with st.container(border=True):
                st.markdown("### 💭 AI's Initial Take")
                st.caption(
                    "💡 AI's gut feeling based on just your question and options (before any scoring)"
                )
                st.info(st.session_state[initial_decision_key])
                # Option to regenerate
                if st.button(
                    "🔄 Regenerate Initial Take",
                    key="regenerate_initial",
                    help="Get a fresh AI take on your decision",
                ):
                    # Clear existing decision and trigger regeneration
                    del st.session_state[initial_decision_key]
                    st.session_state["trigger_initial_decision"] = True
                    st.rerun()

if not st.session_state.get("step1_complete", False):
    st.stop()

# Initialize params and weights to satisfy linters (will be populated in Step 2)
params = []
weights = []

# === STEP 2: Criteria + Weights ===
with st.container(border=True):
    st.markdown("### ⚖️ Step 2: Set Your Criteria & Weights")
    st.caption(
        "💡 Criteria are the factors that matter to you. Weights determine how important each criterion is (they'll be normalized automatically)."
    )

    # Auto-generate criteria, weights, and scores if AI checkbox is enabled
    # Only generate if not loading from a past decision
    if (
        st.session_state.get("use_ai", False)
        and decision
        and options
        and not loaded_criteria  # Don't generate if loading from past decision
    ):
        # Check if we've already generated for this decision/options combination
        decision_hash = f"{decision}_{','.join(options)}"
        if st.session_state.get("ai_generated_for") != decision_hash:
            # Check available APIs
            try:
                available_apis = get_available_apis(st.secrets)
                has_openai = available_apis.get("openai", False)
                has_xai = available_apis.get("xai", False)
                has_any_api = has_openai or has_xai
            except Exception:
                has_any_api = False
                has_openai = False
                has_xai = False

            if has_any_api:
                with st.spinner("🤖 AI is generating criteria, weights, and scores..."):
                    try:
                        # Determine which API to use based on user preference
                        preferred_api = st.session_state.get("preferred_ai_api", None)
                        if preferred_api and available_apis.get(preferred_api, False):
                            api_type = preferred_api
                        elif has_openai:
                            api_type = "openai"
                        elif has_xai:
                            api_type = "xai"
                        else:
                            api_type = None

                        if not api_type:
                            st.error("⚠️ No API available for generation")
                            st.stop()

                        api_key = (
                            st.secrets.get("openai", {}).get("api_key")
                            if api_type == "openai"
                            else st.secrets.get("xai", {}).get("api_key")
                        )
                        api_model = (
                            st.session_state.get("openai_model", DEFAULT_OPENAI_MODEL)
                            if api_type == "openai"
                            else st.session_state.get("xai_model", DEFAULT_XAI_MODEL)
                        )

                        # Step 1: Generate criteria and weights together (saves tokens)
                        criteria_suggestions = None
                        weight_suggestions = None

                        criteria_and_weights = get_ai_criteria_and_weights_suggestions(
                            decision, options, api_key, api_type, api_model
                        )

                        if criteria_and_weights:
                            criteria_suggestions, weight_suggestions = (
                                criteria_and_weights
                            )

                            # Update criteria count and set suggested criteria
                            st.session_state["num_criteria"] = len(criteria_suggestions)
                            for i, criterion in enumerate(criteria_suggestions):
                                st.session_state[f"p{i}"] = criterion

                            # Update weights based on suggestions
                            if weight_suggestions:
                                for i, criterion in enumerate(criteria_suggestions):
                                    if criterion in weight_suggestions:
                                        st.session_state[f"w{i}"] = weight_suggestions[
                                            criterion
                                        ]
                        else:
                            # Fallback: try separate calls if combined fails
                            criteria_suggestions = get_ai_criteria_suggestions(
                                decision, options, api_key, api_type, api_model
                            )

                            if criteria_suggestions:
                                # Update criteria count and set suggested criteria
                                st.session_state["num_criteria"] = len(
                                    criteria_suggestions
                                )
                                for i, criterion in enumerate(criteria_suggestions):
                                    st.session_state[f"p{i}"] = criterion

                                # Step 2: Generate weights separately
                                weight_suggestions = get_ai_weight_suggestions(
                                    decision,
                                    options,
                                    criteria_suggestions,
                                    api_key,
                                    api_type,
                                    api_model,
                                )

                                if weight_suggestions:
                                    # Update weights based on suggestions
                                    for i, criterion in enumerate(criteria_suggestions):
                                        if criterion in weight_suggestions:
                                            st.session_state[f"w{i}"] = (
                                                weight_suggestions[criterion]
                                            )

                        if criteria_suggestions:

                            # Step 3: Generate scores
                            try:
                                score_suggestions = get_ai_score_suggestions(
                                    decision,
                                    options,
                                    criteria_suggestions,
                                    api_key,
                                    api_type,
                                    api_model,
                                )

                                if score_suggestions:
                                    # Update scores based on suggestions
                                    for opt_idx, option in enumerate(options):
                                        if option in score_suggestions:
                                            for param_idx, criterion in enumerate(
                                                criteria_suggestions
                                            ):
                                                if (
                                                    criterion
                                                    in score_suggestions[option]
                                                ):
                                                    score = score_suggestions[option][
                                                        criterion
                                                    ]
                                                    st.session_state[
                                                        f"score_{opt_idx}_{param_idx}"
                                                    ] = score
                            except Exception as e:
                                error_msg = str(e)
                                if "timeout" in error_msg.lower():
                                    st.warning(
                                        "⚠️ Score generation timed out. The request took too long. You can manually score the options or try again."
                                    )
                                else:
                                    st.warning(
                                        f"⚠️ Score generation failed: {error_msg}. You can manually score the options."
                                    )
                                logging.error(
                                    f"Score generation error: {error_msg}",
                                    exc_info=True,
                                )
                                score_suggestions = None

                            # Show debug info
                            with st.expander(
                                "🔍 Debug: View Prompts & API Responses", expanded=False
                            ):
                                st.markdown("**API Configuration:**")
                                st.write(f"- API Type: {api_type}")
                                st.write(f"- Model: {api_model}")
                                st.write(f"- Has OpenAI: {has_openai}")
                                st.write(f"- Has xAI: {has_xai}")
                                st.markdown("---")

                                st.markdown(
                                    "**Step 1: Criteria & Weight Generation (Combined)**"
                                )
                                st.write(f"- Criteria: {criteria_suggestions}")
                                st.write(f"- Weights: {weight_suggestions}")
                                if not weight_suggestions:
                                    st.error(
                                        "⚠️ No weights generated. Check console logs for details."
                                    )
                                st.markdown("---")

                                st.markdown("**Step 2: Score Generation**")
                                st.write(f"- Result: {score_suggestions}")
                                if not score_suggestions:
                                    st.error(
                                        "⚠️ No scores generated. Check console logs for details."
                                    )
                                st.markdown("---")

                                st.caption(
                                    "💡 Check the browser console or Streamlit logs for detailed API responses and parsing info."
                                )

                            # Mark as generated for this decision/options combination
                            st.session_state["ai_generated_for"] = decision_hash

                            # Show summary
                            if (
                                criteria_suggestions
                                and weight_suggestions
                                and score_suggestions
                            ):
                                st.success(
                                    "✨ AI generated criteria, weights, and scores!"
                                )
                            elif criteria_suggestions:
                                st.warning(
                                    "⚠️ Criteria generated, but weights or scores failed. Check debug info above."
                                )
                            st.rerun()
                        else:
                            st.error(
                                "⚠️ Could not generate AI suggestions. Please try again."
                            )
                    except Exception as e:
                        st.error(f"⚠️ Error generating AI suggestions: {str(e)}")
                        logging.error(
                            f"AI auto-generation error: {str(e)}", exc_info=True
                        )
            else:
                st.warning("⚠️ No API keys configured. AI suggestions unavailable.")

    # Initialize criteria count in session state
    if "num_criteria" not in st.session_state:
        # Use loaded criteria count if available, otherwise default to 3
        st.session_state["num_criteria"] = (
            len(loaded_criteria) if loaded_criteria else 3
        )

    # Default common criteria
    default_criteria = ["Cost", "Comfortability", "Time"]

    # Add/Remove criteria buttons - both on one line, Remove aligned to right
    # Wider middle column creates more visual separation
    col_add, col_spacer, col_remove = st.columns([1, 4, 1], gap="small")
    with col_add:
        if st.button("➕ Criterion", help="Add another criterion"):
            st.session_state["num_criteria"] += 1
            st.rerun()
    with col_spacer:
        st.write("            ")  # Empty spacer to push Remove button to the right
    with col_remove:
        if st.button(
            "➖ Criterion",
            help="Remove the last criterion",
            disabled=st.session_state["num_criteria"] <= 1,
        ):
            if st.session_state["num_criteria"] > 1:
                st.session_state["num_criteria"] -= 1
                st.rerun()

    # Determine number of columns (max 3 per row)
    num_criteria = st.session_state["num_criteria"]
    cols_per_row = min(3, num_criteria)
    num_rows = (num_criteria + cols_per_row - 1) // cols_per_row

    params, weights = [], []

    # Use loaded criteria if available, otherwise use defaults
    for i in range(num_criteria):
        row = i // cols_per_row
        col_idx = i % cols_per_row

        # Create columns for this row if needed
        if col_idx == 0:
            cols = st.columns(cols_per_row)

        with cols[col_idx]:
            # Always use session state value if it exists, otherwise use default
            if f"p{i}" in st.session_state:
                # Use session state value explicitly
                param = st.text_input(
                    f"Criteria {i+1}",
                    value=st.session_state[f"p{i}"],
                    key=f"p{i}",
                    placeholder="e.g., Income",
                    help=f"Name the {i+1}{'st' if i==0 else 'nd' if i==1 else 'rd'} factor that matters to you",
                )
            else:
                default_value = (
                    loaded_criteria[i]
                    if i < len(loaded_criteria)
                    else (default_criteria[i] if i < len(default_criteria) else "")
                )
                param = st.text_input(
                    f"Criteria {i+1}",
                    value=default_value,
                    key=f"p{i}",
                    placeholder="e.g., Income",
                    help=f"Name the {i+1}{'st' if i==0 else 'nd' if i==1 else 'rd'} factor that matters to you",
                )

            if f"w{i}" in st.session_state:
                # Use session state value explicitly
                weight = st.slider(
                    f"Weight",
                    0.0,
                    1.0,
                    value=st.session_state[f"w{i}"],
                    step=0.05,
                    key=f"w{i}",
                    help=f"How important is this criterion? (0 = not important, 1 = very important)",
                )
            else:
                default_weight = (
                    loaded_weights[i]
                    if i < len(loaded_weights)
                    else (1.0 / num_criteria)
                )
                weight = st.slider(
                    f"Weight",
                    0.0,
                    1.0,
                    default_weight,
                    0.05,
                    key=f"w{i}",
                    help=f"How important is this criterion? (0 = not important, 1 = very important)",
                )
            if param:
                st.caption(f"Current weight: {weight*100:.0f}%")
            params.append(param)
            weights.append(weight)

    # Normalize weights
    total_weight = sum(weights)
    weights = [w / total_weight if total_weight > 0 else 0 for w in weights]

# === STEP 3: Score Options ===
with st.container(border=True):
    st.markdown("### 🎯 Step 3: Score Each Option")
    st.caption(
        "💡 Rate how well each option performs on each criterion using a 1-10 scale (1 = poor, 5 = average, 10 = excellent)"
    )

    data = {"Option": options}
    for param in params:
        data[f"{param} (1-10)"] = []
        data[f"{param} (Weighted)"] = []

    # Organize scoring by option, with columns matching number of criteria
    if len(params) == 0:
        st.warning("⚠️ Please set at least one criterion in Step 2 to continue")
        st.stop()

    for opt_idx, opt in enumerate(options):
        with st.container():
            st.markdown(f"#### {opt}")
            # Create columns based on number of criteria
            score_cols = st.columns(len(params))
            for j, param in enumerate(params):
                with score_cols[j]:
                    # Always use session state value if it exists, otherwise use default
                    # Use opt_idx to ensure unique keys even if option names are duplicated
                    score_key = f"score_{opt_idx}_{j}"
                    if score_key in st.session_state:
                        # Use session state value explicitly
                        score = st.slider(
                            param,
                            1,
                            10,
                            value=st.session_state[score_key],
                            key=score_key,
                            help=f"Rate {opt} on {param} (1-10)",
                        )
                    else:
                        default_score = (
                            loaded_scores.get(opt, {}).get(param, 5)
                            if loaded_scores
                            else 5
                        )
                        score = st.slider(
                            param,
                            1,
                            10,
                            (
                                int(default_score)
                                if isinstance(default_score, (int, float))
                                else 5
                            ),
                            key=score_key,
                            help=f"Rate {opt} on {param} (1-10)",
                        )
                    # Show weighted score preview
                    weighted = score * weights[j]
                    st.caption(f"Weighted: {weighted:.2f}")
                    data[f"{param} (1-10)"].append(score)
                    data[f"{param} (Weighted)"].append(round(weighted, 2))
        st.markdown("---")

    df = pd.DataFrame(data)
    df["Total Score"] = df.filter(like="(Weighted)").sum(axis=1)
    df = df.sort_values("Total Score", ascending=False).reset_index(drop=True)

# === VISUAL RANKING ===
with st.container(border=True):
    st.markdown("### 🏆 Step 4: View Your Results")
    st.caption(
        "💡 Options are ranked by total weighted score. The higher the score, the better the option based on your criteria and weights."
    )
    fig = px.bar(
        df,
        x="Total Score",
        y="Option",
        orientation="h",
        text="Total Score",
        color="Total Score",
        color_continuous_scale="emrld",
        title="Your Best Path (Higher = Better)",
    )
    fig.update_traces(texttemplate="%{x:.1f}", textposition="outside")
    fig.update_layout(
        yaxis={"categoryorder": "total ascending"}, height=300 + len(options) * 50
    )
    st.plotly_chart(fig, width="stretch")

# === AI VERDICT & INSIGHTS ===
with st.expander("🤖 AI Verdict & Insights", expanded=False):
    st.caption(
        "💡 Let AI summarize your results, add context, and compare with the initial take."
    )

    # Custom prompt field for user context
    custom_prompt = st.text_area(
        "💬 Additional context (optional):",
        value=st.session_state.get("custom_ai_prompt", ""),
        placeholder="e.g., I'm risk-averse, or Consider my budget constraints, or What if I prioritize work-life balance?",
        help="Add any additional context, constraints, or questions for the AI to consider in the recommendation",
        key="custom_ai_prompt_input",
    )

    # Check available APIs
    try:
        available_apis = get_available_apis(st.secrets)
        has_openai = available_apis.get("openai", False)
        has_xai = available_apis.get("xai", False)
    except Exception:
        has_openai = False
        has_xai = False

    # API selection checkboxes for final recommendation
    preferred_api = None
    preferred_model = None
    if has_openai or has_xai:
        col_openai_rec, col_xai_rec = st.columns(2)

        with col_openai_rec:
            use_openai_rec = st.checkbox(
                "🤖 OpenAI GPT",
                value=st.session_state.get("use_openai_rec", has_openai),
                disabled=not has_openai,
                help=(
                    "Use OpenAI GPT for recommendation"
                    if has_openai
                    else "OpenAI API key not configured"
                ),
                key="use_openai_rec_checkbox",
            )
            st.session_state["use_openai_rec"] = use_openai_rec if has_openai else False

            if use_openai_rec and has_openai:
                openai_model_default = st.session_state.get(
                    "openai_model", DEFAULT_OPENAI_MODEL
                )
                openai_rec_model = st.selectbox(
                    "Model",
                    options=[opt["id"] for opt in OPENAI_MODEL_OPTIONS],
                    index=get_model_index(
                        openai_model_default,
                        OPENAI_MODEL_OPTIONS,
                        DEFAULT_OPENAI_MODEL,
                    ),
                    format_func=lambda m: get_model_display(m, OPENAI_MODEL_OPTIONS),
                    key="openai_rec_model_select",
                )
                st.session_state["openai_model"] = openai_rec_model

        with col_xai_rec:
            use_xai_rec = st.checkbox(
                "🤖 xAI Grok",
                value=st.session_state.get("use_xai_rec", has_xai),
                disabled=not has_xai,
                help=(
                    "Use xAI Grok for recommendation"
                    if has_xai
                    else "xAI API key not configured"
                ),
                key="use_xai_rec_checkbox",
            )
            st.session_state["use_xai_rec"] = use_xai_rec if has_xai else False

            if use_xai_rec and has_xai:
                xai_model_default = st.session_state.get("xai_model", DEFAULT_XAI_MODEL)
                xai_rec_model = st.selectbox(
                    "Model",
                    options=[opt["id"] for opt in XAI_MODEL_OPTIONS],
                    index=get_model_index(
                        xai_model_default,
                        XAI_MODEL_OPTIONS,
                        DEFAULT_XAI_MODEL,
                    ),
                    format_func=lambda m: get_model_display(m, XAI_MODEL_OPTIONS),
                    key="xai_rec_model_select",
                )
                st.session_state["xai_model"] = xai_rec_model

        # Determine which API to use based on checkboxes
        # Priority: xAI if both checked, then OpenAI, then fallback
        if st.session_state.get("use_xai_rec", False) and has_xai:
            preferred_api = "xai"
            preferred_model = st.session_state.get("xai_model", DEFAULT_XAI_MODEL)
        elif st.session_state.get("use_openai_rec", False) and has_openai:
            preferred_api = "openai"
            preferred_model = st.session_state.get("openai_model", DEFAULT_OPENAI_MODEL)
        else:
            preferred_api = None  # Fallback
            preferred_model = None

        if preferred_api is None:
            st.warning(
                "⚠️ No AI selected. Using fallback recommendation. Check at least one AI above."
            )
    else:
        st.warning(
            "⚠️ No API keys configured. Using fallback recommendation. Configure API keys in Streamlit secrets to get real AI recommendations."
        )
        preferred_api = None
        preferred_model = None

    # Get initial decision for comparison
    decision_hash = f"{decision}_{','.join(options)}"
    initial_decision_key = f"initial_decision_{decision_hash}"
    initial_decision = st.session_state.get(initial_decision_key, None)

    # Clear stored verdict if it belongs to a different decision/options set
    stored_verdict_key = st.session_state.get("ai_final_verdict_key")
    if stored_verdict_key and stored_verdict_key != decision_hash:
        st.session_state.pop("ai_final_verdict", None)
        st.session_state.pop("ai_final_verdict_key", None)
        st.session_state.pop("ai_comparison_result", None)

    stored_final_verdict = st.session_state.get("ai_final_verdict")
    stored_comparison = st.session_state.get("ai_comparison_result")

    if st.button("🤖 Get AI Verdict", type="primary", width="stretch"):
        # Get custom prompt from text area (submitted with button click)
        custom_prompt_value = custom_prompt.strip() if custom_prompt else None
        st.session_state["custom_ai_prompt"] = custom_prompt_value

        with st.spinner("Yes? is thinking..."):
            # Get final recommendation with custom prompt
            final_verdict = get_ai_recommendation(
                decision,
                options,
                df,
                params,
                weights,
                custom_prompt_value,
                preferred_api,
                preferred_model,
            )

            # Show final verdict
            st.session_state["ai_final_verdict"] = final_verdict
            st.session_state["ai_final_verdict_key"] = decision_hash

            # Show comparison if initial decision exists
            if initial_decision:
                # Get AI comparison if both APIs available
                if has_openai or has_xai:
                    with st.spinner("🤖 Analyzing differences..."):
                        try:
                            comparison_prompt = f"""
Initial AI Decision: {initial_decision}
Final AI Decision: {final_verdict}
Decision Question: {decision}
Options: {', '.join(options)}
Top Scored Option: {df.iloc[0]['Option']} (Score: {df.iloc[0]['Total Score']:.2f})

Compare the initial decision with the final decision. Did the structured analysis (criteria, weights, scores) confirm or contradict the initial assessment? What changed and why? Keep it concise (2-3 sentences).
"""
                            comparison_system = "You are a decision analysis expert. Compare initial vs final decisions and explain what changed."

                            comparison_api = (
                                preferred_api
                                if preferred_api
                                else ("openai" if has_openai else "xai")
                            )
                            comparison_key = (
                                st.secrets.get(comparison_api, {}).get("api_key")
                                if comparison_api == "openai"
                                else st.secrets.get("xai", {}).get("api_key")
                            )
                            if comparison_api == "openai":
                                comparison_model = (
                                    preferred_model
                                    if preferred_api == "openai" and preferred_model
                                    else st.session_state.get(
                                        "openai_model", DEFAULT_OPENAI_MODEL
                                    )
                                )
                            else:
                                comparison_model = (
                                    preferred_model
                                    if preferred_api == "xai" and preferred_model
                                    else st.session_state.get(
                                        "xai_model", DEFAULT_XAI_MODEL
                                    )
                                )

                            if comparison_api == "openai":
                                comparison_result = call_openai_gpt(
                                    comparison_key,
                                    comparison_prompt,
                                    comparison_system,
                                    model=comparison_model,
                                    max_tokens=200,
                                )
                            else:
                                comparison_result = call_xai_grok(
                                    comparison_key,
                                    comparison_prompt,
                                    comparison_system,
                                    model=comparison_model,
                                    max_tokens=200,
                                )

                            if comparison_result:
                                st.markdown("**🔍 Analysis:**")
                                st.session_state["ai_comparison_result"] = (
                                    comparison_result
                                )
                            else:
                                st.session_state["ai_comparison_result"] = None
                        except Exception as e:
                            logging.error(
                                f"Error getting comparison: {str(e)}", exc_info=True
                            )
                            st.session_state["ai_comparison_result"] = None
                else:
                    st.session_state["ai_comparison_result"] = None
            else:
                st.session_state["ai_comparison_result"] = None

            stored_final_verdict = st.session_state.get("ai_final_verdict")
            stored_comparison = st.session_state.get("ai_comparison_result")

    # Display stored results (if any)
    if stored_final_verdict:
        st.markdown("### 🎯 AI Verdict")
        st.info(stored_final_verdict)

        if initial_decision:
            st.markdown("---")
            st.markdown("### 📊 Decision Comparison")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**💭 Initial Take**")
                st.info(initial_decision)
            with col2:
                st.markdown("**🎯 Final Verdict**")
                st.info(stored_final_verdict)

            if stored_comparison:
                st.markdown("**🔍 Analysis:**")
                st.success(stored_comparison)
            else:
                st.caption(
                    "💡 Compare the two decisions above to see how structured analysis changed the recommendation."
                )

# === SAVE DECISION ===
with st.container(border=True):
    st.markdown("### 💾 Save Your Decision")
    if st.session_state["user_id"] is None:
        st.caption(
            "💡 Save temporarily (lost on refresh) or log in to save permanently. You can load it from the sidebar anytime."
        )
    else:
        st.caption(
            "💡 Save this decision to review later. You can load it from the sidebar anytime."
        )

    if st.button("💾 Save This Decision", width="stretch"):
        timestamp = datetime.now().strftime("%b %d, %Y")
        entry = (
            f"{decision} → **{df.iloc[0]['Option']}** ({df.iloc[0]['Total Score']:.1f})"
        )

        # Prepare scores dictionary for database from DataFrame
        # The DataFrame already has all the scores we need
        scores_dict = {}
        for opt_idx, opt in enumerate(options):
            scores_dict[opt] = {}
            for param_idx, param in enumerate(params):
                # Get score from DataFrame
                score_col = f"{param} (1-10)"
                score = float(df[df["Option"] == opt][score_col].iloc[0])
                scores_dict[opt][param] = score

        # Prepare decision data
        decision_data = {
            "timestamp": timestamp,
            "datetime": datetime.now().isoformat(),
            "decision": decision,
            "options": options,
            "criteria": params,
            "weights": weights,
            "winner": df.iloc[0]["Option"],
            "winner_score": float(df.iloc[0]["Total Score"]),
            "full_results": df.to_dict("records"),
            "scores": scores_dict,
        }

        if st.session_state["user_id"] is None:
            # Save temporarily to session state
            if "temp_decisions" not in st.session_state:
                st.session_state["temp_decisions"] = []
            st.session_state["temp_decisions"].append(decision_data)
            st.success(f"💾 Saved temporarily: {entry}")
            st.info(
                "💡 *This decision will be lost on refresh. Log in to save permanently.*"
            )
        else:
            # Save to database
            decision_id = db_save_decision(
                user_id=st.session_state["user_id"],
                decision=decision,
                options=options,
                criteria=params,
                weights=weights,
                scores=scores_dict,
                winner=df.iloc[0]["Option"],
                winner_score=float(df.iloc[0]["Total Score"]),
            )
            decision_data["id"] = decision_id
            st.success(f"✅ Saved permanently: {entry}")

        st.rerun()  # Refresh the app to update Past Decisions

# === FULL TABLE ===
with st.expander("📊 View Full Matrix"):
    # Format only numeric columns, excluding the Option column
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    st.dataframe(
        df.style.format("{:.2f}", subset=numeric_cols).background_gradient(
            cmap="Greens", subset=["Total Score"]
        )
    )

# === FOOTER ===
st.markdown("---")
st.caption(
    "Yes? • AI-Powered Decision Guide • Built to beat Darwin • [Deploy yours → streamlit.io](https://streamlit.io)"
)
