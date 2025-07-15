#!/usr/bin/env python3
"""
Generate training data from GitHub issues using Azure OpenAI GPT-4o.
Processes issues fetched by fetch_github_issues.py and creates high-quality Q&A pairs.
"""

import json
import os
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests
from openai import AzureOpenAI
from azure.identity import AzureCliCredential, get_bearer_token_provider
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.qa_allocation import calculate_qa_allocation, print_allocation_summary


class IssueTrainingDataGenerator:
    """Generate training data from GitHub issues using Azure OpenAI"""
    
    def __init__(self, azure_endpoint: str = None, deployment: str = "gpt-4o"):
        # Azure OpenAI setup (same as code-scanner)
        self.azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.deployment = deployment or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        
        if not self.azure_endpoint:
            raise ValueError(
                "Azure OpenAI endpoint must be provided via --azure-endpoint parameter or AZURE_OPENAI_ENDPOINT environment variable.\n"
                "Example: export AZURE_OPENAI_ENDPOINT='https://your-resource-name.openai.azure.com/'"
            )
        
        # Initialize Azure OpenAI client
        token_provider = get_bearer_token_provider(AzureCliCredential(), "https://cognitiveservices.azure.com/.default")
        self.client = AzureOpenAI(
            azure_endpoint=self.azure_endpoint,
            azure_ad_token_provider=token_provider,
            api_version="2024-02-01"
        )
        
        # GitHub API setup
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self.repo = "containerd/containerd"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "containerd-training-data-generator"
        }
        if self.github_token:
            self.headers["Authorization"] = f"token {self.github_token}"
        
        # Rate limiting (same as code-scanner)
        self.max_issues_per_minute = 6  # Conservative for 100K TPM
        self.max_qa_entries_per_minute = 30  # Conservative for 100K TPM (assuming ~3K tokens per entry)
        self.github_rate_limit_delay = 1.0  # 1 second between GitHub API calls
        self.last_github_request_time = 0
        self.last_openai_request_time = 0
        self.qa_entries_this_minute = 0
        self.minute_start_time = time.time()
        
        # Training data generation stats
        self.stats = {
            "total_issues_processed": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "total_qa_pairs": 0,
            "total_tokens_used": 0,
            "estimated_cost": 0.0
        }
    
    def _rate_limit_github(self):
        """Rate limit GitHub API calls"""
        current_time = time.time()
        elapsed = current_time - self.last_github_request_time
        if elapsed < self.github_rate_limit_delay:
            time.sleep(self.github_rate_limit_delay - elapsed)
        self.last_github_request_time = time.time()
    
    def _rate_limit_openai(self):
        """Rate limit OpenAI API calls with both per-minute and per-issue limits"""
        current_time = time.time()
        
        # Check if we've exceeded Q&A entries per minute
        if current_time - self.minute_start_time >= 60:
            # Reset minute counter
            self.qa_entries_this_minute = 0
            self.minute_start_time = current_time
        
        # Rate limit based on issues per minute
        elapsed = current_time - self.last_openai_request_time
        min_delay = 60.0 / self.max_issues_per_minute
        
        if elapsed < min_delay:
            sleep_time = min_delay - elapsed
            print(f"⏰ Rate limiting: sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
        
        self.last_openai_request_time = time.time()
    
    def _check_qa_rate_limit(self, expected_qa_pairs: int):
        """Check if we can generate the expected number of Q&A pairs without exceeding rate limits"""
        current_time = time.time()
        
        # Check if we've exceeded Q&A entries per minute
        if current_time - self.minute_start_time >= 60:
            # Reset minute counter
            self.qa_entries_this_minute = 0
            self.minute_start_time = current_time
        
        # Check if adding expected pairs would exceed limit
        if self.qa_entries_this_minute + expected_qa_pairs > self.max_qa_entries_per_minute:
            # Calculate sleep time to wait for next minute
            sleep_time = 60 - (current_time - self.minute_start_time)
            if sleep_time > 0:
                print(f"⏰ Q&A rate limit: waiting {sleep_time:.1f}s for next minute")
                time.sleep(sleep_time)
                self.qa_entries_this_minute = 0
                self.minute_start_time = time.time()
    
    def _update_qa_rate_limit(self, actual_qa_pairs: int):
        """Update the Q&A rate limit counter"""
        self.qa_entries_this_minute += actual_qa_pairs
    
    def _get_issue_details(self, issue_number: int) -> Dict[str, Any]:
        """Fetch full issue details including comments"""
        self._rate_limit_github()
        
        # Get issue details
        issue_url = f"{self.base_url}/repos/{self.repo}/issues/{issue_number}"
        try:
            response = requests.get(issue_url, headers=self.headers)
            response.raise_for_status()
            issue = response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to fetch issue #{issue_number}: {e}")
            return {}
        
        # Get comments
        comments_url = f"{self.base_url}/repos/{self.repo}/issues/{issue_number}/comments"
        comments = []
        page = 1
        
        while True:
            self._rate_limit_github()
            try:
                params = {"page": page, "per_page": 100}
                response = requests.get(comments_url, headers=self.headers, params=params)
                response.raise_for_status()
                page_comments = response.json()
                
                if not page_comments:
                    break
                
                comments.extend(page_comments)
                
                if len(page_comments) < 100:
                    break
                
                page += 1
            except requests.exceptions.RequestException as e:
                print(f"⚠️  Failed to fetch comments for issue #{issue_number}: {e}")
                break
        
        return {
            "issue": issue,
            "comments": comments
        }
    
    def _calculate_qa_allocation(self, issues: List[Dict[str, Any]], max_qa_entries: int) -> Dict[int, int]:
        """Calculate weighted allocation of Q&A pairs based on priority scores"""
        return calculate_qa_allocation(
            items=issues,
            max_qa_entries=max_qa_entries,
            priority_field="priority_score",
            id_field="number"
        )
    
    def _create_training_prompt(self, issue_data: Dict[str, Any], qa_count: int = 3) -> str:
        """Create prompt for GPT-4o to generate training data"""
        issue = issue_data["issue"]
        comments = issue_data["comments"]
        
        # Prepare issue content
        issue_content = f"""
ISSUE #{issue['number']}: {issue['title']}

Status: {issue['state']}
Labels: {', '.join([label['name'] for label in issue['labels']])}
Created: {issue['created_at']}
Author: {issue['user']['login']}

DESCRIPTION:
{issue['body'] or 'No description provided'}

DISCUSSION:
"""
        
        # Add comments (limit to most relevant ones)
        for i, comment in enumerate(comments[:20]):  # Limit to first 20 comments
            issue_content += f"""
Comment #{i+1} by {comment['user']['login']} ({comment['created_at']}):
{comment['body']}

---
"""
        
        # Create the prompt with dynamic Q&A count
        prompt = f"""You are an expert in containerd, container runtime, and cloud-native technologies. 

Based on the following GitHub issue discussion, generate exactly {qa_count} high-quality training Q&A pairs that would help someone learn about containerd and related technologies.

Focus on:
1. Technical problem-solving patterns
2. Best practices and recommendations  
3. Common issues and their solutions
4. Architecture and design concepts
5. Troubleshooting approaches

Generate questions that are:
- Specific and actionable
- Technically accurate
- Relevant to containerd ecosystem
- Educational and practical

Generate answers that are:
- Comprehensive but concise
- Technically correct
- Include context and reasoning
- Mention relevant containerd concepts

{issue_content}

Generate exactly {qa_count} training Q&A pairs as a JSON array. Use proper JSON escaping for quotes and newlines.

Return only this JSON array with no markdown formatting:

[
  {{
    "question": "Your question here",
    "answer": "Your detailed answer here"
  }},
  {{
    "question": "Your next question here", 
    "answer": "Your next detailed answer here"
  }}
]

CRITICAL: Return only the JSON array. Use proper JSON escaping. No markdown blocks. No explanations."""
        
        return prompt
    
    def _generate_training_data(self, issue_data: Dict[str, Any], qa_count: int = 3) -> List[Dict[str, str]]:
        """Generate training data for a single issue using GPT-4o"""
        issue = issue_data["issue"]
        
        try:
            # Check rate limits before proceeding
            self._check_qa_rate_limit(qa_count)
            self._rate_limit_openai()
            
            prompt = self._create_training_prompt(issue_data, qa_count)
            
            print(f"  🤖 Generating {qa_count} training Q&A pairs for issue #{issue['number']}...")
            
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in containerd and container technologies. Generate high-quality training data from GitHub issues."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            # Parse the response
            response_content = response.choices[0].message.content.strip()
            
            # Extract JSON from response with better error handling
            if "```json" in response_content:
                json_start = response_content.find("```json") + 7
                json_end = response_content.find("```", json_start)
                if json_end == -1:
                    json_end = len(response_content)
                json_content = response_content[json_start:json_end].strip()
            else:
                json_content = response_content.strip()
            
            # Try to parse JSON with multiple strategies
            qa_pairs = None
            
            # Strategy 1: Direct JSON parsing
            try:
                qa_pairs = json.loads(json_content)
            except json.JSONDecodeError as e:
                print(f"  ⚠️  JSON parse error (attempt 1): {e}")
                
                # Strategy 2: Try to fix common JSON issues
                try:
                    # Remove any trailing commas and fix common issues
                    fixed_json = json_content.replace(",]", "]").replace(",}", "}")
                    # Try to find and extract just the array part
                    if "[" in fixed_json and "]" in fixed_json:
                        start = fixed_json.find("[")
                        end = fixed_json.rfind("]") + 1
                        fixed_json = fixed_json[start:end]
                    qa_pairs = json.loads(fixed_json)
                except json.JSONDecodeError as e2:
                    print(f"  ⚠️  JSON parse error (attempt 2): {e2}")
                    
                    # Strategy 3: Try to regenerate with simpler prompt
                    print(f"  🔄 Attempting to regenerate with simpler prompt...")
                    try:
                        simple_prompt = f"""Generate {qa_count} Q&A pairs about containerd from this GitHub issue. Return only valid JSON array.

Issue: {issue['title']}

Format:
[{{"question": "...", "answer": "..."}}, {{"question": "...", "answer": "..."}}]"""
                        
                        retry_response = self.client.chat.completions.create(
                            model=self.deployment,
                            messages=[
                                {"role": "system", "content": "Generate only valid JSON. No markdown, no explanations."},
                                {"role": "user", "content": simple_prompt}
                            ],
                            temperature=0.3,
                            max_tokens=1500
                        )
                        
                        retry_content = retry_response.choices[0].message.content.strip()
                        # Clean up any markdown
                        if "```" in retry_content:
                            retry_content = retry_content.split("```")[1].replace("json", "").strip()
                        
                        qa_pairs = json.loads(retry_content)
                        
                        # Update token usage for retry
                        self.stats["total_tokens_used"] += retry_response.usage.total_tokens
                        self.stats["estimated_cost"] += (
                            retry_response.usage.prompt_tokens * 0.005 / 1000 +
                            retry_response.usage.completion_tokens * 0.015 / 1000
                        )
                        
                    except Exception as e3:
                        print(f"  ❌ All JSON parsing strategies failed: {e3}")
                        return []
            
            if qa_pairs is None:
                print(f"⚠️  Could not parse response for issue #{issue['number']}")
                return []
            
            if not isinstance(qa_pairs, list):
                print(f"⚠️  Invalid response format for issue #{issue['number']} (not a list)")
                return []
            
            # Validate Q&A pairs
            valid_pairs = []
            for pair in qa_pairs:
                if isinstance(pair, dict) and "question" in pair and "answer" in pair:
                    # Clean up the strings
                    question = str(pair["question"]).strip()
                    answer = str(pair["answer"]).strip()
                    
                    if question and answer:  # Only include non-empty pairs
                        valid_pairs.append({
                            "question": question,
                            "answer": answer
                        })
            
            # Update stats
            self.stats["total_tokens_used"] += response.usage.total_tokens
            self.stats["estimated_cost"] += (
                response.usage.prompt_tokens * 0.005 / 1000 +  # Input cost
                response.usage.completion_tokens * 0.015 / 1000  # Output cost
            )
            
            # Update Q&A rate limit counter
            self._update_qa_rate_limit(len(valid_pairs))
            
            print(f"  ✅ Generated {len(valid_pairs)} Q&A pairs")
            return valid_pairs
            
        except Exception as e:
            print(f"❌ Error generating training data for issue #{issue['number']}: {e}")
            # Log the raw response for debugging if available
            if 'response_content' in locals():
                print(f"   Raw response preview: {response_content[:200]}...")
            return []
            # Log the raw response for debugging if available
            if 'response_content' in locals():
                print(f"   Raw response preview: {response_content[:200]}...")
            return []
    
    def _convert_to_chat_format(self, qa_pairs: List[Dict[str, str]], issue_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert Q&A pairs to chat format for fine-tuning"""
        chat_examples = []
        
        for pair in qa_pairs:
            chat_example = {
                "messages": [
                    {
                        "role": "user",
                        "content": pair["question"]
                    },
                    {
                        "role": "assistant", 
                        "content": pair["answer"]
                    }
                ],
                "metadata": {
                    "source": "github_issue",
                    "issue_number": issue_metadata["number"],
                    "issue_title": issue_metadata["title"],
                    "issue_type": issue_metadata["issue_type"],
                    "priority_score": issue_metadata["priority_score"]
                }
            }
            chat_examples.append(chat_example)
        
        return chat_examples
    
    def generate_training_data(self, issues_metadata_path: str, output_path: str, max_issues: int = None, max_qa_entries: int = 3000):
        """Generate training data from fetched issues with weighted allocation"""
        print(f"🎯 Generating training data from GitHub issues...")
        
        # Load issues metadata
        with open(issues_metadata_path, 'r') as f:
            metadata = json.load(f)
        
        # Use all issues if max_issues is None or greater than available issues
        all_issues = metadata["issues"]
        if max_issues is None or max_issues > len(all_issues):
            issues = all_issues
            print(f"📋 Processing ALL {len(issues)} issues...")
        else:
            issues = all_issues[:max_issues]
            print(f"📋 Processing {len(issues)} of {len(all_issues)} issues...")
        
        # Calculate weighted allocation of Q&A pairs
        qa_allocation = self._calculate_qa_allocation(issues, max_qa_entries)
        
        # Print allocation summary using utility function
        print_allocation_summary(
            items=issues,
            allocation=qa_allocation,
            priority_field="priority_score",
            id_field="number",
            title_field="title",
            max_display=20
        )
        
        # Estimate time and cost
        total_allocated = sum(qa_allocation.values())
        estimated_time_hours = len(issues) / (self.max_issues_per_minute * 60)
        estimated_cost = total_allocated * 0.20  # Rough estimate: $0.20 per Q&A pair
        print(f"⏱️  Estimated processing time: {estimated_time_hours:.1f} hours")
        print(f"💰 Estimated cost: ${estimated_cost:.2f}")
        
        print(f"\n🚀 Starting training data generation at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
        start_time = time.time()
        
        all_training_data = []
        
        for i, issue_metadata in enumerate(issues, 1):
            issue_num = issue_metadata["number"]
            
            # Skip if not in allocation (shouldn't happen, but safety check)
            if issue_num not in qa_allocation:
                continue
            
            qa_count = qa_allocation[issue_num]
            
            # Progress tracking
            elapsed_time = time.time() - start_time
            progress_percent = (i / len(issues)) * 100
            
            print(f"\n📄 Processing issue {i}/{len(issues)} ({progress_percent:.1f}%): #{issue_num}")
            print(f"   Title: {issue_metadata['title']}")
            print(f"   Type: {issue_metadata['issue_type']}, Priority: {issue_metadata['priority_score']:.1f}")
            print(f"   Generating {qa_count} Q&A pairs")
            print(f"   ⏱️  Elapsed: {elapsed_time/3600:.1f}h, Current Q&A rate: {self.stats['total_qa_pairs']/(elapsed_time/3600):.1f}/hour")
            
            # Save intermediate results every 50 issues
            if i % 50 == 0:
                print(f"   💾 Saving intermediate results...")
                intermediate_path = output_path.replace('.jsonl', f'_intermediate_{i}.jsonl')
                with open(intermediate_path, 'w') as f:
                    for example in all_training_data:
                        f.write(json.dumps(example) + '\n')
                print(f"   ✅ Saved {len(all_training_data)} examples to {intermediate_path}")
            
            # Fetch full issue details
            issue_data = self._get_issue_details(issue_num)
            
            if not issue_data:
                self.stats["failed_generations"] += 1
                continue
            
            # Generate training data with specific Q&A count
            qa_pairs = self._generate_training_data(issue_data, qa_count)
            
            if qa_pairs:
                # Convert to chat format
                chat_examples = self._convert_to_chat_format(qa_pairs, issue_metadata)
                all_training_data.extend(chat_examples)
                
                self.stats["successful_generations"] += 1
                self.stats["total_qa_pairs"] += len(qa_pairs)
            else:
                self.stats["failed_generations"] += 1
            
            self.stats["total_issues_processed"] += 1
        
        # Save training data
        print(f"\n💾 Saving training data to {output_path}...")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w') as f:
            for example in all_training_data:
                f.write(json.dumps(example) + '\n')
        
        # Save metadata
        metadata_path = output_path.replace('.jsonl', '_metadata.json')
        training_metadata = {
            "generation_timestamp": datetime.now().isoformat(),
            "source_metadata_file": issues_metadata_path,
            "total_issues_processed": self.stats["total_issues_processed"],
            "successful_generations": self.stats["successful_generations"],
            "failed_generations": self.stats["failed_generations"],
            "total_training_examples": len(all_training_data),
            "total_qa_pairs": self.stats["total_qa_pairs"],
            "total_tokens_used": self.stats["total_tokens_used"],
            "estimated_cost": self.stats["estimated_cost"],
            "azure_endpoint": self.azure_endpoint,
            "deployment": self.deployment
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(training_metadata, f, indent=2)
        
        # Final summary
        total_time = time.time() - start_time
        print(f"\n✅ Training data generation complete!")
        print(f"⏱️  Total processing time: {total_time/3600:.1f} hours ({total_time/60:.1f} minutes)")
        print(f"📊 Generated {len(all_training_data)} training examples from {self.stats['total_qa_pairs']} Q&A pairs")
        print(f"� Average Q&A generation rate: {self.stats['total_qa_pairs']/(total_time/3600):.1f} Q&A pairs/hour")
        print(f"�💰 Final estimated cost: ${self.stats['estimated_cost']:.2f}")
        print(f"🔢 Total tokens used: {self.stats['total_tokens_used']:,}")
        print(f"✅ Success rate: {self.stats['successful_generations']}/{self.stats['total_issues_processed']} ({(self.stats['successful_generations']/self.stats['total_issues_processed']*100):.1f}%)")
        print(f"🏁 Completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    """Main function to generate training data from GitHub issues"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate training data from GitHub issues")
    parser.add_argument("--issues-metadata", default="output/github_issues_metadata_all.json", 
                       help="Path to issues metadata JSON file")
    parser.add_argument("--output-path", default="output/github_issues_training_data_full.jsonl",
                       help="Output path for training data")
    parser.add_argument("--max-issues", type=int, default=None,
                       help="Maximum number of issues to process (None = all issues)")
    parser.add_argument("--max-qa-entries", type=int, default=3000,
                       help="Maximum total Q&A entries to generate (allocated by priority)")
    parser.add_argument("--azure-endpoint", 
                       help="Azure OpenAI endpoint (or use AZURE_OPENAI_ENDPOINT env var)")
    parser.add_argument("--deployment", default="gpt-4o",
                       help="Azure OpenAI deployment name")
    parser.add_argument("--max-issues-per-minute", type=int, default=6,
                       help="Maximum issues to process per minute (rate limiting)")
    parser.add_argument("--max-qa-entries-per-minute", type=int, default=30,
                       help="Maximum Q&A entries to generate per minute (TPM-based rate limiting)")
    
    args = parser.parse_args()
    
    # Initialize generator
    try:
        generator = IssueTrainingDataGenerator(
            azure_endpoint=args.azure_endpoint,
            deployment=args.deployment
        )
        generator.max_issues_per_minute = args.max_issues_per_minute
        generator.max_qa_entries_per_minute = args.max_qa_entries_per_minute
        
        # Generate training data
        generator.generate_training_data(
            issues_metadata_path=args.issues_metadata,
            output_path=args.output_path,
            max_issues=args.max_issues,
            max_qa_entries=args.max_qa_entries
        )
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
