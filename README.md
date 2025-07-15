# Azure OpenAI Training Data 5. **Generate training data**:
   ```bash
   # Small test with rate limiting (3 files per minute)
   python3 code-scanner/generate_code_training_data.py --max-files 10 --max-qa-entries 3 --max-files-per-minute 3
   
   # Production run with TPM quota respect (6 files per minute for 100K TPM)
   python3 code-scanner/generate_code_training_data.py --max-files 500 --max-qa-entries 12 --max-files-per-minute 6
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
   python3 code-scanner/generate_code_training_data.py --max-files 10 --max-qa-entries 3 --max-files-per-minute 3
   
   # Production run with TPM quota respect (6 files per minute for 100K TPM)
   python3 code-scanner/generate_code_training_data.py --max-files 500 --max-qa-entries 12 --max-files-per-minute 6
   ```

6. **Full repository processing (long-running job)**:
   ```bash
   # Process all containerd files safely in background (~2.5 hours)
   nohup python3 -u code-scanner/generate_code_training_data.py \
     --max-files 855 \
     --max-qa-entries 5 \
     --max-files-per-minute 6 \
     --output-path output/containerd_full_training_data.jsonl \
     > output/generation.log 2>&1 &
   
   echo "Background job started. PID: $!"
   ```

## GitHub Issues Training Data Generation

Generate training data from GitHub issues using the same Azure OpenAI approach:

### 1. **Fetch GitHub Issues**:
```bash
# Fetch ALL issues from last 2 years (prioritized by bugs, questions, maintainer responses)
python3 issue-miner/prioritize_github_issues.py --output-path output/github_issues_metadata.json

# Or limit to top 500 issues
python3 issue-miner/prioritize_github_issues.py --max-issues 500 --output-path output/github_issues_metadata.json
```

### 2. **Generate Training Data from Issues**:
```bash
# Small test (10 issues)
python3 issue-miner/generate_issue_training_data.py --max-issues 10 --max-issues-per-minute 3

# Production run (100 issues)
python3 issue-miner/generate_issue_training_data.py --max-issues 100 --max-issues-per-minute 6
```

### 3. **Combined approach** (recommended for comprehensive training):
```bash
# First fetch issues
python3 issue-miner/prioritize_github_issues.py --max-issues 200

# Then generate training data
python3 issue-miner/generate_issue_training_data.py --max-issues 100
```

## Q&A Allocation System

The system now uses a unified Q&A allocation utility (`utils/qa_allocation.py`) that ensures:

1. **Priority-based allocation**: Higher priority items get more Q&A pairs
2. **Quota management**: Total Q&A pairs are distributed according to a global quota
3. **Fair distribution**: Lower priority items still get at least 1 Q&A pair
4. **Validation**: Allocation constraints are validated before processing

### Usage in Issue-Miner

The issue-miner uses `calculate_qa_allocation()` to allocate Q&A pairs based on issue priority scores:

```python
qa_allocation = calculate_qa_allocation(
    items=issues,
    max_qa_entries=max_qa_entries,
    priority_field="priority_score",
    id_field="number"
)
```

### Usage in Code-Scanner

The code-scanner uses `calculate_file_qa_allocation()` for file-based allocation with additional per-file limits:

```python
qa_allocation = calculate_file_qa_allocation(
    files_data=files_for_allocation,
    max_qa_entries=max_qa_entries,
    max_qa_per_file=20,
    priority_field='priority_score',
    file_path_field='path'
)
```

### Key Features

- **Weighted distribution**: Q&A pairs are allocated proportionally to priority scores
- **Minimum guarantees**: Each item gets at least 1 Q&A pair (if quota allows)
- **Maximum limits**: Per-file limits prevent any single file from dominating
- **Validation**: Built-in validation ensures constraints are met
- **Debugging**: Detailed allocation summaries for monitoring

## What's Included

- **`code-scanner/`**: Scripts for AI-powered training data generation from code repositories
- **`issue-miner/`**: Scripts for mining GitHub issues and generating training data from issue conversations
- **`static/`**: Template-based training data generation (faster, less detailed)
- **`output/`**: Generated JSONL files and metadata
- **Templates**: Safe configuration templates (`.env.template`, `azure_openai_config.template.txt`)

## Security

All personal configuration is excluded from git commits via `.gitignore`. The system uses Azure AD authentication for secure access to Azure OpenAI.
