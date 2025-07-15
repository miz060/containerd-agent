# Containerd Agent Training Data Generator

This system generates high-quality fine-tuning data for Azure OpenAI by analyzing the containerd repository. It creates comprehensive training datasets from both source code and GitHub issues using Azure OpenAI GPT-4o. The generated data is specifically formatted for supervised fine-tuning of Azure OpenAI models to create containerd domain experts.

**Note**: While configured for containerd, this system can be easily adapted to work with any code repository by changing the repository path and adjusting the priority scoring logic.

## Quick Setup

1. **Prerequisites**: 
   - Azure OpenAI resource with GPT-4o deployment
   - Azure CLI installed and configured (`az login`)
   - Python 3.8+ 
   - GitHub token (for issue mining)

2. **Install dependencies**:
   ```bash
   cd /workspace/containerd-agent
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.template .env
   # Edit .env with your Azure OpenAI endpoint, deployment, and GitHub token
   ```

4. **Test the setup**:
   ```bash
   python3 code-scanner/test_code_training_generator.py
   ```

## Usage

### Code Training Data Generation

Generate training data from containerd source code:

```bash
# Test run (10 Q&A pairs from 5 files)
python3 code-scanner/generate_code_training_data.py \
  --max-files 5 --max-qa-entries 10 --max-files-per-minute 3

# Production run (6,000 Q&A pairs from 855 files, ~$180, 5 hours)
python3 code-scanner/generate_code_training_data.py \
  --max-files 855 --max-qa-entries 6000 --max-files-per-minute 6

# Maximum coverage (12,000 Q&A pairs, ~$360, 10 hours)
python3 code-scanner/generate_code_training_data.py \
  --max-files 855 --max-qa-entries 12000 --max-files-per-minute 6
```

### GitHub Issues Training Data Generation

Generate training data from GitHub issues:

```bash
# Step 1: Fetch and prioritize issues (one-time)
python3 issue-miner/prioritize_github_issues.py

# Step 2: Generate training data (3,000 Q&A pairs, ~$25, 3 hours)
python3 issue-miner/generate_issue_training_data.py \
  --max-qa-entries 3000 --max-issues-per-minute 6
```

### Background Processing

For long-running jobs:

```bash
# Code training (background)
nohup python3 -u code-scanner/generate_code_training_data.py \
  --max-files 855 --max-qa-entries 12000 --max-files-per-minute 6 \
  > output/code_generation.log 2>&1 &

# Issue training (background)
nohup python3 -u issue-miner/generate_issue_training_data.py \
  --max-qa-entries 3000 --max-issues-per-minute 6 \
  > output/issue_generation.log 2>&1 &
```

## Key Features

### Smart Q&A Allocation
- **Priority-based**: Higher priority items get more Q&A pairs
- **Quota management**: Total Q&A pairs distributed according to global quota
- **Fair distribution**: Lower priority items still get at least 1 Q&A pair
- **Per-file limits**: Prevents any single file from dominating (max 20 Q&A per file)

### Rate Limiting & Cost Control
- **TPM-aware**: Respects Azure OpenAI 100K TPM quotas
- **Cost estimation**: Real-time cost tracking and estimates
- **Efficient processing**: 6 files/issues per minute for stable processing

### Security & Configuration
- **Environment variables**: All sensitive config in `.env` (git-excluded)
- **Azure AD authentication**: Uses Azure CLI credentials
- **No hardcoded secrets**: All endpoints and tokens via environment variables

## Components

- **`code-scanner/`**: AI-powered training data from Go source files
- **`issue-miner/`**: GitHub issues mining and training data generation
- **`utils/`**: Shared Q&A allocation and processing utilities
- **`output/`**: Generated JSONL files and metadata

## Cost Estimation

| Component | Q&A Pairs | Cost | Time |
|-----------|-----------|------|------|
| Issue data | 3,000 | ~$25 | 3 hours |
| Code data (balanced) | 6,000 | ~$180 | 5 hours |
| Code data (maximum) | 12,000 | ~$360 | 10 hours |
| **Combined maximum** | **15,000** | **~$385** | **13 hours** |

## Output Format

Generated training data is in JSONL format compatible with Azure OpenAI fine-tuning:

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are an expert in containerd..."
    },
    {
      "role": "user", 
      "content": "How do I configure containerd snapshotter?"
    },
    {
      "role": "assistant",
      "content": "To configure containerd snapshotter..."
    }
  ],
  "metadata": {
    "source": "code_file",
    "file_path": "client/client.go",
    "priority_score": 32.0
  }
}
```

## Monitoring Progress

Check logs for real-time progress:

```bash
# Watch current generation
tail -f output/code_generation.log
tail -f output/issue_generation.log

# Check allocation summary
grep "Q&A Allocation Summary" output/*.log
```

This system creates comprehensive, high-quality training data for fine-tuning Azure OpenAI models on containerd expertise.
