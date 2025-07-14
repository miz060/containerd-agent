#!/bin/bash
# Load environment variables from .env file
# Usage: source load_env.sh

if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ Environment variables loaded"
    echo "AZURE_OPENAI_ENDPOINT: $AZURE_OPENAI_ENDPOINT"
    echo "AZURE_OPENAI_DEPLOYMENT: $AZURE_OPENAI_DEPLOYMENT"
else
    echo "❌ .env file not found."
    echo "Please create it from the template:"
    echo "  cp .env.template .env"
    echo "  # Edit .env with your actual Azure OpenAI configuration"
fi
