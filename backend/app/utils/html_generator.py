import os
import logging
from datetime import datetime
from typing import Dict, Any, List
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..models.post import Post, PostTemplate, ChartData
from .chart_generator import ChartGenerator

logger = logging.getLogger(__name__)

class HTMLGenerator:
    """Generates HTML content from post data using templates"""
    
    def __init__(self):
        # Setup Jinja2 environment
        template_dir = os.path.join("app", "templates")
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )
        self.chart_generator = ChartGenerator()
        
        # Add custom filters
        self.env.filters['timeago'] = self._timeago_filter
        self.env.filters['truncate_smart'] = self._truncate_smart_filter
        self.env.filters['format_number'] = self._format_number_filter
    
    def generate_html(self, post: Post) -> str:
        """Generate HTML content for a post"""
        try:
            # Select template file
            template_file = self._get_template_file(post.template)
            template = self.env.get_template(template_file)
            
            # Prepare template data
            template_data = self._prepare_template_data(post)
            
            # Render HTML
            html_content = template.render(**template_data)
            
            logger.info(f"Generated HTML for post {post.id}")
            return html_content
            
        except Exception as e:
            logger.error(f"Error generating HTML for post {post.id}: {e}")
            # Fallback to basic template
            return self._generate_fallback_html(post)
    
    def _get_template_file(self, template: PostTemplate) -> str:
        """Get the template filename for a given template type"""
        template_mapping = {
            PostTemplate.FEATURE: "template_feature.html",
            PostTemplate.BUGFIX: "template_bugfix.html",
            PostTemplate.SECURITY: "template_security.html",
            PostTemplate.PERFORMANCE: "template_performance.html",
            PostTemplate.GENERAL: "template_general.html"
        }
        
        return template_mapping.get(template, "template_general.html")
    
    def _prepare_template_data(self, post: Post) -> Dict[str, Any]:
        """Prepare data for template rendering"""
        
        # Calculate engagement data
        engagement_data = self._generate_engagement_data(post)
        
        # Generate chart HTML
        chart_html = self._generate_chart_html(post.content.charts)
        
        # Format code snippets
        formatted_code = self._format_code_snippets(post.content.code_snippets)
        
        # Generate diff view for technical highlights
        diff_content = self._generate_diff_content(post.content.technical_highlights)
        
        # Progress bars for metrics
        progress_bars = self._generate_progress_bars(post.metrics)
        
        return {
            'post': post,
            'content': post.content,
            'metrics': post.metrics,
            'engagement': engagement_data,
            'charts': chart_html,
            'code_snippets': formatted_code,
            'diff_content': diff_content,
            'progress_bars': progress_bars,
            'timestamp': post.created_at,
            'timeago': self._format_timeago(post.created_at),
            'avatar_url': self._get_avatar_url(post.repository),
            'username': self._extract_username(post.repository),
            'repo_name': post.repository.split('/')[-1] if '/' in post.repository else post.repository
        }
    
    def _generate_engagement_data(self, post: Post) -> Dict[str, int]:
        """Generate mock engagement data (would be real data in production)"""
        import random
        
        # Generate realistic engagement numbers based on post metrics
        base_engagement = max(10, post.metrics.total_commits * 2)
        
        return {
            'likes': random.randint(base_engagement, base_engagement * 3),
            'comments': random.randint(base_engagement // 3, base_engagement),
            'shares': random.randint(base_engagement * 2, base_engagement * 5)
        }
    
    def _generate_chart_html(self, charts: List[ChartData]) -> List[str]:
        """Generate HTML for charts"""
        chart_html = []
        
        for chart in charts:
            try:
                html = self.chart_generator.generate_chart_html(chart)
                chart_html.append(html)
            except Exception as e:
                logger.warning(f"Error generating chart HTML: {e}")
                continue
        
        return chart_html
    
    def _format_code_snippets(self, code_snippets: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Format code snippets with syntax highlighting info"""
        formatted = []
        
        for snippet in code_snippets:
            formatted_snippet = {
                'language': snippet.get('language', 'text'),
                'code': self._escape_html(snippet.get('code', '')),
                'description': snippet.get('description', ''),
                'language_class': f"language-{snippet.get('language', 'text')}"
            }
            formatted.append(formatted_snippet)
        
        return formatted
    
    def _generate_diff_content(self, technical_highlights: List[str]) -> List[Dict[str, str]]:
        """Generate diff-style content from technical highlights"""
        diff_content = []
        
        for highlight in technical_highlights:
            # Simple heuristic to determine if it's an addition or removal
            if any(word in highlight.lower() for word in ['add', 'new', 'implement', 'create']):
                diff_type = 'added'
            elif any(word in highlight.lower() for word in ['remove', 'delete', 'deprecat']):
                diff_type = 'removed'
            else:
                diff_type = 'added'  # Default to addition
            
            diff_content.append({
                'type': diff_type,
                'content': highlight
            })
        
        return diff_content
    
    def _generate_progress_bars(self, metrics) -> List[Dict[str, Any]]:
        """Generate progress bar data from metrics"""
        progress_bars = []
        
        # Implementation progress (mock calculation)
        if metrics.total_commits > 0:
            implementation_progress = min(95, (metrics.total_commits * 10) % 100)
            progress_bars.append({
                'label': 'Implementation Progress',
                'percentage': implementation_progress,
                'color': 'primary'
            })
        
        # Quality progress (based on files changed vs commits ratio)
        if metrics.total_commits > 0:
            quality_ratio = metrics.files_changed / metrics.total_commits
            quality_progress = min(90, int(quality_ratio * 30) + 60)
            progress_bars.append({
                'label': 'Code Quality',
                'percentage': quality_progress,
                'color': 'success'
            })
        
        return progress_bars
    
    def _escape_html(self, text: str) -> str:
        """Basic HTML escaping"""
        return (text.replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
                    .replace('"', '&quot;')
                    .replace("'", '&#x27;'))
    
    def _get_avatar_url(self, repository: str) -> str:
        """Get avatar URL for repository (placeholder)"""
        return "https://avatars.githubusercontent.com/u/0"
    
    def _extract_username(self, repository: str) -> str:
        """Extract username from repository string"""
        if '/' in repository:
            return repository.split('/')[0]
        return repository
    
    def _format_timeago(self, timestamp: datetime) -> str:
        """Format timestamp as relative time"""
        now = datetime.now()
        diff = now - timestamp
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}h ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}m ago"
        else:
            return "Just now"
    
    def _timeago_filter(self, timestamp):
        """Jinja2 filter for timeago formatting"""
        return self._format_timeago(timestamp)
    
    def _truncate_smart_filter(self, text, length=100):
        """Jinja2 filter for smart text truncation"""
        if len(text) <= length:
            return text
        
        # Try to truncate at word boundary
        truncated = text[:length]
        last_space = truncated.rfind(' ')
        
        if last_space > length * 0.7:  # If we can find a good word boundary
            return truncated[:last_space] + "..."
        else:
            return truncated + "..."
    
    def _format_number_filter(self, number):
        """Jinja2 filter for number formatting"""
        if number >= 1000000:
            return f"{number/1000000:.1f}M"
        elif number >= 1000:
            return f"{number/1000:.1f}K"
        else:
            return str(number)
    
    def _generate_fallback_html(self, post: Post) -> str:
        """Generate basic HTML when template rendering fails"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{post.content.title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
                .post {{ background: #f9f9f9; padding: 20px; border-radius: 8px; }}
                .title {{ color: #333; margin-bottom: 10px; }}
                .summary {{ color: #666; margin-bottom: 20px; }}
                .metrics {{ background: #fff; padding: 15px; border-radius: 6px; }}
            </style>
        </head>
        <body>
            <div class="post">
                <h1 class="title">{post.content.title}</h1>
                <p class="summary">{post.content.summary}</p>
                <div class="metrics">
                    <strong>Metrics:</strong>
                    {post.metrics.total_commits} commits,
                    {post.metrics.files_changed} files changed,
                    {post.metrics.lines_added} lines added
                </div>
            </div>
        </body>
        </html>
        """
        return html