#!/usr/bin/env python3
"""
Azure OpenAI-powered training data generator for containerd repository.
Generates high-quality JSONL training data using Azure OpenAI to analyze Go code.
"""

import os
import json
import argparse
import re
import time
import random
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from collections import defaultdict

# Azure OpenAI imports
from openai import AzureOpenAI
from azure.identity import AzureCliCredential, get_bearer_token_provider

@dataclass
class FileInfo:
    path: str
    package: str
    size: int
    function_count: int
    has_structs: bool
    has_interfaces: bool
    has_consts: bool
    complexity_score: float
    priority_score: float

class AzureOpenAITrainingDataGenerator:
    def __init__(self, 
                 repo_path: str = "/workspace/upstream/containerd",
                 output_path: str = "/workspace/containerd-agent/output/containerd_training_data_azure.jsonl",
                 max_files: int = 500,  # Increased from 50
                 max_qa_per_file: int = 12,  # Increased for better coverage
                 azure_endpoint: str = None,
                 azure_deployment: str = "gpt-4o",
                 batch_size: int = 10):
        
        self.repo_path = Path(repo_path)
        self.output_path = Path(output_path)
        self.max_files = max_files
        self.max_qa_per_file = max_qa_per_file
        self.batch_size = batch_size
        
        # Azure OpenAI configuration
        self.azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_deployment = azure_deployment or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        
        if not self.azure_endpoint:
            raise ValueError(
                "Azure OpenAI endpoint must be provided via --azure-endpoint parameter or AZURE_OPENAI_ENDPOINT environment variable.\n"
                "Example: export AZURE_OPENAI_ENDPOINT='https://your-resource-name.openai.azure.com/'"
            )
        
        # Initialize Azure OpenAI client with Azure CLI authentication
        token_provider = get_bearer_token_provider(
            AzureCliCredential(), 
            "https://cognitiveservices.azure.com/.default"
        )
        
        self.client = AzureOpenAI(
            azure_endpoint=self.azure_endpoint,
            azure_ad_token_provider=token_provider,
            api_version="2024-02-01"
        )
        
        # Enhanced priority system for containerd
        self.priority_dirs = {
            'client': 20,      # Core client API
            'api': 18,         # API definitions  
            'core': 16,        # Core functionality
            'pkg': 14,         # Package implementations
            'cmd': 12,         # Command-line tools
            'plugins': 10,     # Plugin system
            'internal': 8,     # Internal packages
            'contrib': 6,      # Contributions
            'defaults': 4,     # Default configurations
            'integration': 2,  # Integration tests
            'test': 0,         # Skip test files
            'vendor': 0,       # Skip vendor files
        }
        
        # File importance bonuses
        self.file_bonuses = {
            'client.go': 10,
            'container.go': 8,
            'image.go': 8,
            'task.go': 8,
            'service.go': 6,
            'server.go': 6,
            'api.go': 5,
            'main.go': 4,
        }
        
        # Skip patterns
        self.skip_patterns = [
            r'.*_test\.go$',
            r'.*/test/.*',
            r'.*/vendor/.*',
            r'.*\.pb\.go$',
            r'.*\.gen\.go$',
            r'.*/testdata/.*',
            r'.*mock.*\.go$',
            r'.*example.*\.go$',
            r'.*/\..*',  # Hidden files
        ]
        
        self.generated_hashes = set()
        self.stats = {
            'total_files_scanned': 0,
            'files_processed': 0,
            'qa_pairs_generated': 0,
            'api_calls_made': 0,
            'errors': 0,
            'duplicates_avoided': 0
        }

    def should_skip_file(self, file_path: str) -> bool:
        """Check if file should be skipped based on patterns"""
        for pattern in self.skip_patterns:
            if re.match(pattern, file_path):
                return True
        return False

    def calculate_file_priority(self, file_info: FileInfo) -> float:
        """Calculate priority score for a file"""
        path_parts = Path(file_info.path).parts
        filename = Path(file_info.path).name
        
        # Base directory priority
        score = 0
        for part in path_parts:
            if part in self.priority_dirs:
                score += self.priority_dirs[part]
                break
        
        # File-specific bonuses
        if filename in self.file_bonuses:
            score += self.file_bonuses[filename]
        
        # Pattern-based bonuses
        if filename.endswith('_client.go'):
            score += 5
        elif filename.endswith('_api.go'):
            score += 4
        elif filename.startswith('service'):
            score += 3
        elif filename.endswith('_opts.go'):
            score += 2
        
        # Size and complexity factors
        if file_info.function_count > 20:
            score += 3
        elif file_info.function_count > 10:
            score += 2
        elif file_info.function_count > 5:
            score += 1
        
        if file_info.has_interfaces:
            score += 2
        if file_info.has_structs:
            score += 1
        
        return score

    def analyze_go_file(self, file_path: Path) -> Optional[FileInfo]:
        """Analyze a Go file and extract metadata"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (UnicodeDecodeError, OSError):
            return None
        
        # Extract package name
        package_match = re.search(r'package\s+(\w+)', content)
        package = package_match.group(1) if package_match else 'unknown'
        
        # Count functions
        function_count = len(re.findall(r'\nfunc\s+\w+', content))
        
        # Check for structs, interfaces, constants
        has_structs = bool(re.search(r'\ntype\s+\w+\s+struct\s*{', content))
        has_interfaces = bool(re.search(r'\ntype\s+\w+\s+interface\s*{', content))
        has_consts = bool(re.search(r'\nconst\s+', content))
        
        # Simple complexity score based on various factors
        complexity_score = (
            len(content) / 1000 +  # Lines factor
            function_count * 2 +    # Function factor
            (3 if has_interfaces else 0) +
            (2 if has_structs else 0) +
            (1 if has_consts else 0)
        )
        
        file_info = FileInfo(
            path=str(file_path),
            package=package,
            size=len(content),
            function_count=function_count,
            has_structs=has_structs,
            has_interfaces=has_interfaces,
            has_consts=has_consts,
            complexity_score=complexity_score,
            priority_score=0  # Will be calculated later
        )
        
        file_info.priority_score = self.calculate_file_priority(file_info)
        return file_info

    def scan_repository(self) -> List[FileInfo]:
        """Scan the repository and collect file information"""
        print(f"Scanning repository: {self.repo_path}")
        go_files = []
        
        for go_file in self.repo_path.rglob("*.go"):
            if self.should_skip_file(str(go_file)):
                continue
            
            file_info = self.analyze_go_file(go_file)
            if file_info:
                go_files.append(file_info)
        
        self.stats['total_files_scanned'] = len(go_files)
        
        # Sort by priority score (descending)
        go_files.sort(key=lambda x: x.priority_score, reverse=True)
        
        print(f"Found {len(go_files)} eligible Go files")
        print(f"Top 10 files by priority:")
        for i, file_info in enumerate(go_files[:10]):
            print(f"  {i+1}. {file_info.path} (score: {file_info.priority_score:.1f})")
        
        return go_files[:self.max_files]

    def generate_training_prompt(self, file_info: FileInfo, file_content: str) -> str:
        """Generate a comprehensive prompt for Azure OpenAI to analyze Go code"""
        relative_path = Path(file_info.path).relative_to(self.repo_path)
        
        prompt = """
You are an expert in containerd and Go programming. Analyze the following Go source code file and generate high-quality training data for fine-tuning a containerd expert assistant.

File: {relative_path}
Package: {package}
Functions: {function_count}
Has Structs: {has_structs}
Has Interfaces: {has_interfaces}

SOURCE CODE:
```go
{file_content}
```

Generate 8-12 diverse question-answer pairs that would help train an AI assistant to be an expert in containerd. Focus on:

1. **File Purpose**: What does this file do in the containerd architecture?
2. **Key Functions**: What are the most important exported functions and what do they do?
3. **Data Structures**: What are the main structs/interfaces and their purpose?
4. **Integration**: How does this component integrate with other parts of containerd?
5. **Usage Patterns**: How would developers typically use this code?
6. **Technical Details**: Important implementation details, algorithms, or design patterns
7. **Error Handling**: How does this code handle errors and edge cases?

Each question should be specific, technical, and practical for someone working with containerd. Each answer should be comprehensive, accurate, and demonstrate deep understanding of both the code and containerd architecture.

Return the response as a JSON array of objects, where each object has:
- "question": A specific, technical question about the code
- "answer": A comprehensive, expert-level answer

Example format:
[
  {{
    "question": "What is the purpose of the X function in this file?",
    "answer": "The X function serves as... It handles... and integrates with..."
  }}
]

Generate questions that would actually be asked by developers working with containerd, not generic questions.
""".format(
            relative_path=relative_path,
            package=file_info.package,
            function_count=file_info.function_count,
            has_structs=file_info.has_structs,
            has_interfaces=file_info.has_interfaces,
            file_content=file_content
        )
        return prompt

    def call_azure_openai(self, prompt: str) -> Optional[List[Dict[str, str]]]:
        """Call Azure OpenAI API to generate training data"""
        try:
            response = self.client.chat.completions.create(
                model=self.azure_deployment,
                messages=[
                    {"role": "system", "content": "You are an expert in containerd and Go programming. Generate high-quality training data for fine-tuning a containerd expert assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000,
                top_p=0.9
            )
            
            self.stats['api_calls_made'] += 1
            
            # Parse the JSON response
            response_text = response.choices[0].message.content.strip()
            
            # Try to extract JSON from the response
            if response_text.startswith('['):
                qa_pairs = json.loads(response_text)
            else:
                # Try to find JSON in the response
                json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                if json_match:
                    qa_pairs = json.loads(json_match.group(0))
                else:
                    print(f"Warning: Could not extract JSON from response: {response_text[:200]}...")
                    return None
            
            return qa_pairs
            
        except Exception as e:
            print(f"Error calling Azure OpenAI: {e}")
            self.stats['errors'] += 1
            return None

    def process_file(self, file_info: FileInfo) -> List[Dict[str, Any]]:
        """Process a single file and generate training data"""
        try:
            with open(file_info.path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (UnicodeDecodeError, OSError):
            return []
        
        # Truncate very large files to avoid token limits
        if len(content) > 8000:
            content = content[:8000] + "\n// ... (file truncated for analysis)"
        
        prompt = self.generate_training_prompt(file_info, content)
        qa_pairs = self.call_azure_openai(prompt)
        
        if not qa_pairs:
            return []
        
        # Convert to JSONL format with system message
        jsonl_entries = []
        for qa in qa_pairs:
            if not isinstance(qa, dict) or 'question' not in qa or 'answer' not in qa:
                continue
            
            # Create hash for deduplication
            content_hash = hashlib.md5(qa['question'].encode()).hexdigest()
            if content_hash in self.generated_hashes:
                self.stats['duplicates_avoided'] += 1
                continue
            
            self.generated_hashes.add(content_hash)
            
            jsonl_entry = {
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are an expert in containerd and container runtime systems. Provide accurate, detailed, and practical information about containerd's architecture, APIs, and implementation."
                    },
                    {
                        "role": "user", 
                        "content": qa['question']
                    },
                    {
                        "role": "assistant", 
                        "content": qa['answer']
                    }
                ]
            }
            
            jsonl_entries.append(jsonl_entry)
        
        return jsonl_entries

    def generate_training_data(self):
        """Main method to generate training data"""
        print("Starting Azure OpenAI-powered training data generation...")
        print(f"Repository: {self.repo_path}")
        print(f"Output: {self.output_path}")
        print(f"Max files: {self.max_files}")
        print(f"Max Q&A per file: {self.max_qa_per_file}")
        print(f"Azure deployment: {self.azure_deployment}")
        
        # Scan repository
        files_to_process = self.scan_repository()
        
        if not files_to_process:
            print("No Go files found to process!")
            return
        
        # Process files in batches
        all_qa_pairs = []
        
        for i in range(0, len(files_to_process), self.batch_size):
            batch = files_to_process[i:i + self.batch_size]
            print(f"\nProcessing batch {i//self.batch_size + 1}/{(len(files_to_process) + self.batch_size - 1)//self.batch_size}")
            
            for file_info in batch:
                print(f"  Processing: {Path(file_info.path).relative_to(self.repo_path)}")
                
                qa_pairs = self.process_file(file_info)
                all_qa_pairs.extend(qa_pairs)
                
                self.stats['files_processed'] += 1
                self.stats['qa_pairs_generated'] += len(qa_pairs)
                
                # Add delay to avoid rate limiting
                time.sleep(1)
        
        # Write to JSONL file
        with open(self.output_path, 'w', encoding='utf-8') as f:
            for qa_pair in all_qa_pairs:
                f.write(json.dumps(qa_pair) + '\n')
        
        # Generate metadata
        metadata = {
            'generation_info': {
                'timestamp': time.time(),
                'repo_path': str(self.repo_path),
                'azure_deployment': self.azure_deployment,
                'max_files': self.max_files,
                'max_qa_per_file': self.max_qa_per_file
            },
            'stats': self.stats,
            'files_processed': [
                {
                    'path': str(Path(f.path).relative_to(self.repo_path)),
                    'package': f.package,
                    'priority_score': f.priority_score,
                    'function_count': f.function_count
                }
                for f in files_to_process[:self.stats['files_processed']]
            ]
        }
        
        metadata_path = self.output_path.with_suffix('.metadata.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\n✅ Training data generation completed!")
        print(f"📊 Statistics:")
        print(f"  - Total files scanned: {self.stats['total_files_scanned']}")
        print(f"  - Files processed: {self.stats['files_processed']}")
        print(f"  - Q&A pairs generated: {self.stats['qa_pairs_generated']}")
        print(f"  - API calls made: {self.stats['api_calls_made']}")
        print(f"  - Errors: {self.stats['errors']}")
        print(f"  - Duplicates avoided: {self.stats['duplicates_avoided']}")
        print(f"📁 Files created:")
        print(f"  - Training data: {self.output_path}")
        print(f"  - Metadata: {metadata_path}")

def main():
    parser = argparse.ArgumentParser(description='Generate containerd training data using Azure OpenAI')
    parser.add_argument('--repo-path', default='/workspace/upstream/containerd', help='Path to containerd repository')
    parser.add_argument('--output-path', default='/workspace/containerd-agent/output/containerd_training_data_azure.jsonl', help='Output JSONL file path')
    parser.add_argument('--max-files', type=int, default=500, help='Maximum number of files to process')
    parser.add_argument('--max-qa-per-file', type=int, default=12, help='Maximum Q&A pairs per file')
    parser.add_argument('--azure-endpoint', help='Azure OpenAI endpoint')
    parser.add_argument('--azure-deployment', default='gpt-4o', help='Azure OpenAI deployment name')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for processing')
    
    args = parser.parse_args()
    
    generator = AzureOpenAITrainingDataGenerator(
        repo_path=args.repo_path,
        output_path=args.output_path,
        max_files=args.max_files,
        max_qa_per_file=args.max_qa_per_file,
        azure_endpoint=args.azure_endpoint,
        azure_deployment=args.azure_deployment,
        batch_size=args.batch_size
    )
    
    generator.generate_training_data()

if __name__ == "__main__":
    main()
