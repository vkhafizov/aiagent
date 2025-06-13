import re
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any, Set
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
        
        # Create author and committer - handle potential None values
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
        
        # Convert timestamp to timezone-aware if needed
        timestamp = github_commit.commit.author.date
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        
        return Commit(
            sha=github_commit.sha,
            message=github_commit.commit.message,
            author=author,
            committer=committer,
            timestamp=timestamp,
            repository=repo_name,
            branch="main",  # Will be updated in get_commits_all_branches
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
    
    def get_commits_all_branches(self, repo_name: str, since: datetime, until: datetime = None, max_branches: int = 70) -> List[Commit]:
        """Get commits from ALL branches within a time range"""
        try:
            repo = self.github.get_repo(repo_name)
            
            # Ensure timezone-aware datetimes
            if until is None:
                until = datetime.now(timezone.utc)
            elif until.tzinfo is None:
                until = until.replace(tzinfo=timezone.utc)
            
            if since.tzinfo is None:
                since = since.replace(tzinfo=timezone.utc)
            
            logger.info(f"Fetching commits from ALL branches of {repo_name} between {since} and {until}")
            
            # Get all branches
            branches = list(repo.get_branches())
            logger.info(f"Found {len(branches)} branches in {repo_name}")
            
            # Limit branches to avoid rate limiting
            if len(branches) > max_branches:
                logger.info(f"Limiting to first {max_branches} branches to avoid rate limits")
                branches = branches[:max_branches]
            
            all_commits = {}  # Use dict to avoid duplicates, key = sha
            branch_stats = {}
            
            for branch in branches:
                branch_name = branch.name
                logger.info(f"Checking branch: {branch_name}")
                
                try:
                    # Get commits from this specific branch
                    branch_commits = repo.get_commits(sha=branch_name, since=since, until=until)
                    
                    branch_commit_count = 0
                    for github_commit in branch_commits:
                        if github_commit.sha not in all_commits:
                            # Convert to our Commit model
                            commit = self._convert_github_commit(github_commit, repo_name)
                            # Update branch info
                            commit.branch = branch_name
                            all_commits[github_commit.sha] = commit
                            branch_commit_count += 1
                        else:
                            # Commit already exists, just update branch info if it's from main
                            existing_commit = all_commits[github_commit.sha]
                            if existing_commit.branch == "main" and branch_name != "main":
                                existing_commit.branch = branch_name
                    
                    branch_stats[branch_name] = branch_commit_count
                    logger.info(f"Branch {branch_name}: {branch_commit_count} new commits")
                    
                except Exception as e:
                    logger.warning(f"Error getting commits from branch {branch_name}: {e}")
                    branch_stats[branch_name] = f"Error: {str(e)}"
                    continue
            
            # Convert dict values to list
            commits_list = list(all_commits.values())
            
            # Sort by timestamp (newest first)
            commits_list.sort(key=lambda c: c.timestamp, reverse=True)
            
            logger.info(f"Total unique commits found across all branches: {len(commits_list)}")
            logger.info(f"Branch statistics: {branch_stats}")
            
            return commits_list
            
        except GithubException as e:
            logger.error(f"GitHub API error for repo {repo_name}: {e}")
            logger.error(f"Error details: status={e.status}, data={e.data}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching commits from {repo_name}: {e}")
            raise
    
    def get_commits(self, repo_name: str, since: datetime, until: datetime = None, all_branches: bool = True) -> List[Commit]:
        """Get commits from a repository within a time range"""
        if all_branches:
            return self.get_commits_all_branches(repo_name, since, until)
        else:
            # Original method - only default branch
            try:
                repo = self.github.get_repo(repo_name)
                
                # Ensure until is timezone-aware
                if until is None:
                    until = datetime.now(timezone.utc)
                elif until.tzinfo is None:
                    until = until.replace(tzinfo=timezone.utc)
                
                # Ensure since is timezone-aware
                if since.tzinfo is None:
                    since = since.replace(tzinfo=timezone.utc)
                
                logger.info(f"Fetching commits from default branch of {repo_name} between {since} and {until}")
                
                # Get commits from GitHub API (default branch only)
                github_commits = repo.get_commits(since=since, until=until)
                
                # Convert iterator to list to see how many commits we got
                commits_list = list(github_commits)
                logger.info(f"GitHub API returned {len(commits_list)} raw commits from default branch")
                
                commits = []
                for i, github_commit in enumerate(commits_list):
                    try:
                        commit = self._convert_github_commit(github_commit, repo_name)
                        commits.append(commit)
                        logger.debug(f"Converted commit {i+1}/{len(commits_list)}: {github_commit.sha[:7]}")
                    except Exception as e:
                        logger.error(f"Error processing commit {github_commit.sha}: {e}")
                        continue
                
                logger.info(f"Successfully converted {len(commits)} commits from default branch")
                return commits
                
            except GithubException as e:
                logger.error(f"GitHub API error for repo {repo_name}: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error fetching commits from {repo_name}: {e}")
                raise
    
    def get_commits_for_period(self, repo_name: str, hours: int, all_branches: bool = True) -> CommitCollection:
        """Get commits for the last N hours from all branches"""
        # Create timezone-aware datetime objects directly
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)
        
        branch_info = "all branches" if all_branches else "default branch only"
        logger.info(f"Collecting commits for {repo_name} from {branch_info} "
                   f"from {start_time.isoformat()} to {end_time.isoformat()}")
        
        commits = self.get_commits(repo_name, since=start_time, until=end_time, all_branches=all_branches)
        
        # Calculate totals
        total_additions = sum(c.additions for c in commits)
        total_deletions = sum(c.deletions for c in commits)
        total_files_changed = sum(c.files_count for c in commits)
        
        collection = CommitCollection(
            commits=commits,
            start_time=start_time,
            end_time=end_time,
            repository=repo_name,
            total_commits=len(commits),
            total_additions=total_additions,
            total_deletions=total_deletions,
            total_files_changed=total_files_changed
        )
        
        logger.info(f"Created CommitCollection with {len(commits)} commits, "
                   f"{total_additions} additions, {total_deletions} deletions, "
                   f"{total_files_changed} files changed")
        
        return collection
    
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