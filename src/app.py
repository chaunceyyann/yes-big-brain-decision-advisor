# app.py
import json
import os
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# === CONFIG ===
st.set_page_config(page_title="Yes? AI Decision Guide", page_icon="✅", layout="wide")

# File path for decisions storage
DECISIONS_FILE = "decisions.json"


# === MOCK AI (Replace with xAI / OpenAI later) ===
def get_ai_recommendation(decision, options, df, params, weights):
    top = df.iloc[0]
    prompt = f"""
    Decision: {decision}
    Options: {', '.join(options)}
    Criteria: {', '.join([f'{p} ({w*100:.0f}%)' for p, w in zip(params, weights)])}
    Winner: {top['Option']} with score {top['Total Score']:.2f}

    Give a confident, concise, human-sounding recommendation in 2-3 sentences.
    """
    # In real version: call xAI API here
    return f"**Yes? says:** Go with **{top['Option']}**. It crushes on your top priorities — {params[0]} and {params[1] if len(params)>1 else ''}. The numbers don’t lie."


# === APP ===
st.title("✅ Yes?")
st.markdown(
    "*The AI that turns 'maybe' into 'hell yes' — with math, visuals, and zero fluff.*"
)

# Welcome section for new users
if "has_seen_welcome" not in st.session_state:
    with st.expander("👋 Welcome! How does this work?", expanded=True):
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
        if st.button("Got it! Let's start", key="dismiss_welcome"):
            st.session_state["has_seen_welcome"] = True
            st.rerun()

# Sidebar: Mock Login + History
with st.sidebar:
    st.header("👤 Account")
    if st.checkbox("Enable Sync (Mock Login)", value=True):
        st.success("Synced across devices")
    else:
        st.warning("Offline mode")

    st.header("📜 Past Decisions")
    # Load decisions from local JSON file
    if os.path.exists(DECISIONS_FILE):
        try:
            with open(DECISIONS_FILE, "r") as f:
                all_decisions = json.load(f)
            # Display most recent 5 decisions
            if all_decisions:
                for idx, decision_data in enumerate(all_decisions[-5:]):
                    entry = f"{decision_data['decision']} → **{decision_data['winner']}** ({decision_data['winner_score']:.1f})"
                    # Create a button that covers both emoji and text
                    if st.button(
                        f"📋 {entry}",
                        key=f"load_{idx}_{len(all_decisions)}",
                        help=f"Load this decision",
                        use_container_width=True,
                    ):
                        # Store the decision to load in session state
                        st.session_state["decision_to_load"] = decision_data
                        st.session_state["show_load_confirm"] = True
            else:
                st.write("• No decisions saved yet")
        except (json.JSONDecodeError, KeyError) as e:
            st.write("• No valid decisions found")
    else:
        st.write("• No decisions saved yet")

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
st.markdown("---")
st.markdown("### 📝 Step 1: Define Your Decision & Options")

# New Decision button at the top
col_btn, col_info = st.columns([1, 4])
with col_btn:
    if st.button("🧠 New Decision", help="Clear all fields and start fresh"):
        # Clear all session state related to loading
        for key in ["load_decision", "decision_to_load", "show_load_confirm"]:
            if key in st.session_state:
                del st.session_state[key]
        st.success("Fresh start!")
        st.rerun()
with col_info:
    st.caption(
        "💡 Start by entering your decision question and listing all possible options"
    )

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
    del st.session_state["load_decision"]
else:
    loaded_decision = ""
    loaded_options = ""
    loaded_criteria = []
    loaded_weights = []
    loaded_scores = {}

col1, col2 = st.columns(2)
with col1:
    decision = st.text_input(
        "What are you deciding?",
        value=loaded_decision,
        placeholder="e.g., Quit job? Move cities? Buy Tesla?",
        help="Enter a clear question about what you're trying to decide",
    )
    if not decision:
        st.info("👆 Enter your decision question above to get started")
with col2:
    options_text = st.text_area(
        "List your options (one per line):",
        value=loaded_options,
        placeholder="Stay at current job\nSwitch to remote role\nStart freelance",
        height=120,
        help="Enter all possible options, one per line. Be comprehensive but realistic.",
    )
    if not options_text.strip():
        st.info("👆 List all your options above, one per line")

options = options_text.strip().splitlines()
options = [o.strip() for o in options if o.strip()]

if not options:
    st.stop()

# === STEP 2: Criteria + Weights ===
st.markdown("---")
st.markdown("### ⚖️ Step 2: Set Your Criteria & Weights")
st.caption(
    "💡 Criteria are the factors that matter to you. Weights determine how important each criterion is (they'll be normalized automatically)."
)

# Initialize criteria count in session state
if "num_criteria" not in st.session_state:
    # Use loaded criteria count if available, otherwise default to 3
    st.session_state["num_criteria"] = len(loaded_criteria) if loaded_criteria else 3

# Default common criteria
default_criteria = ["Cost", "Comfortability", "Time"]

# Add/Remove criteria buttons
col_add, col_remove, _ = st.columns([1, 1, 4])
with col_add:
    if st.button("➕ Add Criterion", help="Add another criterion"):
        st.session_state["num_criteria"] += 1
        st.rerun()
with col_remove:
    if st.button(
        "➖ Remove Criterion",
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
        default_value = (
            loaded_criteria[i]
            if i < len(loaded_criteria)
            else (default_criteria[i] if i < len(default_criteria) else "")
        )
        default_weight = (
            loaded_weights[i] if i < len(loaded_weights) else (1.0 / num_criteria)
        )
        param = st.text_input(
            f"Criteria {i+1}",
            value=default_value,
            key=f"p{i}",
            placeholder="e.g., Income",
            help=f"Name the {i+1}{'st' if i==0 else 'nd' if i==1 else 'rd'} factor that matters to you",
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
st.markdown("---")
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

for opt in options:
    with st.container():
        st.markdown(f"#### {opt}")
        # Create columns based on number of criteria
        score_cols = st.columns(len(params))
        for j, param in enumerate(params):
            with score_cols[j]:
                # Get loaded score if available
                default_score = (
                    loaded_scores.get(opt, {}).get(param, 5) if loaded_scores else 5
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
                    key=f"score_{opt}_{j}",
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
st.markdown("---")
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
st.plotly_chart(fig, use_container_width=True)

# === AI RECOMMENDATION ===
st.markdown("---")
st.markdown("### 🤖 Get AI Recommendation")
st.caption("💡 Get a confident, human-sounding recommendation based on your scores")

if st.button("🤖 Get AI Verdict", type="primary", use_container_width=True):
    with st.spinner("Yes? is thinking..."):
        verdict = get_ai_recommendation(decision, options, df, params, weights)
        st.info(verdict)

# === SAVE DECISION ===
st.markdown("---")
st.markdown("### 💾 Save Your Decision")
st.caption(
    "💡 Save this decision to review later. You can load it from the sidebar anytime."
)

if st.button("💾 Save This Decision", use_container_width=True):
    timestamp = datetime.now().strftime("%b %d, %Y")
    entry = f"{decision} → **{df.iloc[0]['Option']}** ({df.iloc[0]['Total Score']:.1f})"

    # Save to local file
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
    }

    # Load existing decisions or create new list
    if os.path.exists(DECISIONS_FILE):
        with open(DECISIONS_FILE, "r") as f:
            all_decisions = json.load(f)
    else:
        all_decisions = []

    # Append new decision
    all_decisions.append(decision_data)

    # Save back to file
    with open(DECISIONS_FILE, "w") as f:
        json.dump(all_decisions, f, indent=2)

    st.success(f"Saved: {entry}")
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
