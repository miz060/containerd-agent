# Go Module Dependency Analysis and Q&A Data Generation

This project analyzes Go module dependencies in the containerd codebase and generates high-quality training data for fine-tuning AI assistants.

## Strategy
We extract both internal and external Go modules, along with the files that define and use them. For each module, we collect metadata about its relationships and usage patterns. This structured dependency information is used to prompt Azure OpenAI to generate diverse, technical question-answer pairs that reflect real-world developer inquiries about module roles, integration points, and usage within containerd. This approach ensures the resulting dataset is highly relevant for training an expert assistant on containerd’s architecture and codebase.

## Features
- Visualizes module and file dependencies as a graph (see below)
- Distinguishes internal/external modules and files by color and shape
- Generates Q&A pairs for fine-tuning using Azure OpenAI

## Example Dependency Graph

![Dependency Graph](dependencies_graph.png)

### Graph

- **Blue ellipses**: Internal Go modules (defined within the containerd repository)
- **Orange ellipses**: External Go modules (third-party dependencies)
- **Green boxes**: Go source files
- **Edges**:
  - **From file to module**: The file imports or uses the module
  - **From module to file**: The file defines or implements the module


## Usage

- **Generate Q&A data for fine-tuning with Azure OpenAI:**
  ```bash
  python3 generate_azure_openai_training_dependencies_data.py \
    --repo-path /path/to/containerd \
    --azure-endpoint <YOUR_AZURE_OPENAI_ENDPOINT> \
    --azure-deployment <YOUR_DEPLOYMENT_NAME> \
    --num-modules 10 \
    --max-qa-per-module 3 \
    --output-jsonl output/containerd_module_qa.jsonl
  ```
  - Use `--all-modules` to generate Q&A for all modules.
  - The output will be a JSONL file suitable for fine-tuning.

- **Run the analysis and graph generation:**
  ```bash
  python3 create_dependencies_graph.py --repo-path /path/to/containerd --plot-graph --graph-output dependencies_graph.png
  ```

---
