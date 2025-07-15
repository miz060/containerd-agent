#!/usr/bin/env python3
"""
Fetch GitHub issues from containerd repository for training data generation.
Focuses on last 2 years, prioritizes bugs and questions over features.
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import requests
from dataclasses import dataclass


@dataclass
class IssueMetadata:
    """Metadata for issue prioritization"""
    id: int
    number: int
    title: str
    state: str  # open, closed
    labels: List[str]
    created_at: str
    updated_at: str
    closed_at: Optional[str]
    author: str
    assignees: List[str]
    comments_count: int
    has_maintainer_response: bool
    priority_score: float
    body_length: int
    issue_type: str  # bug, question, feature, enhancement


class GitHubIssuesFetcher:
    """Fetch and prioritize GitHub issues from containerd repository"""
    
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self.repo = "containerd/containerd"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "containerd-training-data-generator"
        }
        if self.github_token:
            self.headers["Authorization"] = f"token {self.github_token}"
        
        # Rate limiting: 5000/hour = 83/minute, we'll use 60/minute safely
        self.rate_limit_delay = 1.0  # 1 second between requests
        self.last_request_time = 0
        
        # Priority scoring weights
        self.priority_weights = {
            "closed_bonus": 2.0,
            "bug_bonus": 3.0,
            "question_bonus": 2.5,
            "feature_penalty": 0.5,
            "maintainer_response_bonus": 2.0,
            "comments_multiplier": 0.1,
            "recent_bonus": 1.0
        }
        
        # Known containerd maintainers (update as needed)
        self.maintainers = {
            "crosbymichael", "stevvooe", "dmcgowan", "estesp", "fuweid",
            "mikebrow", "dims", "thaJeztah", "AkihiroSuda", "ktock",
            "mxpv", "samuelkarp", "cpuguy83", "tianon", "arm64b"
        }
    
    def _rate_limit(self):
        """Implement rate limiting for GitHub API"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
    
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make rate-limited request to GitHub API"""
        self._rate_limit()
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ GitHub API request failed: {e}")
            return {}
    
    def _get_issue_type(self, labels: List[str]) -> str:
        """Determine issue type from labels"""
        label_names = [label.lower() for label in labels]
        
        if any(label in label_names for label in ["bug", "kind/bug", "type/bug"]):
            return "bug"
        elif any(label in label_names for label in ["question", "kind/question", "type/question", "help wanted"]):
            return "question"
        elif any(label in label_names for label in ["feature", "enhancement", "kind/feature", "type/feature"]):
            return "feature"
        else:
            return "other"
    
    def _calculate_priority_score(self, issue: Dict[str, Any], comments: List[Dict[str, Any]]) -> float:
        """Calculate priority score for issue"""
        score = 1.0
        
        # Closed issues get bonus
        if issue["state"] == "closed":
            score += self.priority_weights["closed_bonus"]
        
        # Issue type bonuses/penalties
        labels = [label["name"] for label in issue["labels"]]
        issue_type = self._get_issue_type(labels)
        
        if issue_type == "bug":
            score += self.priority_weights["bug_bonus"]
        elif issue_type == "question":
            score += self.priority_weights["question_bonus"]
        elif issue_type == "feature":
            score *= self.priority_weights["feature_penalty"]
        
        # Maintainer response bonus
        has_maintainer_response = any(
            comment["user"]["login"] in self.maintainers 
            for comment in comments
        )
        if has_maintainer_response:
            score += self.priority_weights["maintainer_response_bonus"]
        
        # Comments count bonus
        score += len(comments) * self.priority_weights["comments_multiplier"]
        
        # Recent activity bonus
        updated_at = datetime.fromisoformat(issue["updated_at"].replace('Z', '+00:00'))
        days_since_update = (datetime.now().astimezone() - updated_at).days
        if days_since_update < 365:  # Updated within last year
            score += self.priority_weights["recent_bonus"]
        
        return score
    
    def _fetch_issue_comments(self, issue_number: int) -> List[Dict[str, Any]]:
        """Fetch comments for a specific issue"""
        url = f"{self.base_url}/repos/{self.repo}/issues/{issue_number}/comments"
        comments = []
        page = 1
        
        while True:
            params = {"page": page, "per_page": 100}
            response = self._make_request(url, params)
            
            if not response or not isinstance(response, list):
                break
                
            comments.extend(response)
            
            if len(response) < 100:  # Last page
                break
                
            page += 1
        
        return comments
    
    def fetch_issues(self, max_issues: int = None) -> List[IssueMetadata]:
        """Fetch issues from the last 2 years"""
        print(f"🔍 Fetching GitHub issues from {self.repo} (last 2 years)...")
        
        # Date range: last 2 years
        since_date = (datetime.now() - timedelta(days=730)).isoformat()
        
        issues_metadata = []
        page = 1
        
        while True:
            print(f"📄 Fetching page {page}...")
            
            params = {
                "state": "all",  # Both open and closed
                "since": since_date,
                "sort": "updated",
                "direction": "desc",
                "per_page": 100,
                "page": page
            }
            
            url = f"{self.base_url}/repos/{self.repo}/issues"
            response = self._make_request(url, params)
            
            if not response or not isinstance(response, list):
                break
            
            for issue in response:
                # Skip pull requests
                if "pull_request" in issue:
                    continue
                
                print(f"  📋 Processing issue #{issue['number']}: {issue['title'][:50]}...")
                
                # Fetch comments for priority scoring
                comments = self._fetch_issue_comments(issue["number"])
                
                # Calculate priority score
                priority_score = self._calculate_priority_score(issue, comments)
                
                # Extract metadata
                labels = [label["name"] for label in issue["labels"]]
                issue_type = self._get_issue_type(labels)
                
                has_maintainer_response = any(
                    comment["user"]["login"] in self.maintainers 
                    for comment in comments
                )
                
                metadata = IssueMetadata(
                    id=issue["id"],
                    number=issue["number"],
                    title=issue["title"],
                    state=issue["state"],
                    labels=labels,
                    created_at=issue["created_at"],
                    updated_at=issue["updated_at"],
                    closed_at=issue.get("closed_at"),
                    author=issue["user"]["login"],
                    assignees=[assignee["login"] for assignee in issue["assignees"]],
                    comments_count=len(comments),
                    has_maintainer_response=has_maintainer_response,
                    priority_score=priority_score,
                    body_length=len(issue["body"] or ""),
                    issue_type=issue_type
                )
                
                issues_metadata.append(metadata)
                
                # Check if we've reached the limit (if specified)
                if max_issues and len(issues_metadata) >= max_issues:
                    break
            
            # Check if we've reached the limit (if specified)
            if max_issues and len(issues_metadata) >= max_issues:
                break
            
            if len(response) < 100:  # Last page
                break
                
            page += 1
        
        # Sort by priority score (descending)
        issues_metadata.sort(key=lambda x: x.priority_score, reverse=True)
        
        print(f"✅ Fetched {len(issues_metadata)} issues")
        return issues_metadata[:max_issues] if max_issues else issues_metadata
    
    def save_issues_metadata(self, issues: List[IssueMetadata], output_path: str):
        """Save issues metadata to JSON file"""
        metadata_dict = {
            "fetch_timestamp": datetime.now().isoformat(),
            "total_issues": len(issues),
            "repo": self.repo,
            "date_range": "last 2 years",
            "priority_weights": self.priority_weights,
            "issues": [
                {
                    "id": issue.id,
                    "number": issue.number,
                    "title": issue.title,
                    "state": issue.state,
                    "labels": issue.labels,
                    "created_at": issue.created_at,
                    "updated_at": issue.updated_at,
                    "closed_at": issue.closed_at,
                    "author": issue.author,
                    "assignees": issue.assignees,
                    "comments_count": issue.comments_count,
                    "has_maintainer_response": issue.has_maintainer_response,
                    "priority_score": issue.priority_score,
                    "body_length": issue.body_length,
                    "issue_type": issue.issue_type
                }
                for issue in issues
            ]
        }
        
        with open(output_path, 'w') as f:
            json.dump(metadata_dict, f, indent=2)
        
        print(f"💾 Saved issues metadata to {output_path}")
    
    def print_summary(self, issues: List[IssueMetadata]):
        """Print summary of fetched issues"""
        print(f"\n📊 Issues Summary:")
        print(f"Total issues: {len(issues)}")
        
        # By state
        open_count = sum(1 for i in issues if i.state == "open")
        closed_count = sum(1 for i in issues if i.state == "closed")
        print(f"Open: {open_count}, Closed: {closed_count}")
        
        # By type
        type_counts = {}
        for issue in issues:
            type_counts[issue.issue_type] = type_counts.get(issue.issue_type, 0) + 1
        
        print("By type:")
        for issue_type, count in sorted(type_counts.items()):
            print(f"  {issue_type}: {count}")
        
        # Top priority issues
        print(f"\n🔝 Top 10 Priority Issues:")
        for i, issue in enumerate(issues[:10], 1):
            print(f"{i:2d}. #{issue.number} ({issue.priority_score:.1f}): {issue.title[:60]}...")


def main():
    """Main function to fetch GitHub issues"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch GitHub issues for training data")
    parser.add_argument("--max-issues", type=int, default=None, help="Maximum number of issues to fetch (default: all issues from last 2 years)")
    parser.add_argument("--output-path", default="output/github_issues_metadata.json", help="Output path for metadata")
    
    args = parser.parse_args()
    
    # Check for GitHub token
    if not os.getenv("GITHUB_TOKEN"):
        print("⚠️  GITHUB_TOKEN environment variable not set. Rate limiting will be more restrictive.")
        print("   Get a token at: https://github.com/settings/tokens")
    
    # Initialize fetcher
    fetcher = GitHubIssuesFetcher()
    
    # Fetch issues
    issues = fetcher.fetch_issues(max_issues=args.max_issues)
    
    # Save metadata
    os.makedirs(os.path.dirname(args.output_path), exist_ok=True)
    fetcher.save_issues_metadata(issues, args.output_path)
    
    # Print summary
    fetcher.print_summary(issues)


if __name__ == "__main__":
    main()
