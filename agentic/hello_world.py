#!/bin/python3
import os
from openai import AzureOpenAI
from azure.identity import AzureCliCredential, get_bearer_token_provider

# Get configuration from environment variables
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

if not endpoint:
    raise ValueError(
        "AZURE_OPENAI_ENDPOINT environment variable is required.\n"
        "Set it with: export AZURE_OPENAI_ENDPOINT='https://your-resource-name.openai.azure.com/'"
    )

# Use AzureCliCredential instead of DefaultAzureCredential for consistency
token_provider = get_bearer_token_provider(AzureCliCredential(), "https://cognitiveservices.azure.com/.default")

client = AzureOpenAI(
    azure_endpoint=endpoint,
    azure_ad_token_provider=token_provider,
    api_version="2024-02-01",
)

completion = client.chat.completions.create(
    model=deployment,
    messages=[
        {
            "role": "user",
            "content": "Why is the sky blue?"
        }
    ],
)

print(completion.to_json())