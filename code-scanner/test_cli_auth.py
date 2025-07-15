#!/usr/bin/env python3
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

print(f"Using endpoint: {endpoint}")
print(f"Using deployment: {deployment}")

# Force use of Azure CLI credentials instead of DefaultAzureCredential
try:
    cli_credential = AzureCliCredential()
    token = cli_credential.get_token("https://cognitiveservices.azure.com/.default")
    
    # Decode the token to see what principal it's using
    import base64
    import json
    payload = token.token.split('.')[1]
    payload += '=' * (4 - len(payload) % 4)
    decoded = base64.b64decode(payload)
    token_info = json.loads(decoded)
    
    print(f"CLI Token Principal ID: {token_info.get('oid', 'Not found')}")
    print(f"CLI Token UPN: {token_info.get('upn', 'Not found')}")
    
    token_provider = get_bearer_token_provider(cli_credential, "https://cognitiveservices.azure.com/.default")
    
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
        ]
    )
    
    print("✅ Success! Response:")
    print(completion.choices[0].message.content)
    
except Exception as e:
    print(f"❌ Error: {e}")
