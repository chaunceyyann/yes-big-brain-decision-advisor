# Deployment Guide

## Streamlit Cloud Deployment

### Prerequisites

1. **Streamlit Cloud Account**: Sign up at [share.streamlit.io](https://share.streamlit.io)
2. **GitHub Repository**: Ensure your code is pushed to GitHub

### Setup Steps

1. **Connect Repository**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click "New app"
   - Select your GitHub repository: `chaunceyyann/yes-big-brain-decision-advisor`
   - Choose branch: `main`
   - Set main file path: `src/app.py`
   - **Important**: Ensure `requirements.txt` is in the root directory (it should be automatically detected)
   - If dependencies aren't installing, try:
     - Redeploy the app (click "Reboot app" in Streamlit Cloud dashboard)
     - Check that `requirements.txt` is in the root directory
     - Verify the file format is correct (one package per line)

2. **Configure API Keys** (for AI recommendations)
   - In Streamlit Cloud dashboard, go to "Settings" → "Secrets"
   - Add API keys in TOML format (at least one is recommended):
     ```toml
     # OpenAI GPT API (optional)
     [openai]
     api_key = "sk-your-actual-openai-api-key-here"

     # xAI Grok API (optional)
     [xai]
     api_key = "xai-your-actual-api-key-here"
     ```
   - **Getting API keys:**
     - **OpenAI GPT:** Sign up at [platform.openai.com](https://platform.openai.com), go to API keys section
     - **xAI Grok:** Sign up at [x.ai](https://x.ai), go to your account settings, generate an API key
   - **Note:**
     - If both APIs are configured, you can choose which one to use in the app
     - If only one is configured, it will be used automatically
     - If no API keys are configured, the app will use a fallback mock recommendation

3. **Deploy**
   - Click "Deploy" - Streamlit Cloud will automatically deploy your app
   - The app will be available at: `https://your-app-name.streamlit.app`

### Releases

- Deploy from `main` (trunk-based)
- Cut production releases with annotated tags (`v1.0.0`, etc.)

### Local Development Setup

1. **Create secrets file:**
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```

2. **Add your API keys:**
   Edit `.streamlit/secrets.toml` and replace the placeholder keys with your actual API keys:
   ```toml
   # OpenAI GPT API (optional)
   [openai]
   api_key = "sk-your-actual-openai-api-key-here"

   # xAI Grok API (optional)
   [xai]
   api_key = "xai-your-actual-api-key-here"
   ```
   - At least one API key should be configured for AI recommendations
   - If both are configured, you can choose which one to use in the app

3. **The secrets file is gitignored** - it won't be committed to the repository.

### File Structure

```
yes-big-brain-decision-advisor/
├── src/
│   └── app.py              # Main Streamlit app
├── requirements.txt         # Python dependencies
├── streamlit.toml          # Streamlit configuration
└── .streamlit/
    ├── secrets.toml        # Local secrets (not committed)
    ├── secrets.toml.example # Example secrets file
    └── README.md           # Secrets setup instructions
```

### Notes

- `decisions.json` is stored locally per user session on Streamlit Cloud
- For persistent storage across sessions, consider using Streamlit's session state or external storage (S3, database)
- Streamlit Cloud automatically redeploys on push to the connected branch

## Future: Production Deployment Pipeline

A separate deployment pipeline module will be created for production deployments (AWS, etc.).
