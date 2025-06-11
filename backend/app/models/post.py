from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from enum import Enum

class PostType(str, Enum):
    FEATURE_ANNOUNCEMENT = "feature_announcement"
    BUG_FIX_SUMMARY = "bug_fix_summary"
    SECURITY_UPDATE = "security_update"
    PERFORMANCE_IMPROVEMENT = "performance_improvement"
    GENERAL_UPDATE = "general_update"
    RELEASE_NOTES = "release_notes"
    DEVELOPMENT_PROGRESS = "development_progress"

class PostTemplate(str, Enum):
    FEATURE = "template_feature"
    BUGFIX = "template_bugfix"
    SECURITY = "template_security"
    PERFORMANCE = "template_performance"
    GENERAL = "template_general"

class ChartData(BaseModel):
    chart_type: str  # bar, line, pie, progress
    data: Dict[str, Any]
    title: str
    description: Optional[str] = None

class PostMetrics(BaseModel):
    total_commits: int
    files_changed: int
    lines_added: int
    lines_removed: int
    contributors: int
    time_period: str  # "2h" or "24h"
    breaking_changes: int = 0
    security_fixes: int = 0

class PostContent(BaseModel):
    title: str
    summary: str
    detailed_explanation: str
    technical_highlights: List[str] = []
    user_benefits: List[str] = []
    code_snippets: List[Dict[str, str]] = []  # {"language": "python", "code": "..."}
    charts: List[ChartData] = []
    tags: List[str] = []
    hashtags: List[str] = []

class Post(BaseModel):
    id: str
    post_type: PostType
    template: PostTemplate
    content: PostContent
    metrics: PostMetrics
    
    # Metadata
    created_at: datetime
    repository: str
    time_period: str  # "2h" or "24h"
    source_commits: List[str]  # List of commit SHAs
    
    # Output
    html_content: Optional[str] = None
    output_file_path: Optional[str] = None
    
    # Engagement data (for future use)
    views: int = 0
    likes: int = 0
    shares: int = 0
    comments: List[str] = []
    
    @property
    def filename(self) -> str:
        timestamp = self.created_at.strftime("%Y%m%d_%H%M%S")
        safe_repo = self.repository.replace('/', '_')
        return f"{safe_repo}_{self.time_period}_{timestamp}.html"
    
    @property
    def short_summary(self) -> str:
        """Return a truncated summary for social media"""
        max_length = 200
        if len(self.content.summary) <= max_length:
            return self.content.summary
        return self.content.summary[:max_length-3] + "..."
    
    def get_engagement_stats(self) -> Dict[str, int]:
        return {
            "views": self.views,
            "likes": self.likes,
            "shares": self.shares,
            "comments": len(self.comments)
        }

class PostGenerationRequest(BaseModel):
    repository: str
    time_period: str  # "2h" or "24h"
    force_template: Optional[PostTemplate] = None
    include_charts: bool = True
    include_code_snippets: bool = True
    target_audience: str = "general"  # general, technical, business
    max_length: Optional[int] = None

class PostGenerationResponse(BaseModel):
    success: bool
    post: Optional[Post] = None
    error_message: Optional[str] = None
    generation_time_seconds: float
    tokens_used: Optional[int] = None