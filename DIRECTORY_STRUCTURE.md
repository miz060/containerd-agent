# Containerd Agent Directory Structure

```
containerd-agent/
├── README.md                           # Main documentation
├── requirements.txt                    # Python dependencies
├── .env.template                       # Environment template (safe to commit)
├── .gitignore                         # Git ignore file (excludes personal config)
├── 
├── code-scanner/                          # Azure OpenAI-powered training data generation
│   ├── generate_azure_openai_training_data.py  # Main generator
│   ├── test_azure_openai_generator.py          # Test script
│   └── hello_world.template.py                 # Simple test template
├── 
└── output/                            # Generated training data
    ├── *.jsonl                        # Training data files
    ├── *.metadata.json               # Generation metadata
    └── *.txt                         # Reports and logs
```

## Key Components

### `/code-scanner/` - Training Data Generation
- Uses Azure OpenAI GPT-4 to analyze code repositories
- Generates high-quality Q&A pairs for fine-tuning
- Can process 500+ files to create comprehensive datasets

### `/output/` - Generated Results
- JSONL files ready for Azure OpenAI fine-tuning
- Metadata tracking generation details and costs
- Analysis reports and logs

### Configuration
- `.env.template` - Copy to `.env` and configure with your Azure OpenAI details
- All personal configuration excluded from git via `.gitignore`
- Uses Azure AD authentication for secure access

## Usage

```bash
# Setup
cp .env.template .env
# Edit .env with your Azure OpenAI endpoint

# Generate training data
python3 code-scanner/generate_azure_openai_training_data.py --max-files 500
```
