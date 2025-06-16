import logging
import os
import json
from typing import Dict, Any, Optional, List
from anthropic import Anthropic
from anthropic.types import Message

from ..models.commit import CommitCollection, CommitType
from ..models.post import PostType, PostTemplate
from .config import settings

logger = logging.getLogger(__name__)

class ClaudeClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.anthropic_api_key
        self.client = Anthropic(api_key=self.api_key)
        self.model = settings.claude_model
        
    def load_main_prompt(self) -> str:
        """Load the main prompt template"""
        prompt_file = os.path.join("app", "prompts", "main_prompt.txt")
        
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Main prompt file {prompt_file} not found!")
            raise
        except Exception as e:
            logger.error(f"Error loading main prompt: {e}")
            raise
    
    def _prepare_commit_data_for_prompt(self, commits: CommitCollection) -> Dict[str, Any]:
        """Prepare commit data in a format suitable for the prompt"""
        
        # Summarize commits by type
        commit_summary = {}
        for commit_type, count in commits.commit_types.items():
            commit_summary[commit_type.value] = {
                "count": count,
                "examples": []
            }
        
        # Add examples for each type
        for commit in commits.commits[:20]:  # Limit to first 20 commits
            commit_type = commit.commit_type.value
            if len(commit_summary[commit_type]["examples"]) < 3:
                commit_summary[commit_type]["examples"].append({
                    "message": commit.message.split('\n')[0][:100],
                    "files": min(commit.files_count, 5),
                    "additions": commit.additions,
                    "deletions": commit.deletions
                })
        
        # File changes summary
        top_files = commits.most_changed_files[:10]
        
        # Contributor summary
        top_contributors = commits.top_contributors[:5]
        
        return {
            "time_period": f"{commits.time_period_hours:.1f} hours",
            "total_commits": commits.total_commits,
            "total_additions": commits.total_additions,
            "total_deletions": commits.total_deletions,
            "total_files_changed": commits.total_files_changed,
            "commits_per_hour": f"{commits.commits_per_hour:.1f}",
            "commit_summary": commit_summary,
            "top_files": top_files,
            "top_contributors": top_contributors,
            "breaking_changes": commits.breaking_changes,
            "security_updates": commits.security_updates,
            "repository": commits.repository
        }
    
    def _determine_post_type(self, commits: CommitCollection) -> PostType:
        """Determine the best post type based on commit analysis"""
        
        if not commits.commits:
            return PostType.GENERAL_UPDATE
        
        # Check for security updates
        if commits.security_updates > 0:
            return PostType.SECURITY_UPDATE
        
        # Check for breaking changes or major features
        if commits.breaking_changes > 0:
            return PostType.FEATURE_ANNOUNCEMENT
        
        # Check commit type distribution
        total_commits = commits.total_commits
        if total_commits == 0:
            return PostType.GENERAL_UPDATE
        
        feature_ratio = commits.commit_types.get(CommitType.FEATURE, 0) / total_commits
        bugfix_ratio = commits.commit_types.get(CommitType.BUGFIX, 0) / total_commits
        performance_ratio = commits.commit_types.get(CommitType.PERFORMANCE, 0) / total_commits
        
        if feature_ratio > 0.4:
            return PostType.FEATURE_ANNOUNCEMENT
        elif bugfix_ratio > 0.5:
            return PostType.BUG_FIX_SUMMARY
        elif performance_ratio > 0.3:
            return PostType.PERFORMANCE_IMPROVEMENT
        else:
            return PostType.GENERAL_UPDATE
    
    def _select_template(self, post_type: PostType) -> PostTemplate:
        """Select appropriate template based on post type"""
        template_mapping = {
            PostType.FEATURE_ANNOUNCEMENT: PostTemplate.FEATURE,
            PostType.BUG_FIX_SUMMARY: PostTemplate.BUGFIX,
            PostType.SECURITY_UPDATE: PostTemplate.SECURITY,
            PostType.PERFORMANCE_IMPROVEMENT: PostTemplate.PERFORMANCE,
            PostType.GENERAL_UPDATE: PostTemplate.GENERAL,
            PostType.RELEASE_NOTES: PostTemplate.GENERAL,
            PostType.DEVELOPMENT_PROGRESS: PostTemplate.GENERAL
        }
        
        return template_mapping.get(post_type, PostTemplate.GENERAL)
    
    def generate_post_content(
        self, 
        commits: CommitCollection, 
        target_audience: str = "general",
        force_template: Optional[PostTemplate] = None
    ) -> Dict[str, Any]:
        """Generate post content using Claude with automatic template selection"""
        
        try:
            # Load the main prompt
            prompt_template = self.load_main_prompt()
            
            # Prepare commit data
            commit_data = self._prepare_commit_data_for_prompt(commits)
            
            # Build the prompt
            prompt = prompt_template.format(
                repository=commits.repository,
                target_audience=target_audience,
                commit_data=json.dumps(commit_data, indent=2),
                time_period=f"{commits.time_period_hours:.1f} hours"
            )
            
            logger.info(f"Generating post content with Claude for {commits.repository}")
            
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.7,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Parse response
            content = response.content[0].text
            
            # Try to parse JSON response
            try:
                parsed_content = json.loads(content)
                logger.info(f"Claude returned JSON: {list(parsed_content.keys())}")
                
                # Check if Claude returned multiple posts
                if "posts" in parsed_content and isinstance(parsed_content["posts"], list) and len(parsed_content["posts"]) > 0:
                    logger.info(f"Claude returned {len(parsed_content['posts'])} posts")
                    return {
                        "content": parsed_content,  # Return the whole structure
                        "tokens_used": response.usage.input_tokens + response.usage.output_tokens
                    }
                else:
                    # Single post format - use as-is
                    logger.info("Claude returned single post format")
                    return {
                        "post_type": self._determine_post_type(commits),
                        "template": self._select_template(self._determine_post_type(commits)),
                        "content": parsed_content,
                        "tokens_used": response.usage.input_tokens + response.usage.output_tokens
                    }
                    
            except json.JSONDecodeError:
                logger.warning("Claude didn't return valid JSON, creating fallback response")
                # Fallback response
                parsed_content = {
                    "template_type": "general",
                    "title": f"🚀 Updates from {commits.repository}",
                    "summary": f"Latest development activity with {commits.total_commits} commits",
                    "detailed_explanation": "The development team has been busy with improvements and updates.",
                    "technical_highlights": [f"{commits.total_commits} commits with {commits.total_files_changed} files updated"],
                    "user_benefits": ["Improved stability", "Better performance", "Enhanced features"],
                    "code_snippets": [],
                    "tags": [commits.repository.split('/')[-1]],
                    "hashtags": ["#coding", "#opensource", "#development"]
                }
                
                return {
                    "post_type": PostType.GENERAL_UPDATE,
                    "template": PostTemplate.GENERAL,
                    "content": parsed_content,
                    "tokens_used": response.usage.input_tokens + response.usage.output_tokens
                }
            
        except Exception as e:
            logger.error(f"Error generating post content: {e}")
            raise
    
    def generate_chart_suggestions(self, commits: CommitCollection) -> List[Dict[str, Any]]:
        """Generate suggestions for charts based on commit data"""
        
        charts = []
        
        # Commit types chart
        if commits.commit_types:
            charts.append({
                "chart_type": "pie",
                "title": "Commit Types Distribution",
                "data": {
                    "labels": [ct.value.title() for ct in commits.commit_types.keys()],
                    "values": list(commits.commit_types.values())
                },
                "description": "Breakdown of different types of commits"
            })
        
        # Progress bar for implementation
        if commits.total_commits > 0:
            completion_percentage = min(95, (commits.total_commits * 10))  # Mock calculation
            charts.append({
                "chart_type": "progress",
                "title": "Development Progress",
                "data": {
                    "percentage": completion_percentage,
                    "label": f"{commits.total_commits} commits this period"
                },
                "description": "Current development activity"
            })
        
        # File changes chart
        if commits.most_changed_files:
            top_files = commits.most_changed_files[:5]
            charts.append({
                "chart_type": "bar",
                "title": "Most Active Files",
                "data": {
                    "labels": [f.get("filename", "").split('/')[-1] for f in top_files],
                    "values": [f.get("changes", 0) for f in top_files]
                },
                "description": "Files with the most changes"
            })
        
        # Contributors chart
        if commits.top_contributors:
            charts.append({
                "chart_type": "bar",
                "title": "Top Contributors",
                "data": {
                    "labels": [c.get("name", "Unknown")[:10] for c in commits.top_contributors[:5]],
                    "values": [c.get("commits", 0) for c in commits.top_contributors[:5]]
                },
                "description": "Most active contributors"
            })
        
        return charts
    
    def test_connection(self) -> bool:
        """Test connection to Claude API"""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[
                    {
                        "role": "user", 
                        "content": "Hello"
                    }
                ]
            )
            return True
        except Exception as e:
            logger.error(f"Claude API connection test failed: {e}")
            return False