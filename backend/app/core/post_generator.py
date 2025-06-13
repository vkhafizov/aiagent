# backend/app/core/post_generator.py - FIXED VERSION
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4

from ..models.post import (
    Post, PostContent, PostMetrics, PostType, PostTemplate,
    PostGenerationRequest, PostGenerationResponse
)
from ..models.commit import CommitCollection
from .claude_client import ClaudeClient
from .config import settings
from ..utils.template_selector import TemplateSelector
from ..utils.html_generator import HTMLGenerator

logger = logging.getLogger(__name__)

class PostGenerator:
    """Core post generation service that orchestrates the entire process"""
    
    def __init__(self):
        self.claude_client = ClaudeClient()
        self.template_selector = TemplateSelector()
        self.html_generator = HTMLGenerator()
    
    async def generate_post(self, request: PostGenerationRequest, commits: CommitCollection) -> PostGenerationResponse:
        """Generate a complete post from commits"""
        start_time = datetime.now()
        
        try:
            logger.info(f"Generating post for {request.repository} ({request.time_period})")
            
            # Generate AI content - FIXED: removed await and fixed parameters
            ai_content = self.claude_client.generate_post_content(
                commits=commits,
                target_audience=getattr(request, 'target_audience', 'general'),
                force_template=getattr(request, 'force_template', None)
            )
            
            if not ai_content:
                return PostGenerationResponse(
                    success=False,
                    error_message="Failed to generate AI content",
                    generation_time_seconds=0.0
                )
            
            # Create post object
            
            content_data = ai_content.get("content", {})  # ✅ ДОБАВЬТЕ ЭТУ СТРОКУ
            post = Post(
                id=str(uuid4()),
                post_type=self._determine_post_type(content_data),  # ✅ ИЗМЕНЕНО
                template=self._get_template_from_ai_content(content_data),  # ✅ ИЗМЕНЕНО
                content=PostContent(
                    title=content_data.get("title", "Repository Update"),  # ✅ ИЗМЕНЕНО
                    summary=content_data.get("summary", ""),  # ✅ ИЗМЕНЕНО
                    detailed_explanation=content_data.get("detailed_explanation", ""),  # ✅ ИЗМЕНЕНО
                    technical_highlights=content_data.get("technical_highlights", []),  # ✅ ИЗМЕНЕНО
                    user_benefits=content_data.get("user_benefits", []),  # ✅ ИЗМЕНЕНО
                    code_snippets=content_data.get("code_snippets", []),  # ✅ ИЗМЕНЕНО
                    tags=content_data.get("tags", []),  # ✅ ИЗМЕНЕНО
                    hashtags=content_data.get("hashtags", [])  # ✅ ИЗМЕНЕНО
                ),
                metrics=self._calculate_metrics(commits, request.time_period),
                created_at=datetime.now(),
                repository=request.repository,
                time_period=request.time_period,
                source_commits=[commit.sha for commit in commits.commits[:10]]  # Limit to 10
            )
            
            # Generate HTML
            html_content = self.html_generator.generate_html(post)
            post.html_content = html_content
            
            # Save to file
            output_path = self._save_post_to_file(post)
            post.output_file_path = output_path
            
            generation_time = (datetime.now() - start_time).total_seconds()
            
            return PostGenerationResponse(
                success=True,
                post=post,
                generation_time_seconds=generation_time
            )
            
        except Exception as e:
            logger.error(f"Error generating post: {e}")
            generation_time = (datetime.now() - start_time).total_seconds()
            
            return PostGenerationResponse(
                success=False,
                error_message=str(e),
                generation_time_seconds=generation_time
            )
    
    def _save_post_to_file(self, post: Post) -> str:
        """Save post HTML to file with proper path handling"""
        try:
            # Create output directory
            output_dir = os.path.join(settings.output_dir, post.time_period)
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate filename
            timestamp = post.created_at.strftime("%Y%m%d_%H%M%S")
            safe_repo = post.repository.replace('/', '_').replace('\\', '_')
            filename = f"{safe_repo}_{post.time_period}_{timestamp}.html"
            
            # Full file path
            file_path = os.path.join(output_dir, filename)
            
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(post.html_content)
            
            logger.info(f"Saved post to: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving post to file: {e}")
            raise
    
    def _determine_post_type(self, ai_content: Dict[str, Any]) -> PostType:
        """Determine post type from AI content"""
        template_type = ai_content.get("template_type", "general")
        
        mapping = {
            "feature": PostType.FEATURE_ANNOUNCEMENT,
            "bugfix": PostType.BUG_FIX_SUMMARY,
            "security": PostType.SECURITY_UPDATE,
            "performance": PostType.PERFORMANCE_IMPROVEMENT,
            "general": PostType.GENERAL_UPDATE
        }
        
        return mapping.get(template_type, PostType.GENERAL_UPDATE)
    
    def _get_template_from_ai_content(self, ai_content: Dict[str, Any]) -> PostTemplate:
        """Get PostTemplate enum from AI content"""
        template_type = ai_content.get("template_type", "general")
        
        mapping = {
            "feature": PostTemplate.FEATURE,
            "bugfix": PostTemplate.BUGFIX,
            "security": PostTemplate.SECURITY,
            "performance": PostTemplate.PERFORMANCE,
            "general": PostTemplate.GENERAL
        }
        
        return mapping.get(template_type, PostTemplate.GENERAL)
    
    def _calculate_metrics(self, commits: CommitCollection, time_period: str) -> PostMetrics:
        """Calculate metrics from commits - FIXED all attribute names"""
        # FIXED: Use correct attribute names from Commit model
        total_additions = sum(commit.additions for commit in commits.commits)
        total_deletions = sum(commit.deletions for commit in commits.commits)
        total_files = sum(len(commit.files_changed) for commit in commits.commits)
        
        # Count unique contributors - FIXED: use username instead of login
        contributors = set(
            commit.author.username for commit in commits.commits 
            if commit.author and commit.author.username
        )
        
        # Count breaking changes (heuristic)
        breaking_changes = sum(1 for commit in commits.commits 
                             if any(keyword in commit.message.lower() 
                                   for keyword in ['breaking', 'break', 'major']))
        
        # Count security fixes
        security_fixes = sum(1 for commit in commits.commits 
                           if any(keyword in commit.message.lower() 
                                 for keyword in ['security', 'vulnerability', 'cve']))
        
        return PostMetrics(
            total_commits=len(commits.commits),
            files_changed=total_files,
            lines_added=total_additions,
            lines_removed=total_deletions,
            contributors=len(contributors),
            time_period=time_period,
            breaking_changes=breaking_changes,
            security_fixes=security_fixes
        )
    
    async def generate_posts_batch(self, repositories: List[str], time_periods: List[str] = ["2h", "24h"]) -> List[PostGenerationResponse]:
        """Generate posts for multiple repositories and time periods"""
        responses = []
        
        for repository in repositories:
            for time_period in time_periods:
                try:
                    request = PostGenerationRequest(
                        repository=repository,
                        time_period=time_period
                    )
                    
                    # Note: This would need actual commit collection logic
                    logger.info(f"Would generate post for {repository} ({time_period})")
                    
                except Exception as e:
                    logger.error(f"Error generating post for {repository} ({time_period}): {e}")
                    continue
        
        return responses
    
    def get_post_analytics(self, post_id: str) -> Dict[str, Any]:
        """Get analytics for a specific post (placeholder for future implementation)"""
        return {
            "post_id": post_id,
            "views": 0,
            "engagement_rate": 0.0,
            "click_through_rate": 0.0,
            "shares": 0,
            "comments": 0
        }
    
    def get_trending_topics(self, commits: CommitCollection) -> List[str]:
        """Extract trending topics from commits"""
        topics = []
        
        # Extract from commit messages
        common_words = {}
        for commit in commits.commits:
            words = commit.message.lower().split()
            for word in words:
                if len(word) > 3 and word.isalpha():
                    common_words[word] = common_words.get(word, 0) + 1
        
        # Get top words
        sorted_words = sorted(common_words.items(), key=lambda x: x[1], reverse=True)
        topics.extend([word for word, count in sorted_words[:10] if count > 1])
        
        # Add commit types as topics
        for commit_type in commits.commit_types.keys():
            topics.append(commit_type.value)
        
        return list(set(topics))[:10]