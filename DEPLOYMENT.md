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
   - Choose branch: `dev` (for development deployment)
   - Set main file path: `src/app.py`

2. **Configure Environment Variables** (if needed)
   - In Streamlit Cloud dashboard, go to "Settings" → "Secrets"
   - Add any required secrets (e.g., API keys for future AI integration):
     ```
     OPENAI_API_KEY=your_key_here
     XAI_API_KEY=your_key_here
     ```

3. **Deploy**
   - Click "Deploy" - Streamlit Cloud will automatically deploy your app
   - The app will be available at: `https://your-app-name.streamlit.app`

### Development vs Production

- **Development**: Deploy from `dev` branch
- **Production**: Deploy from `main` branch (via release branches)

### File Structure

```
yes-big-brain-decision-advisor/
├── src/
│   └── app.py              # Main Streamlit app
├── requirements.txt         # Python dependencies
├── streamlit.toml          # Streamlit configuration
└── .streamlit/
    └── secrets.toml        # Local secrets (not committed)
```

### Notes

- `decisions.json` is stored locally per user session on Streamlit Cloud
- For persistent storage across sessions, consider using Streamlit's session state or external storage (S3, database)
- Streamlit Cloud automatically redeploys on push to the connected branch

## Future: Production Deployment Pipeline

A separate deployment pipeline module will be created for production deployments (AWS, etc.).
