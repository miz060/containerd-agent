#!/bin/python3
import os
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

# Configuration - replace with your values
endpoint = "https://your-resource-name.openai.azure.com/"
deployment = "gpt-4o"

# Or use environment variables (recommended)
# endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
# deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")

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
