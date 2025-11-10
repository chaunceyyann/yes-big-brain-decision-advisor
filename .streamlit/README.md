# Streamlit Secrets Configuration

## Local Development

1. **Copy the example file:**
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

## Streamlit Cloud

1. Go to your Streamlit Cloud app dashboard
2. Click "Settings" → "Secrets"
3. Add API keys (at least one is recommended):
   ```toml
   # OpenAI GPT API (optional)
   [openai]
   api_key = "sk-your-actual-openai-api-key-here"

   # xAI Grok API (optional)
   [xai]
   api_key = "xai-your-actual-api-key-here"
   ```
4. Save and redeploy your app

## Getting API Keys

### OpenAI GPT API Key
1. Sign up at [platform.openai.com](https://platform.openai.com)
2. Go to API keys section
3. Generate a new API key
4. Copy the key and add it to your secrets configuration

### xAI Grok API Key
1. Sign up at [x.ai](https://x.ai)
2. Go to your account settings
3. Generate an API key
4. Copy the key and add it to your secrets configuration

## Security Notes

- ⚠️ **Never commit** `.streamlit/secrets.toml` to git
- ✅ The file is already in `.gitignore`
- ✅ Use environment variables in production if possible
- ✅ Rotate your API keys regularly
