import os
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from ..models.commit import CommitCollection
from ..models.post import (
    Post, PostContent, PostMetrics, PostGenerationRequest, 
    PostGenerationResponse, PostType, PostTemplate, ChartData
)
from .claude_client import ClaudeClient
from .config import settings
from ..utils.template_selector import TemplateSelector
from ..utils.html_generator import HTMLGenerator
from ..utils.chart_generator import ChartGenerator

logger = logging.getLogger(__name__)

class PostGenerator:
    def __init__(self):
        self.claude_client = ClaudeClient()
        self.template_selector = TemplateSelector()
        self.html_generator = HTMLGenerator()
        self.chart_generator = ChartGenerator()
    
    def generate_post(self, request: PostGenerationRequest, commits: CommitCollection) -> PostGenerationResponse:
        """Generate a complete post from commit data"""
        start_time = datetime.now()
        
        try:
            logger.info(f"Generating post for {request.repository} ({request.time_period})")
            
            # Validate input
            if not commits.commits:
                return PostGenerationResponse(
                    success=False,
                    error_message="No commits found for the specified time period",
                    generation_time_seconds=0
                )
            
            # Generate content with Claude
            claude_response = self.claude_client.generate_post_content(
                commits=commits,
                target_audience=request.target_audience,
                force_template=request.force_template
            )
            
            # Generate charts if requested
            charts = []
            if request.include_charts:
                charts = self._create_simple_charts(commits)
            
            # Create post content
            content = PostContent(
                title=claude_response["content"].get("title", "Repository Update"),
                summary=claude_response["content"].get("summary", ""),
                detailed_explanation=claude_response["content"].get("detailed_explanation", ""),
                technical_highlights=claude_response["content"].get("technical_highlights", []),
                user_benefits=claude_response["content"].get("user_benefits", []),
                code_snippets=claude_response["content"].get("code_snippets", []),
                charts=charts,
                tags=claude_response["content"].get("tags", []),
                hashtags=claude_response["content"].get("hashtags", [])
            )
            
            # Create metrics
            metrics = PostMetrics(
                total_commits=commits.total_commits,
                files_changed=commits.total_files_changed,
                lines_added=commits.total_additions,
                lines_removed=commits.total_deletions,
                contributors=len(commits.top_contributors),
                time_period=request.time_period,
                breaking_changes=commits.breaking_changes,
                security_fixes=commits.security_updates
            )
            
            # Create post
            post = Post(
                id=str(uuid.uuid4()),
                post_type=claude_response["post_type"],
                template=claude_response["template"],
                content=content,
                metrics=metrics,
                created_at=datetime.now(),
                repository=request.repository,
                time_period=request.time_period,
                source_commits=[c.sha for c in commits.commits]
            )
            
            # Generate HTML
            html_content = self.html_generator.generate_html(post)
            post.html_content = html_content
            
            # Save to file
            output_path = self._save_post_to_file(post, html_content)
            post.output_file_path = output_path
            
            # Calculate generation time
            generation_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Successfully generated post for {request.repository}")
            
            return PostGenerationResponse(
                success=True,
                post=post,
                generation_time_seconds=generation_time,
                tokens_used=claude_response.get("tokens_used")
            )
            
        except Exception as e:
            logger.error(f"Error generating post: {e}")
            generation_time = (datetime.now() - start_time).total_seconds()
            
            return PostGenerationResponse(
                success=False,
                error_message=str(e),
                generation_time_seconds=generation_time
            )
    
    def _create_simple_charts(self, commits: CommitCollection) -> List[ChartData]:
        """Create simple charts from commit data"""
        charts = []
        
        # Commit types chart
        if commits.commit_types:
            charts.append(ChartData(
                chart_type="pie",
                title="Commit Types Distribution",
                data={
                    "labels": [ct.value.title() for ct in commits.commit_types.keys()],
                    "values": list(commits.commit_types.values())
                },
                description="Breakdown of different types of commits"
            ))
        
        # Development progress
        if commits.total_commits > 0:
            completion_percentage = min(95, (commits.total_commits * 10))
            charts.append(ChartData(
                chart_type="progress",
                title="Development Progress", 
                data={
                    "percentage": completion_percentage,
                    "label": f"{commits.total_commits} commits this period"
                },
                description="Current development activity"
            ))
        
        return charts
    
    def _create_charts(self, chart_suggestions: List[Dict[str, Any]]) -> List[ChartData]:
        """Create chart data from suggestions (legacy method)"""
        charts = []
        
        for suggestion in chart_suggestions:
            try:
                chart = ChartData(
                    chart_type=suggestion["chart_type"],
                    data=suggestion["data"],
                    title=suggestion["title"],
                    description=suggestion.get("description")
                )
                charts.append(chart)
            except Exception as e:
                logger.warning(f"Error creating chart: {e}")
                continue
        
        return charts
    
    def _save_post_to_file(self, post: Post, html_content: str) -> str:
        """Save post HTML to file"""
        try:
            # Create directory structure
            output_dir = os.path.join(settings.output_dir, post.time_period)
            os.makedirs(output_dir, exist_ok=True)
            
            # Create filename
            filename = post.filename
            filepath = os.path.join(output_dir, filename)
            
            # Save HTML file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"Saved post to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving post to file: {e}")
            raise
    
    def generate_batch_posts(self, repositories: List[str], time_periods: List[str]) -> List[PostGenerationResponse]:
        """Generate posts for multiple repositories and time periods"""
        responses = []
        
        for repository in repositories:
            for time_period in time_periods:
                try:
                    # This would need to be connected to the commit collection logic
                    # For now, creating a placeholder request
                    request = PostGenerationRequest(
                        repository=repository,
                        time_period=time_period
                    )
                    
                    # Get commits for this period (would need to implement this)
                    # commits = self._get_commits_for_period(repository, time_period)
                    # response = self.generate_post(request, commits)
                    # responses.append(response)
                    
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