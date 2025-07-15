# Azure OpenAI Training Data 5. **Generate training data**:
   ```bash
   # Small test with rate limiting (3 files per minute)
   python3 code-scanner/generate_azure_openai_training_data.py --max-files 10 --max-qa-per-file 3 --max-files-per-minute 3
   
   # Production run with TPM quota respect (6 files per minute for 100K TPM)
   python3 code-scanner/generate_azure_openai_training_data.py --max-files 500 --max-qa-per-file 12 --max-files-per-minute 6
   ```r

This system generates high-quality fine-tuning data for Azure OpenAI by analyzing code repositories. The `code-scanner/` folder contains scripts that use Azure OpenAI GPT-4 to create training data from code content - currently configured for the containerd repository but can be adapted for any code repository.

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
   python3 code-scanner/test_azure_openai_generator.py
   ```

5. **Generate training data**:
   ```bash
   # Small test with rate limiting (3 files per minute)
   python3 code-scanner/generate_azure_openai_training_data.py --max-files 10 --max-qa-per-file 3 --max-files-per-minute 3
   
   # Production run with TPM quota respect (6 files per minute for 100K TPM)
   python3 code-scanner/generate_azure_openai_training_data.py --max-files 500 --max-qa-per-file 12 --max-files-per-minute 6
   ```

6. **Full repository processing (long-running job)**:
   ```bash
   # Process all containerd files safely in background (~2.5 hours)
   nohup python3 -u code-scanner/generate_azure_openai_training_data.py \
     --max-files 855 \
     --max-qa-per-file 5 \
     --max-files-per-minute 6 \
     --output-path output/containerd_full_training_data.jsonl \
     > output/generation.log 2>&1 &
   
   echo "Background job started. PID: $!"
   ```

## What's Included

- **`code-scanner/`**: Scripts for AI-powered training data generation from code repositories
- **`static/`**: Template-based training data generation (faster, less detailed)
- **`output/`**: Generated JSONL files and metadata
- **Templates**: Safe configuration templates (`.env.template`, `azure_openai_config.template.txt`)

## Security

All personal configuration is excluded from git commits via `.gitignore`. The system uses Azure AD authentication for secure access to Azure OpenAI.
