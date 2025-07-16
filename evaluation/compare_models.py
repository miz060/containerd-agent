#!/usr/bin/env python3
"""
Model Comparison Script for Fine-tuned vs Base Models
Uses Azure CLI authentication for secure API access
"""

import os
import json
import asyncio
from typing import Dict, List, Any
from dataclasses import dataclass
from pathlib import Path
import time
from datetime import datetime

# Azure OpenAI imports
from openai import AzureOpenAI
from azure.identity import AzureCliCredential, get_bearer_token_provider



@dataclass
class ModelConfig:
    name: str
    deployment: str
    endpoint: str
    description: str

@dataclass
class ComparisonResult:
    question: str
    base_response: str
    finetuned_response: str
    base_tokens: int
    finetuned_tokens: int
    base_time: float
    finetuned_time: float
    category: str = "general"
    # Additional metadata from question file
    context: str = None
    expected_topics: List[str] = None
    original_response_summary: str = None

class ModelComparator:
    def __init__(self, 
                 base_endpoint: str = "https://mitchzhu-containerd.openai.azure.com/",
                 base_deployment: str = "gpt-4.1-general",
                 finetuned_endpoint: str = "https://mitchzhu-containerd.openai.azure.com/",
                 finetuned_deployment: str = "gpt-4-04-14"):
        
        # Initialize Azure CLI authentication
        token_provider = get_bearer_token_provider(
            AzureCliCredential(), 
            "https://cognitiveservices.azure.com/.default"
        )
        
        # Initialize clients for both models
        self.base_client = AzureOpenAI(
            azure_endpoint=base_endpoint,
            azure_ad_token_provider=token_provider,
            api_version="2025-01-01-preview"
        )
        
        self.finetuned_client = AzureOpenAI(
            azure_endpoint=finetuned_endpoint,
            azure_ad_token_provider=token_provider,
            api_version="2025-01-01-preview"
        )
        
        self.base_config = ModelConfig(
            name="GPT-4.1 Base",
            deployment=base_deployment,
            endpoint=base_endpoint,
            description="Standard GPT-4.1 model"
        )
        
        self.finetuned_config = ModelConfig(
            name="GPT-4.1 Fine-tuned",
            deployment=finetuned_deployment,
            endpoint=finetuned_endpoint,
            description="Fine-tuned GPT-4.1 model specialized for containerd"
        )
        
        print(f"✅ Initialized model comparator")
        print(f"   Base model: {self.base_config.name} ({self.base_config.deployment})")
        print(f"   Fine-tuned model: {self.finetuned_config.name}")
        print(f"   Authentication: Azure CLI")

    async def query_model(self, client: AzureOpenAI, deployment: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Query a model and return response with metadata"""
        start_time = time.time()
        
        try:
            response = client.chat.completions.create(
                model=deployment,
                messages=messages,
                temperature=0.1,  # Low temperature for consistent responses
                max_tokens=1000,
                top_p=0.9
            )
            
            end_time = time.time()
            
            return {
                "response": response.choices[0].message.content,
                "tokens": response.usage.total_tokens,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "response_time": end_time - start_time,
                "success": True,
                "error": None
            }
            
        except Exception as e:
            end_time = time.time()
            return {
                "response": f"Error: {str(e)}",
                "tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "response_time": end_time - start_time,
                "success": False,
                "error": str(e)
            }

    async def compare_question(self, question: str, system_prompt: str = None, category: str = "general", **kwargs) -> ComparisonResult:
        """Compare both models on a single question"""
        # Default system prompt for containerd questions
        if system_prompt is None:
            system_prompt = "You are an expert in containerd and container runtime systems. Provide accurate, detailed, and practical information about containerd's architecture, APIs, and implementation."
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]
        
        print(f"🔍 Comparing question: {question[:60]}...")
        
        # Query both models
        base_result = await self.query_model(self.base_client, self.base_config.deployment, messages)
        finetuned_result = await self.query_model(self.finetuned_client, self.finetuned_config.deployment, messages)
        
        # Add small delay to avoid rate limiting
        await asyncio.sleep(1)
        
        return ComparisonResult(
            question=question,
            base_response=base_result["response"],
            finetuned_response=finetuned_result["response"],
            base_tokens=base_result["tokens"],
            finetuned_tokens=finetuned_result["tokens"],
            base_time=base_result["response_time"],
            finetuned_time=finetuned_result["response_time"],
            category=category,
            context=kwargs.get("context"),
            expected_topics=kwargs.get("expected_topics"),
            original_response_summary=kwargs.get("original_response_summary")
        )

    async def run_comparison(self, questions_file: str, output_file: str):
        """Run comparison on all questions from a file"""
        print(f"📝 Loading questions from: {questions_file}")
        
        # Load questions
        with open(questions_file, 'r', encoding='utf-8') as f:
            questions_data = json.load(f)
        
        print(f"📊 Found {len(questions_data)} questions to compare")
        
        results = []
        
        for i, question_data in enumerate(questions_data, 1):
            print(f"\n[{i}/{len(questions_data)}] Processing question...")
            
            # Extract question details
            question = question_data.get("question", "")
            system_prompt = question_data.get("system_prompt")
            category = question_data.get("category", "general")
            
            if not question:
                print(f"  ⚠️  Skipping empty question at index {i}")
                continue
            
            try:
                result = await self.compare_question(
                    question=question,
                    system_prompt=system_prompt,
                    category=category,
                    context=question_data.get("context"),
                    expected_topics=question_data.get("expected_topics"),
                    original_response_summary=question_data.get("original_response_summary")
                )
                results.append(result)
                
                print(f"  ✅ Base model: {result.base_tokens} tokens, {result.base_time:.2f}s")
                print(f"  ✅ Fine-tuned model: {result.finetuned_tokens} tokens, {result.finetuned_time:.2f}s")
                
            except Exception as e:
                print(f"  ❌ Error processing question: {e}")
                continue
        
        # Save results
        await self.save_results(results, output_file)
        
        # Print summary
        self.print_summary(results)

    async def save_results(self, results: List[ComparisonResult], output_file: str):
        """Save comparison results to a JSON file"""
        print(f"\n💾 Saving results to: {output_file}")
        
        # Convert results to JSON-serializable format
        results_data = {
            "comparison_info": {
                "timestamp": datetime.now().isoformat(),
                "base_model": {
                    "name": self.base_config.name,
                    "deployment": self.base_config.deployment,
                    "endpoint": self.base_config.endpoint,
                    "description": self.base_config.description
                },
                "finetuned_model": {
                    "name": self.finetuned_config.name,
                    "deployment": self.finetuned_config.deployment,
                    "endpoint": self.finetuned_config.endpoint,
                    "description": self.finetuned_config.description
                },
                "total_questions": len(results)
            },
            "results": []
        }
        
        for result in results:
            result_data = {
                "question": result.question,
                "category": result.category,
                "base_model": {
                    "response": result.base_response,
                    "tokens": result.base_tokens,
                    "response_time": result.base_time
                },
                "finetuned_model": {
                    "response": result.finetuned_response,
                    "tokens": result.finetuned_tokens,
                    "response_time": result.finetuned_time
                }
            }
            
            # Add additional metadata if available
            if result.context:
                result_data["context"] = result.context
            if result.expected_topics:
                result_data["expected_topics"] = result.expected_topics
            if result.original_response_summary:
                result_data["original_response_summary"] = result.original_response_summary
            
            results_data["results"].append(result_data)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Results saved successfully")

    def print_summary(self, results: List[ComparisonResult]):
        """Print comparison summary"""
        if not results:
            print("\n❌ No results to summarize")
            return
        
        print(f"\n📊 COMPARISON SUMMARY")
        print(f"=" * 50)
        print(f"Total questions compared: {len(results)}")
        
        # Token usage summary
        total_base_tokens = sum(r.base_tokens for r in results)
        total_finetuned_tokens = sum(r.finetuned_tokens for r in results)
        
        print(f"\nToken Usage:")
        print(f"  Base model: {total_base_tokens:,} tokens")
        print(f"  Fine-tuned model: {total_finetuned_tokens:,} tokens")
        print(f"  Difference: {total_finetuned_tokens - total_base_tokens:+,} tokens")
        
        # Response time summary
        avg_base_time = sum(r.base_time for r in results) / len(results)
        avg_finetuned_time = sum(r.finetuned_time for r in results) / len(results)
        
        print(f"\nResponse Time:")
        print(f"  Base model: {avg_base_time:.2f}s average")
        print(f"  Fine-tuned model: {avg_finetuned_time:.2f}s average")
        print(f"  Difference: {avg_finetuned_time - avg_base_time:+.2f}s")
        
        # Category breakdown
        categories = {}
        for result in results:
            category = result.category
            if category not in categories:
                categories[category] = 0
            categories[category] += 1
        
        if len(categories) > 1:
            print(f"\nCategory Breakdown:")
            for category, count in sorted(categories.items()):
                print(f"  {category}: {count} questions")
    
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Compare fine-tuned vs base models')
    parser.add_argument('--questions', required=True, help='Path to questions JSON file')
    parser.add_argument('--output', required=True, help='Path to output results JSON file')
    parser.add_argument('--base-deployment', default='gpt-4.1-general', help='Base model deployment name')
    parser.add_argument('--finetuned-deployment', default='gpt-4-04-14', help='Fine-tuned model deployment name')
    
    args = parser.parse_args()
    
    comparator = ModelComparator(
        base_deployment=args.base_deployment,
        finetuned_deployment=args.finetuned_deployment
    )
    
    # Run comparison
    asyncio.run(comparator.run_comparison(args.questions, args.output))

if __name__ == "__main__":
    main()
