# Containerd Agent Directory Structure

```
containerd-agent/
├── README.md                           # Main documentation
├── requirements.txt                    # Python dependencies
├── .env.template                       # Environment template (safe to commit)
├── .gitignore                         # Git ignore file (excludes personal config)
├── 
├── code-scanner/                      # Azure OpenAI-powered code analysis
│   ├── generate_azure_openai_training_data.py  # Main generator
│   ├── test_azure_openai_generator.py          # Test script
│   └── hello_world.template.py                 # Simple test template
├── 
├── issue-miner/                       # GitHub issues training data generation
│   ├── fetch_github_issues.py         # Fetch and prioritize GitHub issues
│   └── generate_issue_training_data.py # Generate training data from issues
├── 
└── output/                            # Generated training data
    ├── *.jsonl                        # Training data files
    ├── *.metadata.json               # Generation metadata
    └── *.txt                         # Reports and logs
```

## Key Components

### `/code-scanner/` - Source Code Analysis
- Uses Azure OpenAI GPT-4 to analyze Go source code
- Generates Q&A pairs about functions, architecture, and usage
- Can process 500+ files to create comprehensive datasets

### `/issue-miner/` - GitHub Issues Analysis  
- Fetches and prioritizes GitHub issues from last 2 years
- Uses Azure OpenAI GPT-4 to extract training data from issue discussions
- Focuses on bugs, questions, and feature requests with maintainer responses

### `/output/` - Generated Results
- JSONL files ready for Azure OpenAI fine-tuning
- Metadata tracking generation details and costs
- Analysis reports and logs

### Configuration
- `.env.template` - Copy to `.env` and configure with your Azure OpenAI details
- All personal configuration excluded from git via `.gitignore`
- Uses Azure AD authentication for secure access

## Usage

### Code Analysis
```bash
# Setup
cp .env.template .env
# Edit .env with your Azure OpenAI endpoint

# Generate training data from source code
python3 code-scanner/generate_azure_openai_training_data.py --max-files 500
```

### GitHub Issues Analysis
```bash
# Fetch and prioritize issues
python3 issue-miner/prioritize_github_issues.py --max-issues 200

# Generate training data from issues
python3 issue-miner/generate_issue_training_data.py --max-issues 100
```
