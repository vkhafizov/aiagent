from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from enum import Enum

class CommitType(str, Enum):
    FEATURE = "feature"
    BUGFIX = "bugfix"
    SECURITY = "security"
    PERFORMANCE = "performance"
    DOCUMENTATION = "documentation"
    REFACTOR = "refactor"
    TEST = "test"
    STYLE = "style"
    CHORE = "chore"
    OTHER = "other"

class FileChange(BaseModel):
    filename: str
    additions: int
    deletions: int
    changes: int
    status: str  # added, modified, removed, renamed
    patch: Optional[str] = None

class CommitAuthor(BaseModel):
    name: Optional[str] = "Unknown"
    email: Optional[str] = "unknown@example.com"
    username: Optional[str] = None
    avatar_url: Optional[str] = None

class Commit(BaseModel):
    sha: str
    message: str
    author: CommitAuthor
    committer: CommitAuthor
    timestamp: datetime
    repository: str
    branch: str
    url: str
    
    # File changes
    files_changed: List[FileChange] = []
    additions: int = 0
    deletions: int = 0
    total_changes: int = 0
    
    # Commit analysis
    commit_type: CommitType = CommitType.OTHER
    is_breaking_change: bool = False
    affects_security: bool = False
    affects_performance: bool = False
    
    # Associated data
    pull_request_number: Optional[int] = None
    issues_closed: List[int] = []
    tags: List[str] = []
    
    @property
    def short_sha(self) -> str:
        return self.sha[:7]
    
    @property
    def is_major_change(self) -> bool:
        return self.total_changes > 50 or self.is_breaking_change
    
    @property
    def files_count(self) -> int:
        return len(self.files_changed)

class CommitCollection(BaseModel):
    commits: List[Commit]
    start_time: datetime
    end_time: datetime
    repository: str
    total_commits: int
    total_additions: int
    total_deletions: int
    total_files_changed: int
    
    # Analysis summary
    commit_types: Dict[CommitType, int] = {}
    top_contributors: List[Dict[str, Any]] = []
    most_changed_files: List[Dict[str, Any]] = []
    breaking_changes: int = 0
    security_updates: int = 0
    
    def __init__(self, **data):
        super().__init__(**data)
        self._analyze_commits()
    
    def _analyze_commits(self):
        if not self.commits:
            return
        
        # Analyze commit types
        type_counts = {}
        contributors = {}
        file_changes = {}
        
        for commit in self.commits:
            # Count commit types
            commit_type = commit.commit_type
            type_counts[commit_type] = type_counts.get(commit_type, 0) + 1
            
            # Count contributors
            author = commit.author.username or commit.author.name
            if author not in contributors:
                contributors[author] = {
                    "name": author,
                    "commits": 0,
                    "additions": 0,
                    "deletions": 0,
                    "avatar_url": commit.author.avatar_url
                }
            contributors[author]["commits"] += 1
            contributors[author]["additions"] += commit.additions
            contributors[author]["deletions"] += commit.deletions
            
            # Count file changes
            for file_change in commit.files_changed:
                filename = file_change.filename
                if filename not in file_changes:
                    file_changes[filename] = {
                        "filename": filename,
                        "changes": 0,
                        "commits": 0
                    }
                file_changes[filename]["changes"] += file_change.changes
                file_changes[filename]["commits"] += 1
        
        # Set analysis results
        self.commit_types = {CommitType(k): v for k, v in type_counts.items()}
        
        # Top contributors (sorted by commits)
        self.top_contributors = sorted(
            contributors.values(),
            key=lambda x: x["commits"],
            reverse=True
        )[:5]
        
        # Most changed files
        self.most_changed_files = sorted(
            file_changes.values(),
            key=lambda x: x["changes"],
            reverse=True
        )[:10]
        
        # Count special commits
        self.breaking_changes = sum(1 for c in self.commits if c.is_breaking_change)
        self.security_updates = sum(1 for c in self.commits if c.affects_security)
    
    @property
    def time_period_hours(self) -> float:
        return (self.end_time - self.start_time).total_seconds() / 3600
    
    @property
    def commits_per_hour(self) -> float:
        hours = self.time_period_hours
        return self.total_commits / hours if hours > 0 else 0