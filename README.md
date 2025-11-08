# ✅ Yes? - Big Brain Decision Advisor

**The AI that turns 'maybe' into 'hell yes' — with math, visuals, and zero fluff.**

![PR Checks](https://github.com/chaunceyyann/yes-big-brain-decision-advisor/actions/workflows/pr-checks.yaml/badge.svg)

## Goal

Yes? is a decision-making tool that helps you make better choices by combining structured analysis with AI-powered recommendations. Instead of relying on gut feelings, Yes? helps you:

1. **Define your decision clearly** — What are you trying to decide?
2. **List all options** — What are your choices?
3. **Set criteria & weights** — What matters most to you? (e.g., Cost, Comfortability, Time)
4. **Score each option** — Rate how well each option performs on each criterion (1-10)
5. **Get ranked results** — See which option scores highest based on your priorities
6. **Receive AI recommendations** — Get a confident, human-sounding recommendation
7. **Save & revisit** — Keep a history of your decisions for future reference

## Features

- 📊 **Visual ranking** with interactive bar charts
- ⚖️ **Weighted scoring** system that respects your priorities
- 🤖 **AI-powered recommendations** (ready for xAI/OpenAI integration)
- 💾 **Decision history** — Save and load past decisions
- 📱 **Clean, intuitive UI** built with Streamlit

## Getting Started

### Prerequisites

- Python 3.13+
- pip

### Installation

1. **Clone the repository**
   ```bash
   git clone git@github.com:chaunceyyann/yes-big-brain-decision-advisor.git
   cd yes-big-brain-decision-advisor
   ```

2. **Install dependencies**
   ```bash
   pip install streamlit pandas numpy plotly
   ```

3. **Run the app**
   ```bash
   streamlit run src/app.py
   ```

The app will open in your browser at `http://localhost:8501`

## How It Works

1. Enter your decision question (e.g., "Which car should I buy?")
2. List your options (one per line)
3. Set up to 3 criteria with weights (defaults: Cost, Comfortability, Time)
4. Score each option against each criterion (1-10 scale)
5. View the ranked results and get an AI recommendation
6. Save your decision to review later

## Decision Storage

All decisions are saved locally in `decisions.json` in the project root. You can:
- View past decisions in the sidebar
- Click the 📋 button to load a previous decision
- All data persists across sessions

## Future Enhancements

- [ ] Integrate xAI/OpenAI API for real AI recommendations
- [ ] Support for more than 3 criteria
- [ ] Export decisions to CSV/PDF
- [ ] Cloud sync for decision history
- [ ] Decision comparison tool

## Contributing

This is a personal project, but suggestions and improvements are welcome!
