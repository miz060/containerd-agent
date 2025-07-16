#!/usr/bin/env python3
"""
HTML Report Generator for Model Comparison Results
Creates a human-readable HTML report from JSON comparison results
"""

import json
import argparse
from datetime import datetime
from pathlib import Path

def generate_html_report(results_file: str, output_file: str):
    """Generate an HTML report from JSON comparison results"""
    
    with open(results_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    comparison_info = data.get("comparison_info", {})
    results = data.get("results", [])
    
    html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Model Comparison Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; text-align: center; margin-bottom: 30px; }}
        h2 {{ color: #555; border-bottom: 2px solid #007acc; padding-bottom: 5px; }}
        h3 {{ color: #666; margin-top: 25px; }}
        .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }}
        .info-box {{ background-color: #f8f9fa; padding: 15px; border-radius: 6px; border-left: 4px solid #007acc; }}
        .summary {{ background-color: #e7f3ff; padding: 15px; border-radius: 6px; margin-bottom: 20px; }}
        .question-container {{ margin-bottom: 40px; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; }}
        .question-header {{ background-color: #007acc; color: white; padding: 12px; font-weight: bold; }}
        .question-category {{ background-color: #17a2b8; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; margin-left: 10px; }}
        .responses {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0; }}
        .response {{ padding: 20px; }}
        .base-response {{ background-color: #fff8dc; border-right: 1px solid #ddd; }}
        .finetuned-response {{ background-color: #f0fff0; }}
        .response-header {{ font-weight: bold; margin-bottom: 10px; color: #333; }}
        .response-meta {{ font-size: 0.9em; color: #666; margin-bottom: 10px; }}
        .response-text {{ line-height: 1.6; white-space: pre-wrap; word-wrap: break-word; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 20px; }}
        .stat-box {{ background-color: #f8f9fa; padding: 15px; border-radius: 6px; text-align: center; }}
        .stat-value {{ font-size: 1.5em; font-weight: bold; color: #007acc; }}
        .stat-label {{ color: #666; font-size: 0.9em; }}
        .improvement {{ color: #28a745; font-weight: bold; }}
        .degradation {{ color: #dc3545; font-weight: bold; }}
        .neutral {{ color: #6c757d; font-weight: bold; }}
        .toc {{ background-color: #f8f9fa; padding: 15px; border-radius: 6px; margin-bottom: 20px; }}
        .toc ul {{ list-style-type: none; padding: 0; }}
        .toc li {{ margin: 5px 0; }}
        .toc a {{ color: #007acc; text-decoration: none; }}
        .toc a:hover {{ text-decoration: underline; }}
        @media (max-width: 768px) {{
            .info-grid, .responses, .stats {{ grid-template-columns: 1fr; }}
            .response {{ border-bottom: 1px solid #ddd; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Model Comparison Report</h1>
        
        <div class="info-grid">
            <div class="info-box">
                <h3>📊 Comparison Info</h3>
                <p><strong>Generated:</strong> {timestamp}</p>
                <p><strong>Total Questions:</strong> {total_questions}</p>
            </div>
            <div class="info-box">
                <h3>🔧 Models Compared</h3>
                <p><strong>Base:</strong> {base_model_name}</p>
                <p><strong>Fine-tuned:</strong> {finetuned_model_name}</p>
            </div>
        </div>
        
        <div class="summary">
            <h2>📈 Summary Statistics</h2>
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-value">{total_questions}</div>
                    <div class="stat-label">Questions Compared</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{total_base_tokens:,}</div>
                    <div class="stat-label">Base Model Tokens</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{total_finetuned_tokens:,}</div>
                    <div class="stat-label">Fine-tuned Model Tokens</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value {token_diff_class}">{token_diff:+,}</div>
                    <div class="stat-label">Token Difference</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{avg_base_time:.2f}s</div>
                    <div class="stat-label">Base Model Avg Time</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{avg_finetuned_time:.2f}s</div>
                    <div class="stat-label">Fine-tuned Model Avg Time</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value {time_diff_class}">{time_diff:+.2f}s</div>
                    <div class="stat-label">Time Difference</div>
                </div>
            </div>
        </div>
        
        <div class="toc">
            <h2>📋 Table of Contents</h2>
            <ul>
                {toc_items}
            </ul>
        </div>
        
        <h2>💬 Question Comparisons</h2>
        {question_comparisons}
    </div>
</body>
</html>
    """
    
    # Calculate statistics
    total_questions = len(results)
    total_base_tokens = sum(r["base_model"]["tokens"] for r in results)
    total_finetuned_tokens = sum(r["finetuned_model"]["tokens"] for r in results)
    token_diff = total_finetuned_tokens - total_base_tokens
    
    avg_base_time = sum(r["base_model"]["response_time"] for r in results) / len(results) if results else 0
    avg_finetuned_time = sum(r["finetuned_model"]["response_time"] for r in results) / len(results) if results else 0
    time_diff = avg_finetuned_time - avg_base_time
    
    # Generate question comparisons HTML
    question_comparisons = ""
    toc_items = ""
    
    for i, result in enumerate(results, 1):
        question = result["question"]
        category = result.get("category", "general")
        base_response = result["base_model"]["response"]
        finetuned_response = result["finetuned_model"]["response"]
        base_tokens = result["base_model"]["tokens"]
        finetuned_tokens = result["finetuned_model"]["tokens"]
        base_time = result["base_model"]["response_time"]
        finetuned_time = result["finetuned_model"]["response_time"]
        
        # Add to TOC
        toc_items += f'<li><a href="#question{i}">{i}. {question[:60]}...</a> <span class="question-category">{category}</span></li>\\n'
        
        # Generate comparison HTML
        question_comparisons += f"""
        <div class="question-container" id="question{i}">
            <div class="question-header">
                Question {i}: {question}
                <span class="question-category">{category}</span>
            </div>
            <div class="responses">
                <div class="response base-response">
                    <div class="response-header">🔵 Base Model ({comparison_info.get('base_model', {}).get('name', 'Unknown')})</div>
                    <div class="response-meta">
                        Tokens: {base_tokens} | Time: {base_time:.2f}s
                    </div>
                    <div class="response-text">{base_response}</div>
                </div>
                <div class="response finetuned-response">
                    <div class="response-header">🟢 Fine-tuned Model ({comparison_info.get('finetuned_model', {}).get('name', 'Unknown')})</div>
                    <div class="response-meta">
                        Tokens: {finetuned_tokens} | Time: {finetuned_time:.2f}s
                    </div>
                    <div class="response-text">{finetuned_response}</div>
                </div>
            </div>
        </div>
        """
    
    # Determine improvement/degradation classes
    token_diff_class = "improvement" if token_diff < 0 else "degradation" if token_diff > 0 else "neutral"
    time_diff_class = "improvement" if time_diff < 0 else "degradation" if time_diff > 0 else "neutral"
    
    # Format timestamp
    timestamp = comparison_info.get("timestamp", datetime.now().isoformat())
    try:
        timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
    except:
        pass
    
    # Fill in the template
    html_content = html_template.format(
        timestamp=timestamp,
        total_questions=total_questions,
        base_model_name=comparison_info.get("base_model", {}).get("name", "Unknown"),
        finetuned_model_name=comparison_info.get("finetuned_model", {}).get("name", "Unknown"),
        total_base_tokens=total_base_tokens,
        total_finetuned_tokens=total_finetuned_tokens,
        token_diff=token_diff,
        token_diff_class=token_diff_class,
        avg_base_time=avg_base_time,
        avg_finetuned_time=avg_finetuned_time,
        time_diff=time_diff,
        time_diff_class=time_diff_class,
        toc_items=toc_items,
        question_comparisons=question_comparisons
    )
    
    # Write HTML file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ HTML report generated: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Generate HTML report from JSON comparison results')
    parser.add_argument('--results', required=True, help='Path to JSON results file')
    parser.add_argument('--output', required=True, help='Path to output HTML file')
    
    args = parser.parse_args()
    
    generate_html_report(args.results, args.output)

if __name__ == "__main__":
    main()
