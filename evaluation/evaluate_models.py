#!/usr/bin/env python3
"""
Model Evaluation Script for Containerd Fine-tuned Model

This script compares responses from a fine-tuned model against a baseline model
to evaluate the quality and specialization of the fine-tuned model.
"""

import json
import os
import time
from typing import Dict, List, Any
from datetime import datetime
from openai import AzureOpenAI
import argparse


class ModelEvaluator:
    def __init__(self, azure_endpoint: str, api_key: str = None):
        """Initialize the evaluator with Azure OpenAI client"""
        self.client = AzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=api_key or os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2025-01-01-preview"
        )
        
        # Model configurations
        self.models = {
            "fine_tuned": {
                "deployment": "t-4-1-2025-04-14-ft-f20223e392164a70bf32144db3ab63c6-_containerd",
                "display_name": "Fine-tuned Containerd Model",
                "system_message": "You are an expert in containerd and container runtime systems. Provide accurate, detailed, and practical information about containerd's architecture, APIs, and implementation."
            },
            "baseline": {
                "deployment": "gpt-4.1-general", 
                "display_name": "GPT-4.1 Baseline",
                "system_message": "You are a helpful assistant with expertise in container technologies and system administration."
            }
        }
    
    def query_model(self, deployment: str, question: str, system_message: str) -> Dict[str, Any]:
        """Query a model and return response with metadata"""
        try:
            start_time = time.time()
            
            response = self.client.chat.completions.create(
                model=deployment,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": question}
                ],
                temperature=0.7,
                max_tokens=1000,
                top_p=0.95
            )
            
            end_time = time.time()
            
            return {
                "response": response.choices[0].message.content,
                "response_time": end_time - start_time,
                "tokens_used": response.usage.total_tokens,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "success": True,
                "error": None
            }
            
        except Exception as e:
            return {
                "response": None,
                "response_time": None,
                "tokens_used": None,
                "prompt_tokens": None,
                "completion_tokens": None,
                "success": False,
                "error": str(e)
            }
    
    def evaluate_questions(self, questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate all questions against both models"""
        results = {
            "evaluation_timestamp": datetime.now().isoformat(),
            "models": self.models,
            "questions": [],
            "summary": {
                "total_questions": len(questions),
                "successful_fine_tuned": 0,
                "successful_baseline": 0,
                "average_response_time": {
                    "fine_tuned": 0,
                    "baseline": 0
                },
                "average_tokens_used": {
                    "fine_tuned": 0,
                    "baseline": 0
                }
            }
        }
        
        total_response_time = {"fine_tuned": 0, "baseline": 0}
        total_tokens = {"fine_tuned": 0, "baseline": 0}
        
        for i, question_data in enumerate(questions, 1):
            print(f"\n{'='*60}")
            print(f"Question {i}/{len(questions)}: {question_data['id']}")
            print(f"Category: {question_data['category']}")
            print(f"Question: {question_data['question']}")
            print(f"{'='*60}")
            
            question_result = {
                "question_id": question_data["id"],
                "category": question_data["category"],
                "question": question_data["question"],
                "expected_topics": question_data.get("expected_topics", []),
                "responses": {}
            }
            
            # Query both models
            for model_key, model_config in self.models.items():
                print(f"\n🤖 Querying {model_config['display_name']}...")
                
                result = self.query_model(
                    deployment=model_config["deployment"],
                    question=question_data["question"],
                    system_message=model_config["system_message"]
                )
                
                question_result["responses"][model_key] = result
                
                if result["success"]:
                    print(f"✅ Response received ({result['tokens_used']} tokens, {result['response_time']:.2f}s)")
                    
                    if model_key == "fine_tuned":
                        results["summary"]["successful_fine_tuned"] += 1
                    else:
                        results["summary"]["successful_baseline"] += 1
                    
                    total_response_time[model_key] += result["response_time"]
                    total_tokens[model_key] += result["tokens_used"]
                else:
                    print(f"❌ Error: {result['error']}")
                
                # Rate limiting
                time.sleep(1)
            
            results["questions"].append(question_result)
        
        # Calculate averages
        if results["summary"]["successful_fine_tuned"] > 0:
            results["summary"]["average_response_time"]["fine_tuned"] = total_response_time["fine_tuned"] / results["summary"]["successful_fine_tuned"]
            results["summary"]["average_tokens_used"]["fine_tuned"] = total_tokens["fine_tuned"] / results["summary"]["successful_fine_tuned"]
        
        if results["summary"]["successful_baseline"] > 0:
            results["summary"]["average_response_time"]["baseline"] = total_response_time["baseline"] / results["summary"]["successful_baseline"]
            results["summary"]["average_tokens_used"]["baseline"] = total_tokens["baseline"] / results["summary"]["successful_baseline"]
        
        return results
    
    def generate_human_readable_report(self, results: Dict[str, Any], output_file: str):
        """Generate a human-readable HTML report"""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Containerd Model Evaluation Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1, h2, h3 {{
            color: #333;
        }}
        h1 {{
            border-bottom: 3px solid #007acc;
            padding-bottom: 10px;
        }}
        .summary {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .question-block {{
            margin: 30px 0;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 20px;
            background-color: #fafafa;
        }}
        .question-header {{
            background-color: #007acc;
            color: white;
            padding: 10px;
            margin: -20px -20px 15px -20px;
            border-radius: 5px 5px 0 0;
        }}
        .response-comparison {{
            display: flex;
            gap: 20px;
            margin-top: 15px;
        }}
        .response-box {{
            flex: 1;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            background-color: white;
        }}
        .fine-tuned {{
            border-left: 4px solid #28a745;
        }}
        .baseline {{
            border-left: 4px solid #ffc107;
        }}
        .response-meta {{
            font-size: 0.9em;
            color: #666;
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #eee;
        }}
        .error {{
            color: #dc3545;
            background-color: #f8d7da;
            padding: 10px;
            border-radius: 3px;
        }}
        .expected-topics {{
            background-color: #e9ecef;
            padding: 10px;
            border-radius: 3px;
            margin: 10px 0;
        }}
        .category-tag {{
            background-color: #007acc;
            color: white;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 0.8em;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .stat-card {{
            background-color: white;
            padding: 15px;
            border-radius: 5px;
            border: 1px solid #ddd;
            text-align: center;
        }}
        .stat-value {{
            font-size: 1.5em;
            font-weight: bold;
            color: #007acc;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Containerd Model Evaluation Report</h1>
        
        <div class="summary">
            <h2>📊 Evaluation Summary</h2>
            <p><strong>Generated:</strong> {results['evaluation_timestamp']}</p>
            <p><strong>Total Questions:</strong> {results['summary']['total_questions']}</p>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">{results['summary']['successful_fine_tuned']}</div>
                    <div class="stat-label">Fine-tuned Success</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{results['summary']['successful_baseline']}</div>
                    <div class="stat-label">Baseline Success</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{results['summary']['average_response_time']['fine_tuned']:.2f}s</div>
                    <div class="stat-label">Fine-tuned Avg Time</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{results['summary']['average_response_time']['baseline']:.2f}s</div>
                    <div class="stat-label">Baseline Avg Time</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{results['summary']['average_tokens_used']['fine_tuned']:.0f}</div>
                    <div class="stat-label">Fine-tuned Avg Tokens</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{results['summary']['average_tokens_used']['baseline']:.0f}</div>
                    <div class="stat-label">Baseline Avg Tokens</div>
                </div>
            </div>
        </div>
        
        <h2>🔍 Model Configurations</h2>
        <ul>
            <li><strong>Fine-tuned Model:</strong> {results['models']['fine_tuned']['deployment']}</li>
            <li><strong>Baseline Model:</strong> {results['models']['baseline']['deployment']}</li>
        </ul>
        
        <h2>📝 Question-by-Question Analysis</h2>
"""
        
        # Add each question and response comparison
        for question in results["questions"]:
            expected_topics_html = ""
            if question["expected_topics"]:
                topics_list = ", ".join(question["expected_topics"])
                expected_topics_html = f'<div class="expected-topics"><strong>Expected Topics:</strong> {topics_list}</div>'
            
            html_content += f"""
        <div class="question-block">
            <div class="question-header">
                <h3>🔸 {question['question_id']} <span class="category-tag">{question['category']}</span></h3>
            </div>
            <p><strong>Question:</strong> {question['question']}</p>
            {expected_topics_html}
            
            <div class="response-comparison">
"""
            
            # Add fine-tuned response
            ft_response = question["responses"]["fine_tuned"]
            if ft_response["success"]:
                html_content += f"""
                <div class="response-box fine-tuned">
                    <h4>🎯 Fine-tuned Model Response</h4>
                    <div style="white-space: pre-wrap;">{ft_response['response']}</div>
                    <div class="response-meta">
                        <strong>Tokens:</strong> {ft_response['tokens_used']} | 
                        <strong>Time:</strong> {ft_response['response_time']:.2f}s
                    </div>
                </div>
"""
            else:
                html_content += f"""
                <div class="response-box fine-tuned">
                    <h4>🎯 Fine-tuned Model Response</h4>
                    <div class="error">Error: {ft_response['error']}</div>
                </div>
"""
            
            # Add baseline response
            baseline_response = question["responses"]["baseline"]
            if baseline_response["success"]:
                html_content += f"""
                <div class="response-box baseline">
                    <h4>📊 Baseline Model Response</h4>
                    <div style="white-space: pre-wrap;">{baseline_response['response']}</div>
                    <div class="response-meta">
                        <strong>Tokens:</strong> {baseline_response['tokens_used']} | 
                        <strong>Time:</strong> {baseline_response['response_time']:.2f}s
                    </div>
                </div>
"""
            else:
                html_content += f"""
                <div class="response-box baseline">
                    <h4>📊 Baseline Model Response</h4>
                    <div class="error">Error: {baseline_response['error']}</div>
                </div>
"""
            
            html_content += """
            </div>
        </div>
"""
        
        html_content += """
        <footer style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666;">
            <p>Generated by Containerd Model Evaluator</p>
        </footer>
    </div>
</body>
</html>
"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"📄 Human-readable report saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate fine-tuned containerd model")
    parser.add_argument("--questions", default="sample_questions.json", help="Path to questions JSON file")
    parser.add_argument("--output-json", default="evaluation_results.json", help="Output JSON file")
    parser.add_argument("--output-html", default="evaluation_report.html", help="Output HTML report file")
    parser.add_argument("--azure-endpoint", default="https://mitchzhu-containerd.openai.azure.com/", help="Azure OpenAI endpoint")
    parser.add_argument("--api-key", help="Azure OpenAI API key (or use AZURE_OPENAI_API_KEY env var)")
    
    args = parser.parse_args()
    
    # Load questions
    if not os.path.exists(args.questions):
        print(f"❌ Questions file not found: {args.questions}")
        return
    
    with open(args.questions, 'r') as f:
        questions_data = json.load(f)
    
    questions = questions_data["questions"]
    print(f"📋 Loaded {len(questions)} questions from {args.questions}")
    
    # Initialize evaluator
    evaluator = ModelEvaluator(args.azure_endpoint, args.api_key)
    
    # Run evaluation
    print(f"🚀 Starting evaluation with {len(questions)} questions...")
    results = evaluator.evaluate_questions(questions)
    
    # Save JSON results
    with open(args.output_json, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"💾 Raw results saved to: {args.output_json}")
    
    # Generate human-readable report
    evaluator.generate_human_readable_report(results, args.output_html)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"✅ Evaluation Complete!")
    print(f"{'='*60}")
    print(f"Fine-tuned successful: {results['summary']['successful_fine_tuned']}/{results['summary']['total_questions']}")
    print(f"Baseline successful: {results['summary']['successful_baseline']}/{results['summary']['total_questions']}")
    print(f"Average response time (fine-tuned): {results['summary']['average_response_time']['fine_tuned']:.2f}s")
    print(f"Average response time (baseline): {results['summary']['average_response_time']['baseline']:.2f}s")
    print(f"Average tokens (fine-tuned): {results['summary']['average_tokens_used']['fine_tuned']:.0f}")
    print(f"Average tokens (baseline): {results['summary']['average_tokens_used']['baseline']:.0f}")


if __name__ == "__main__":
    main()
