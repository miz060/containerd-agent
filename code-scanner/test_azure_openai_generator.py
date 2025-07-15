#!/usr/bin/env python3
"""
Test script for Azure OpenAI training data generator
"""

import os
import sys
import subprocess
from pathlib import Path

def test_azure_openai_generator():
    """Test the Azure OpenAI generator with minimal settings"""
    
    # Check if Azure OpenAI endpoint is set
    if not os.getenv("AZURE_OPENAI_ENDPOINT"):
        print("❌ AZURE_OPENAI_ENDPOINT environment variable not set")
        print("Set it with: export AZURE_OPENAI_ENDPOINT='https://your-resource-name.openai.azure.com/'")
        print("Replace 'your-resource-name' with your actual Azure OpenAI resource name")
        return False
    
    # Check if user is logged in to Azure
    try:
        import subprocess
        result = subprocess.run(['az', 'account', 'show'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Not logged in to Azure CLI")
            print("Please run: az login")
            return False
        print("✅ Azure CLI authentication verified")
    except FileNotFoundError:
        print("❌ Azure CLI not found. Please install Azure CLI")
        return False
    
    # Check if containerd repo exists
    repo_path = Path("/workspace/upstream/containerd")
    if not repo_path.exists():
        print(f"❌ Containerd repository not found at {repo_path}")
        return False
    
    # Check if there are Go files
    go_files = list(repo_path.rglob("*.go"))
    if len(go_files) == 0:
        print(f"❌ No Go files found in {repo_path}")
        return False
    
    print(f"✅ Found {len(go_files)} Go files in containerd repository")
    
    # Import the generator
    try:
        from generate_azure_openai_training_data import AzureOpenAITrainingDataGenerator
        print("✅ Successfully imported AzureOpenAITrainingDataGenerator")
    except ImportError as e:
        print(f"❌ Failed to import generator: {e}")
        print("Install dependencies with: pip install -r requirements.txt")
        return False
    
    # Test with minimal settings
    try:
        generator = AzureOpenAITrainingDataGenerator(
            repo_path=str(repo_path),
            output_path="/workspace/containerd-agent/output/test_output.jsonl",
            max_files=2,  # Just test with 2 files
            max_qa_per_file=3,  # 3 Q&A pairs per file
            batch_size=1
        )
        print("✅ Generator initialized successfully")
        
        # Test repository scanning
        files = generator.scan_repository()
        print(f"✅ Scanned repository, found {len(files)} high-priority files")
        
        if len(files) > 0:
            print(f"Top file: {files[0].path} (priority: {files[0].priority_score})")
        
        return True
        
    except Exception as e:
        print(f"❌ Generator test failed: {e}")
        return False

def show_usage():
    """Show usage examples"""
    print("\n🚀 Usage Examples:")
    print("\n1. Login to Azure:")
    print("   az login")
    
    print("\n2. Test the generator:")
    print("   python3 code-scanner/test_azure_openai_generator.py")
    
    print("\n3. Small test run (2 files):")
    print("   python3 code-scanner/generate_azure_openai_training_data.py --max-files 2 --max-qa-per-file 3")
    
    print("\n4. Medium run (50 files):")
    print("   python3 code-scanner/generate_azure_openai_training_data.py --max-files 50 --max-qa-per-file 8")
    
    print("\n5. Full run (500 files):")
    print("   python3 code-scanner/generate_azure_openai_training_data.py --max-files 500 --max-qa-per-file 12")
    
    print("\n6. Large scale (1000 files):")
    print("   python3 code-scanner/generate_azure_openai_training_data.py --max-files 1000 --max-qa-per-file 15")

if __name__ == "__main__":
    print("🧪 Testing Azure OpenAI Training Data Generator")
    print("=" * 50)
    
    success = test_azure_openai_generator()
    
    if success:
        print("\n✅ All tests passed! Ready to generate training data.")
        show_usage()
    else:
        print("\n❌ Tests failed. Please fix the issues above.")
        sys.exit(1)
