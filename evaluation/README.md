# Containerd Model Evaluation

This directory contains scripts and resources for evaluating the fine-tuned containerd model against the baseline GPT-4.1 model.

## Files

### Core Scripts
- `evaluate_models.py` - Main evaluation script that compares both models
- `quick_test.py` - Quick test script for rapid evaluation of a few questions
- `sample_questions.json` - Comprehensive set of containerd-related questions

### Usage

#### Quick Test
For a rapid evaluation with 3 questions:
```bash
cd /workspace/containerd-agent/evaluation
export AZURE_OPENAI_API_KEY=your_api_key_here
python3 quick_test.py
```

#### Full Evaluation
For comprehensive evaluation with all questions:
```bash
cd /workspace/containerd-agent/evaluation
export AZURE_OPENAI_API_KEY=your_api_key_here
python3 evaluate_models.py
```

#### Custom Evaluation
```bash
python3 evaluate_models.py \
    --questions custom_questions.json \
    --output-json my_results.json \
    --output-html my_report.html
```

## Model Endpoints

- **Fine-tuned Model**: `gpt-4-04-14`
- **Baseline Model**: `gpt-4.1-general`

## Evaluation Categories

The evaluation covers the following areas:
- **Basic Concepts**: Fundamental containerd knowledge
- **Architecture**: System design and components
- **CRI Integration**: Kubernetes Container Runtime Interface
- **Image Management**: Container image handling
- **Snapshotter**: Filesystem layer management
- **Troubleshooting**: Common issues and debugging
- **Performance**: Optimization and monitoring
- **Security**: Container isolation and security features
- **API Usage**: Go client programming
- **Plugins**: Extensibility and plugin system
- **Networking**: Container networking and CNI
- **Runtimes**: OCI runtime integration
- **Storage**: Persistent storage and volumes
- **Operations**: Production deployment and maintenance

## Output Files

### JSON Results (`evaluation_results.json`)
Raw evaluation data including:
- Question details and responses
- Token usage and response times
- Success/failure status
- Model configurations

### HTML Report (`evaluation_report.html`)
Human-readable report with:
- Summary statistics
- Side-by-side response comparisons
- Performance metrics
- Visual formatting for easy review

## Expected Improvements

The fine-tuned model should show improvements in:
- **Accuracy**: More precise technical details
- **Specificity**: containerd-specific terminology and concepts
- **Completeness**: Comprehensive coverage of topics
- **Practical Focus**: Actionable advice and code examples
- **Consistency**: Uniform quality across different question types

## Analysis Tips

When reviewing results, look for:
1. **Technical Accuracy**: Correct API usage, proper terminology
2. **Depth**: Detailed explanations vs. surface-level answers
3. **Containerd-specific Knowledge**: References to specific components, files, or workflows
4. **Code Examples**: Practical Go client code snippets
5. **Troubleshooting Quality**: Specific debugging steps and tools
6. **Performance Insights**: Optimization recommendations

## Environment Setup

Make sure you have:
```bash
pip install openai
export AZURE_OPENAI_API_KEY=your_api_key_here
```

## Rate Limiting

The scripts include 1-second delays between API calls to respect rate limits. For production use, consider implementing exponential backoff and retry logic.
