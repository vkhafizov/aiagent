import re
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from github import Github, Repository, Commit as GithubCommit
from github.GithubException import GithubException

from ..models.commit import Commit, CommitCollection, CommitType, FileChange, CommitAuthor
from .config import settings

logger = logging.getLogger(__name__)

class GitHubCollector:
    def __init__(self, token: str = None):
        self.token = token or settings.github_token
        self.github = Github(self.token)
        self.rate_limit_remaining = None
        
    def _classify_commit_type(self, message: str, files: List[str]) -> CommitType:
        """Classify commit type based on message and files changed"""
        message_lower = message.lower()
        
        # Check commit message patterns
        if any(keyword in message_lower for keyword in ['feat:', 'feature:', 'add:', 'new:']):
            return CommitType.FEATURE
        elif any(keyword in message_lower for keyword in ['fix:', 'bug:', 'bugfix:', 'hotfix:']):
            return CommitType.BUGFIX
        elif any(keyword in message_lower for keyword in ['security:', 'sec:', 'vulnerability', 'cve']):
            return CommitType.SECURITY
        elif any(keyword in message_lower for keyword in ['perf:', 'performance:', 'optimize:', 'speed:']):
            return CommitType.PERFORMANCE
        elif any(keyword in message_lower for keyword in ['docs:', 'doc:', 'documentation:', 'readme']):
            return CommitType.DOCUMENTATION
        elif any(keyword in message_lower for keyword in ['refactor:', 'refactoring:', 'cleanup:', 'restructure:']):
            return CommitType.REFACTOR
        elif any(keyword in message_lower for keyword in ['test:', 'tests:', 'testing:', 'spec:']):
            return CommitType.TEST
        elif any(keyword in message_lower for keyword in ['style:', 'format:', 'lint:', 'prettier:']):
            return CommitType.STYLE
        elif any(keyword in message_lower for keyword in ['chore:', 'build:', 'ci:', 'deps:']):
            return CommitType.CHORE
        
        # Check based on files changed
        if files:
            test_files = sum(1 for f in files if 'test' in f.lower() or f.endswith('.test.js') or f.endswith('_test.py'))
            doc_files = sum(1 for f in files if f.lower().endswith(('.md', '.rst', '.txt')) or 'doc' in f.lower())
            
            if test_files > len(files) * 0.5:
                return CommitType.TEST
            elif doc_files > len(files) * 0.5:
                return CommitType.DOCUMENTATION
        
        return CommitType.OTHER
    
    def _is_breaking_change(self, message: str) -> bool:
        """Check if commit is a breaking change"""
        indicators = [
            'breaking change', 'breaking:', 'break:', 'major:', 
            'BREAKING CHANGE', 'BREAKING:', '!:', 'major version'
        ]
        return any(indicator in message for indicator in indicators)
    
    def _affects_security(self, message: str, files: List[str]) -> bool:
        """Check if commit affects security"""
        security_keywords = [
            'security', 'vulnerability', 'cve', 'auth', 'authentication',
            'authorization', 'crypto', 'encrypt', 'decrypt', 'hash', 'token',
            'password', 'secret', 'credential'
        ]
        
        message_lower = message.lower()
        if any(keyword in message_lower for keyword in security_keywords):
            return True
        
        # Check file paths
        security_files = [
            'auth', 'security', 'crypto', 'password', 'token', 'credential'
        ]
        for file in files:
            if any(sec_file in file.lower() for sec_file in security_files):
                return True
        
        return False
    
    def _affects_performance(self, message: str, files: List[str]) -> bool:
        """Check if commit affects performance"""
        performance_keywords = [
            'performance', 'optimize', 'speed', 'fast', 'slow', 'cache',
            'memory', 'cpu', 'benchmark', 'profil', 'bottleneck'
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in performance_keywords)
    
    def _extract_file_changes(self, github_commit: GithubCommit) -> List[FileChange]:
        """Extract file changes from GitHub commit"""
        file_changes = []
        
        try:
            for file in github_commit.files:
                file_change = FileChange(
                    filename=file.filename,
                    additions=file.additions,
                    deletions=file.deletions,
                    changes=file.changes,
                    status=file.status,
                    patch=file.patch if hasattr(file, 'patch') else None
                )
                file_changes.append(file_change)
        except Exception as e:
            logger.warning(f"Error extracting file changes: {e}")
        
        return file_changes
    
    def _convert_github_commit(self, github_commit: GithubCommit, repo_name: str) -> Commit:
        """Convert GitHub commit to our Commit model"""
        
        # Extract file changes
        file_changes = self._extract_file_changes(github_commit)
        filenames = [fc.filename for fc in file_changes]
        
        # Create author and committer
        author = CommitAuthor(
            name=github_commit.author.name if github_commit.author else "Unknown",
            email=github_commit.author.email if github_commit.author else "",
            username=github_commit.author.login if github_commit.author else None,
            avatar_url=github_commit.author.avatar_url if github_commit.author else None
        )
        
        committer = CommitAuthor(
            name=github_commit.committer.name if github_commit.committer else author.name,
            email=github_commit.committer.email if github_commit.committer else author.email,
            username=github_commit.committer.login if github_commit.committer else author.username,
            avatar_url=github_commit.committer.avatar_url if github_commit.committer else author.avatar_url
        )
        
        # Calculate totals
        total_additions = sum(fc.additions for fc in file_changes)
        total_deletions = sum(fc.deletions for fc in file_changes)
        total_changes = sum(fc.changes for fc in file_changes)
        
        # Analyze commit
        commit_type = self._classify_commit_type(github_commit.commit.message, filenames)
        is_breaking = self._is_breaking_change(github_commit.commit.message)
        affects_security = self._affects_security(github_commit.commit.message, filenames)
        affects_performance = self._affects_performance(github_commit.commit.message, filenames)
        
        return Commit(
            sha=github_commit.sha,
            message=github_commit.commit.message,
            author=author,
            committer=committer,
            timestamp=github_commit.commit.author.date,
            repository=repo_name,
            branch="main",  # Default branch, could be enhanced
            url=github_commit.html_url,
            files_changed=file_changes,
            additions=total_additions,
            deletions=total_deletions,
            total_changes=total_changes,
            commit_type=commit_type,
            is_breaking_change=is_breaking,
            affects_security=affects_security,
            affects_performance=affects_performance
        )
    
    def get_commits(self, repo_name: str, since: datetime, until: datetime = None) -> List[Commit]:
        """Get commits from a repository within a time range"""
        try:
            repo = self.github.get_repo(repo_name)
            until = until or datetime.now()
            
            logger.info(f"Fetching commits from {repo_name} between {since} and {until}")
            
            # Get commits from GitHub
            github_commits = repo.get_commits(since=since, until=until)
            
            commits = []
            for github_commit in github_commits:
                try:
                    commit = self._convert_github_commit(github_commit, repo_name)
                    commits.append(commit)
                except Exception as e:
                    logger.error(f"Error processing commit {github_commit.sha}: {e}")
                    continue
            
            logger.info(f"Successfully fetched {len(commits)} commits from {repo_name}")
            return commits
            
        except GithubException as e:
            logger.error(f"GitHub API error for repo {repo_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching commits from {repo_name}: {e}")
            raise
    
    def get_commits_for_period(self, repo_name: str, hours: int) -> CommitCollection:
        """Get commits for the last N hours"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        commits = self.get_commits(repo_name, since=start_time, until=end_time)
        
        # Calculate totals
        total_additions = sum(c.additions for c in commits)
        total_deletions = sum(c.deletions for c in commits)
        total_files_changed = sum(c.files_count for c in commits)
        
        return CommitCollection(
            commits=commits,
            start_time=start_time,
            end_time=end_time,
            repository=repo_name,
            total_commits=len(commits),
            total_additions=total_additions,
            total_deletions=total_deletions,
            total_files_changed=total_files_changed
        )
    
    def save_commits_to_file(self, commits: CommitCollection, filepath: str):
        """Save commits to JSON file"""
        try:
            # Convert to dict for JSON serialization
            data = commits.dict()
            
            # Convert datetime objects to ISO strings
            data['start_time'] = commits.start_time.isoformat()
            data['end_time'] = commits.end_time.isoformat()
            
            for commit_data in data['commits']:
                if isinstance(commit_data['timestamp'], datetime):
                    commit_data['timestamp'] = commit_data['timestamp'].isoformat()
                elif hasattr(commit_data['timestamp'], 'isoformat'):
                    commit_data['timestamp'] = commit_data['timestamp'].isoformat()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(commits.commits)} commits to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving commits to file {filepath}: {e}")
            raise
    
    def load_commits_from_file(self, filepath: str) -> CommitCollection:
        """Load commits from JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert ISO strings back to datetime objects
            data['start_time'] = datetime.fromisoformat(data['start_time'])
            data['end_time'] = datetime.fromisoformat(data['end_time'])
            
            for commit_data in data['commits']:
                commit_data['timestamp'] = datetime.fromisoformat(commit_data['timestamp'])
            
            return CommitCollection(**data)
            
        except Exception as e:
            logger.error(f"Error loading commits from file {filepath}: {e}")
            raise
    
    def check_rate_limit(self) -> Dict[str, Any]:
        """Check GitHub API rate limit"""
        try:
            rate_limit = self.github.get_rate_limit()
            return {
                "core": {
                    "limit": rate_limit.core.limit,
                    "remaining": rate_limit.core.remaining,
                    "reset": rate_limit.core.reset
                }
            }
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return {"error": str(e)}