import argparse
import re
import json
import os
import time
from pathlib import Path
from openai import AzureOpenAI
from azure.identity import AzureCliCredential, get_bearer_token_provider
from go_dependencies import get_go_modules

class GoModuleAnalyzer:
    def __init__(self, repo_path):
        self.repo_path = Path(repo_path)

    def should_skip_file(self, file_path, skip_patterns):
        for pattern in skip_patterns:
            if re.match(pattern, str(file_path)):
                return True
        return False

    def analyze_go_files(self, modules):
        skip_patterns = [
            r'.*_test\.go$',
            r'.*/test/.*',
            r'.*/vendor/.*',
            r'.*\.pb\.go$',
            r'.*\.gen\.go$',
            r'.*/testdata/.*',
            r'.*mock.*\.go$',
            r'.*example.*\.go$',
            r'.*/\..*',
        ]
        internal_modules = [mod for mod, info in modules.items() if info['type'] == 'internal']
        for go_file in self.repo_path.rglob("*.go"):
            if self.should_skip_file(go_file, skip_patterns):
                continue
            try:
                with open(go_file, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                continue
            pkg_match = re.search(r'package\s+([\w/.-]+)', content)
            if not pkg_match:
                continue
            pkg_name = pkg_match.group(1)
            for mod in internal_modules:
                if pkg_name in mod or mod.endswith(pkg_name):
                    rel_file = str(go_file.relative_to(self.repo_path))
                    modules[mod].setdefault('definition_files', []).append(rel_file)
            import_matches = re.findall(r'import\s*\((.*?)\)|import\s+"([^"]+)",?', content, re.DOTALL)
            imports = set()
            for block, single in import_matches:
                if block:
                    for line in block.splitlines():
                        imp = line.strip().strip('"')
                        if imp:
                            imports.add(imp)
                elif single:
                    imports.add(single)
            for imp in imports:
                for mod in modules:
                    if imp.startswith(mod):
                        rel_file = str(go_file.relative_to(self.repo_path))
                        modules[mod].setdefault('used_in_files', []).append(rel_file)

class AzureModuleQAGenerator:
    def __init__(self, azure_endpoint, azure_deployment, use_env_key=False):
        self.azure_endpoint = azure_endpoint
        self.azure_deployment = azure_deployment
        self.use_env_key = use_env_key
        if use_env_key:
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            self.client = AzureOpenAI(
                azure_endpoint=azure_endpoint,
                api_key=api_key,
                api_version="2024-02-01"
            )
        else:
            token_provider = get_bearer_token_provider(
                AzureCliCredential(),
                "https://cognitiveservices.azure.com/.default"
            )
            self.client = AzureOpenAI(
                azure_endpoint=azure_endpoint,
                azure_ad_token_provider=token_provider,
                api_version="2024-02-01"
            )

    def generate_module_training_prompt(self, module, info, repo_path, max_qa_pairs=3):
        definition_files = info.get('definition_files', [])
        used_in_files = info.get('used_in_files', [])
        if info.get('type') == 'internal':
            prompt = f'''
You are an expert in containerd and Go programming. Analyze the following internal Go module and generate high-quality training data for fine-tuning a containerd expert assistant.

Module: {module}
Version: {info.get('version')}
Type: {info.get('type')}

List all files that define this module ("Defined in files") and all files that use/import this module ("Used in files").

Defined in files:\n{chr(10).join(definition_files)}
Used in files:\n{chr(10).join(used_in_files)}

Generate exactly {max_qa_pairs} diverse question-answer pairs that would help train an AI assistant to be an expert in containerd. Focus on:

1. What files constitute this internal module? List all files if possible.
2. In which files is this module used? List all usage if possible.
3. How does this module integrate with other parts of containerd?

Each question should be specific, technical, and practical for someone working with containerd. Each answer should be comprehensive, accurate, and demonstrate deep understanding of both the code and containerd architecture.

Return the response as a JSON array of objects, where each object has:
- "question": A specific, technical question about the module
- "answer": A comprehensive, expert-level answer

Example format:
[
  {{
    "question": "Which files define this module and what are their roles?",
    "answer": "The module is defined in ..."
  }}
]

Generate questions that would actually be asked by developers working with containerd, not generic questions.
IMPORTANT: Generate exactly {max_qa_pairs} question-answer pairs, no more, no less.
'''
        else:
            prompt = f'''
You are an expert in containerd and Go programming. Analyze the following external Go module and generate high-quality training data for fine-tuning a containerd expert assistant.

Module: {module}
Version: {info.get('version')}
Type: {info.get('type')}

Used in files:\n{chr(10).join(used_in_files)}

Generate exactly {max_qa_pairs} diverse question-answer pairs that would help train an AI assistant to be an expert in containerd. Focus on:

1. **Module Purpose**: What does this module do in the containerd architecture?
2. **In which files is this module used?** List of usage if possible.
3. **Key Functions/Types**: What are the most important exported functions/types and what do they do?
4. **Integration**: How does this module integrate with other parts of containerd?
5. **Usage Patterns**: How would developers typically use this module?
6. **Technical Details**: Important implementation details, algorithms, or design patterns
7. **Error Handling**: How does this module handle errors and edge cases?

Each question should be specific, technical, and practical for someone working with containerd. Each answer should be comprehensive, accurate, and demonstrate deep understanding of both the code and containerd architecture.

Return the response as a JSON array of objects, where each object has:
- "question": A specific, technical question about the module
- "answer": A comprehensive, expert-level answer

Example format:
[
  {{
    "question": "What is the purpose of this module and where is it used?",
    "answer": "This module is used in ..."
  }}
]

Generate questions that would actually be asked by developers working with containerd, not generic questions.
IMPORTANT: Generate exactly {max_qa_pairs} question-answer pairs, no more, no less.
'''
        return prompt

    def call_azure_openai(self, prompt):
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
            response_text = response.choices[0].message.content.strip()
            if response_text.startswith('['):
                qa_pairs = json.loads(response_text)
            else:
                json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                if json_match:
                    qa_pairs = json.loads(json_match.group(0))
                else:
                    print(f"Warning: Could not extract JSON from response: {response_text[:200]}...")
                    return None
            return qa_pairs
        except Exception as e:
            print(f"Error calling Azure OpenAI: {e}")
            return None

    def generate_qa_for_modules(self, modules, num_modules, repo_path, max_qa_per_module=8, output_jsonl=None, all_modules=False):
        def usage_count(info):
            return len(set(info.get('used_in_files', []))) + len(set(info.get('definition_files', [])))
        sorted_mods = sorted(modules.items(), key=lambda kv: (-usage_count(kv[1]), kv[0]))
        if all_modules:
            selected_mods = [mod for mod, _ in sorted_mods]
        else:
            selected_mods = [mod for mod, _ in sorted_mods[:num_modules]]
        qa_jsonl = []
        stats = {
            'total_modules_scanned': len(modules),
            'modules_processed': 0,
            'qa_pairs_generated': 0,
            'api_calls_made': 0,
            'errors': 0,
            'duplicates_avoided': 0
        }
        for idx, mod in enumerate(selected_mods):
            info = modules[mod]
            print(f"Processing module {idx+1}/{len(selected_mods)}: {mod}")
            prompt = self.generate_module_training_prompt(mod, info, repo_path, max_qa_pairs=max_qa_per_module)
            qa_pairs = self.call_azure_openai(prompt)
            stats['api_calls_made'] += 1
            if not qa_pairs:
                print(f"No Q&A pairs generated for module: {mod}")
                stats['errors'] += 1
                continue
            for qa in qa_pairs:
                if not isinstance(qa, dict) or 'question' not in qa or 'answer' not in qa:
                    continue
                # Clean answer: replace all newlines (escaped or real) with a single space
                answer = qa['answer'].replace('\\n', ' ').replace('\n', ' ')
                answer = re.sub(r'\s+', ' ', answer).strip()
                qa_jsonl.append({
                    "messages": [
                        {"role": "system", "content": "You are an expert in containerd and container runtime systems. Provide accurate, detailed, and practical information about containerd's architecture, APIs, and implementation."},
                        {"role": "user", "content": qa['question']},
                        {"role": "assistant", "content": answer}
                    ]
                })
            stats['modules_processed'] += 1
            stats['qa_pairs_generated'] += len(qa_pairs)
            print(f"Generated {len(qa_pairs)} Q&A pairs for module: {mod}")
        if output_jsonl and qa_jsonl:
            with open(output_jsonl, 'w', encoding='utf-8') as f:
                for entry in qa_jsonl:
                    f.write(json.dumps(entry) + '\n')
            print(f"Q&A pairs written to {output_jsonl}")
        # Write metadata
        metadata = {
            'generation_info': {
                'timestamp': time.time(),
                'repo_path': str(repo_path),
                'azure_deployment': self.azure_deployment,
                'num_modules': len(selected_mods),
                'max_qa_per_module': max_qa_per_module,
                'all_modules': all_modules
            },
            'stats': stats,
            'modules_processed': selected_mods[:stats['modules_processed']]
        }
        metadata_path = None
        if output_jsonl:
            metadata_path = Path(output_jsonl).with_suffix('.metadata.json')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
        print(f"\n✅ Training data generation completed!")
        print(f"📊 Statistics:")
        print(f"  - Total modules scanned: {stats['total_modules_scanned']}")
        print(f"  - Modules processed: {stats['modules_processed']}")
        print(f"  - Q&A pairs generated: {stats['qa_pairs_generated']}")
        print(f"  - API calls made: {stats['api_calls_made']}")
        print(f"  - Errors: {stats['errors']}")
        print(f"  - Duplicates avoided: {stats['duplicates_avoided']}")
        print(f"📁 Files created:")
        if output_jsonl:
            print(f"  - Training data: {output_jsonl}")
        if metadata_path:
            print(f"  - Metadata: {metadata_path}")

def main():
    parser = argparse.ArgumentParser(description="Print Go modules and optionally generate Azure OpenAI Q&A for selected modules")
    parser.add_argument('--repo-path', default=os.getenv('CONTAINERD_REPO_PATH', '/workspace/upstream/containerd'), help='Path to Go repository (default: /workspace/upstream/containerd or $CONTAINERD_REPO_PATH)')
    parser.add_argument('--azure-endpoint', default=os.getenv('AZURE_OPENAI_ENDPOINT'), help='Azure OpenAI endpoint (default: $AZURE_OPENAI_ENDPOINT)')
    parser.add_argument('--azure-deployment', default=os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4o'), help='Azure OpenAI deployment name (default: gpt-4o or $AZURE_OPENAI_DEPLOYMENT)')
    parser.add_argument('--use-env-key', action='store_true', help='Use AZURE_OPENAI_API_KEY environment variable for authentication')
    parser.add_argument('--num-modules', type=int, help='Number of top modules to generate Q&A for')
    parser.add_argument('--all-modules', action='store_true', help='If set, generate Q&A for all modules and ignore --num-modules')
    parser.add_argument('--max-qa-per-module', type=int, default=3, help='Number of Q&A pairs per module')
    parser.add_argument('--output-jsonl', default=os.getenv('QAMODULES_OUTPUT_PATH', '/workspace/containerd-agent/output/containerd_module_qa.jsonl'), help='Output JSONL file for Q&A pairs (default: /workspace/containerd-agent/output/containerd_module_qa.jsonl or $QAMODULES_OUTPUT_PATH)')
    args = parser.parse_args()

    modules = get_go_modules(args.repo_path)
    if not modules:
        print("No Go modules found.")
        exit(1)
    analyzer = GoModuleAnalyzer(args.repo_path)
    analyzer.analyze_go_files(modules)

    if (args.all_modules or args.num_modules) and args.azure_endpoint:
        qa_generator = AzureModuleQAGenerator(args.azure_endpoint, args.azure_deployment, use_env_key=args.use_env_key)
        qa_generator.generate_qa_for_modules(
            modules,
            args.num_modules if not args.all_modules else None,
            args.repo_path,
            max_qa_per_module=args.max_qa_per_module,
            output_jsonl=args.output_jsonl,
            all_modules=args.all_modules
        )

if __name__ == "__main__":
    main()
