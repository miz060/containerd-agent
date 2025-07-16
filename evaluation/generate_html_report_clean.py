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
        .original-response {{ background-color: #f8f9fa; border-top: 1px solid #ddd; padding: 15px; }}
        .original-response-header {{ font-weight: bold; margin-bottom: 10px; color: #333; }}
        .original-response-text {{ font-size: 0.9em; line-height: 1.4; color: #555; }}
        .context-info {{ background-color: #e9ecef; padding: 10px; margin-bottom: 10px; border-radius: 4px; font-size: 0.9em; }}
        .expected-topics {{ margin-top: 10px; }}
        .expected-topics ul {{ margin: 5px 0; padding-left: 20px; }}
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
                    <div class="stat-label">Total Questions</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{base_avg_tokens:,.0f}</div>
                    <div class="stat-label">Base Model Avg Tokens</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{finetuned_avg_tokens:,.0f}</div>
                    <div class="stat-label">Fine-tuned Model Avg Tokens</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value {token_diff_class}">{token_diff:+.0f}</div>
                    <div class="stat-label">Token Difference</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{base_avg_time:.1f}s</div>
                    <div class="stat-label">Base Model Avg Time</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{finetuned_avg_time:.1f}s</div>
                    <div class="stat-label">Fine-tuned Model Avg Time</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value {time_diff_class}">{time_diff:+.1f}s</div>
                    <div class="stat-label">Time Difference</div>
                </div>
            </div>
        </div>
        
        <div class="toc">
            <h2>📋 Questions Overview</h2>
            <ul>
                {toc_items}
            </ul>
        </div>
        
        <h2>💬 Detailed Comparisons</h2>
        {question_sections}
    </div>
</body>
</html>
"""

    # Calculate statistics
    base_tokens = [result["base_model"]["tokens"] for result in results]
    finetuned_tokens = [result["finetuned_model"]["tokens"] for result in results]
    base_times = [result["base_model"]["response_time"] for result in results]
    finetuned_times = [result["finetuned_model"]["response_time"] for result in results]
    
    base_avg_tokens = sum(base_tokens) / len(base_tokens) if base_tokens else 0
    finetuned_avg_tokens = sum(finetuned_tokens) / len(finetuned_tokens) if finetuned_tokens else 0
    token_diff = finetuned_avg_tokens - base_avg_tokens
    
    base_avg_time = sum(base_times) / len(base_times) if base_times else 0
    finetuned_avg_time = sum(finetuned_times) / len(finetuned_times) if finetuned_times else 0
    time_diff = finetuned_avg_time - base_avg_time
    
    # Generate table of contents
    toc_items = []
    for i, result in enumerate(results, 1):
        question_short = result["question"][:80] + "..." if len(result["question"]) > 80 else result["question"]
        category = result.get("category", "general")
        toc_items.append(f'<li><a href="#question-{i}">[{category}] {question_short}</a></li>')
    
    # Generate detailed question sections
    question_sections = []
    for i, result in enumerate(results, 1):
        question = result["question"]
        category = result.get("category", "general")
        
        # Get responses
        base_response = result["base_model"]["response"]
        finetuned_response = result["finetuned_model"]["response"]
        base_tokens = result["base_model"]["tokens"]
        finetuned_tokens = result["finetuned_model"]["tokens"]
        base_time = result["base_model"]["response_time"]
        finetuned_time = result["finetuned_model"]["response_time"]
        
        # Add context section if available
        context_section = ""
        if result.get("context") or result.get("expected_topics"):
            context_parts = []
            if result.get("context"):
                context_parts.append(f"<strong>Context:</strong> {result['context']}")
            if result.get("expected_topics"):
                topics_list = "".join([f"<li>{topic}</li>" for topic in result["expected_topics"]])
                context_parts.append(f"<strong>Expected Topics:</strong><ul>{topics_list}</ul>")
            
            context_section = f"""
            <div class="context-info">
                {"<br><br>".join(context_parts)}
            </div>
            """
        
        # Add original response section if available
        original_response_section = ""
        if result.get("original_response_summary"):
            original_response_section = f"""
            <div class="original-response">
                <div class="original-response-header">🏛️ Community Expert Answer Summary</div>
                <div class="original-response-text">{result["original_response_summary"]}</div>
            </div>
            """
        
        # Build question section
        question_section = f"""
        <div class="question-container" id="question-{i}">
            <div class="question-header">
                Question {i}
                <span class="question-category">{category}</span>
            </div>
            
            <div class="question-text" style="padding: 15px; background-color: #f8f9fa; border-bottom: 1px solid #ddd;">
                <strong>Question:</strong> {question}
            </div>
            
            {context_section}
            
            <div class="responses">
                <div class="response base-response">
                    <div class="response-header">🔵 Base Model Response</div>
                    <div class="response-meta">
                        Tokens: {base_tokens:,} | Time: {base_time:.2f}s
                    </div>
                    <div class="response-text">{base_response}</div>
                </div>
                
                <div class="response finetuned-response">
                    <div class="response-header">🟢 Fine-tuned Model Response</div>
                    <div class="response-meta">
                        Tokens: {finetuned_tokens:,} | Time: {finetuned_time:.2f}s
                    </div>
                    <div class="response-text">{finetuned_response}</div>
                </div>
            </div>
            
            {original_response_section}
        </div>
        """
        
        question_sections.append(question_section)
    
    # Helper function to get CSS class for differences
    def get_diff_class(diff):
        if diff < 0:
            return "improvement"
        elif diff > 0:
            return "degradation"
        else:
            return "neutral"
    
    # Format the HTML
    html_content = html_template.format(
        timestamp=comparison_info.get("timestamp", "Unknown"),
        total_questions=len(results),
        base_model_name=comparison_info.get("base_model", {}).get("name", "Unknown"),
        finetuned_model_name=comparison_info.get("finetuned_model", {}).get("name", "Unknown"),
        base_avg_tokens=base_avg_tokens,
        finetuned_avg_tokens=finetuned_avg_tokens,
        token_diff=token_diff,
        token_diff_class=get_diff_class(token_diff),
        base_avg_time=base_avg_time,
        finetuned_avg_time=finetuned_avg_time,
        time_diff=time_diff,
        time_diff_class=get_diff_class(time_diff),
        toc_items="\\n".join(toc_items),
        question_sections="\\n".join(question_sections)
    )
    
    # Write to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ HTML report generated: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Generate HTML report from model comparison results')
    parser.add_argument('--results', required=True, help='Path to comparison results JSON file')
    parser.add_argument('--output', required=True, help='Path to output HTML file')
    
    args = parser.parse_args()
    
    generate_html_report(args.results, args.output)

if __name__ == "__main__":
    main()
