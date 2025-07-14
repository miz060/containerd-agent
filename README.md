# Azure OpenAI Training Data Generator

This system generates high-quality fine-tuning data for Azure OpenAI by analyzing code repositories. The `agentic/` folder contains scripts that use Azure OpenAI GPT-4 to create training data from code content - currently configured for the containerd repository but can be adapted for any code repository.

## Quick Setup

1. **Prerequisites**: Azure OpenAI resource with GPT-4o deployment, Azure CLI, Python 3.8+

2. **Install dependencies**:
   ```bash
   cd /workspace/containerd-agent
   pip install -r requirements.txt
   ```

3. **Configure Azure OpenAI**:
   ```bash
   # Login to Azure
   az login
   
   # Copy template and edit with your values
   cp .env.template .env
   # Edit .env with your actual Azure OpenAI endpoint and deployment
   ```

4. **Test the setup**:
   ```bash
   python3 agentic/test_azure_openai_generator.py
   ```

5. **Generate training data**:
   ```bash
   # Small test (2 files)
   python3 agentic/generate_azure_openai_training_data.py --max-files 2 --max-qa-per-file 3
   
   # Production run (500 files)
   python3 agentic/generate_azure_openai_training_data.py --max-files 500 --max-qa-per-file 12
   ```

## What's Included

- **`agentic/`**: Scripts for AI-powered training data generation from code repositories
- **`static/`**: Template-based training data generation (faster, less detailed)
- **`output/`**: Generated JSONL files and metadata
- **Templates**: Safe configuration templates (`.env.template`, `azure_openai_config.template.txt`)

## Security

All personal configuration is excluded from git commits via `.gitignore`. The system uses Azure AD authentication for secure access to Azure OpenAI.
