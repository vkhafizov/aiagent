import logging
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from collections import defaultdict, Counter

from ..models.commit import CommitCollection, Commit, CommitType

logger = logging.getLogger(__name__)

class DataProcessor:
    """Processes and analyzes commit data for insights and trends"""
    
    def __init__(self):
        # Patterns for commit message analysis
        self.commit_patterns = {
            CommitType.FEATURE: [
                r'\b(feat|feature|add|new|implement|create)\b',
                r'\b(introduce|build|develop)\b'
            ],
            CommitType.BUGFIX: [
                r'\b(fix|bug|issue|resolve|correct|patch)\b',
                r'\b(hotfix|quickfix|repair)\b'
            ],
            CommitType.SECURITY: [
                r'\b(security|vulnerability|auth|encrypt|decrypt)\b',
                r'\b(token|password|credential|cve)\b'
            ],
            CommitType.PERFORMANCE: [
                r'\b(perf|performance|optimize|speed|fast)\b',
                r'\b(cache|memory|cpu|benchmark)\b'
            ],
            CommitType.DOCUMENTATION: [
                r'\b(docs?|documentation|readme|comment)\b',
                r'\b(guide|tutorial|example)\b'
            ],
            CommitType.REFACTOR: [
                r'\b(refactor|cleanup|restructure|reorganize)\b',
                r'\b(simplify|improve|enhance)\b'
            ],
            CommitType.TEST: [
                r'\b(test|tests|testing|spec|specs)\b',
                r'\b(unit|integration|e2e|coverage)\b'
            ],
            CommitType.STYLE: [
                r'\b(style|format|lint|prettier|eslint)\b',
                r'\b(whitespace|indent|spacing)\b'
            ],
            CommitType.CHORE: [
                r'\b(chore|build|ci|cd|deps|dependencies)\b',
                r'\b(config|setup|maintenance)\b'
            ]
        }
    
    def analyze_commit_trends(self, commits: List[Commit]) -> Dict[str, Any]:
        """Analyze trends in commit data"""
        
        if not commits:
            return {"error": "No commits to analyze"}
        
        # Sort commits by timestamp
        sorted_commits = sorted(commits, key=lambda c: c.timestamp)
        
        # Time-based analysis
        time_analysis = self._analyze_commit_timeline(sorted_commits)
        
        # Contributor analysis
        contributor_analysis = self._analyze_contributors(sorted_commits)
        
        # File analysis
        file_analysis = self._analyze_file_changes(sorted_commits)
        
        # Commit type trends
        type_trends = self._analyze_commit_type_trends(sorted_commits)
        
        # Impact analysis
        impact_analysis = self._analyze_commit_impact(sorted_commits)
        
        return {
            "summary": {
                "total_commits": len(commits),
                "time_span": (sorted_commits[-1].timestamp - sorted_commits[0].timestamp).total_seconds() / 3600,
                "unique_contributors": len(set(c.author.email for c in commits)),
                "files_affected": len(set(f.filename for c in commits for f in c.files_changed)),
                "total_changes": sum(c.total_changes for c in commits)
            },
            "time_analysis": time_analysis,
            "contributors": contributor_analysis,
            "files": file_analysis,
            "types": type_trends,
            "impact": impact_analysis
        }
    
    def _analyze_commit_timeline(self, commits: List[Commit]) -> Dict[str, Any]:
        """Analyze commit patterns over time"""
        
        # Group commits by hour
        hourly_commits = defaultdict(int)
        hourly_changes = defaultdict(int)
        
        for commit in commits:
            hour_key = commit.timestamp.strftime("%Y-%m-%d %H:00")
            hourly_commits[hour_key] += 1
            hourly_changes[hour_key] += commit.total_changes
        
        # Find peak activity
        peak_hour = max(hourly_commits.items(), key=lambda x: x[1]) if hourly_commits else None
        
        # Calculate velocity (commits per hour)
        if len(commits) > 1:
            time_span = (commits[-1].timestamp - commits[0].timestamp).total_seconds() / 3600
            velocity = len(commits) / time_span if time_span > 0 else 0
        else:
            velocity = 0
        
        return {
            "hourly_distribution": dict(hourly_commits),
            "hourly_changes": dict(hourly_changes),
            "peak_activity": {
                "hour": peak_hour[0] if peak_hour else None,
                "commits": peak_hour[1] if peak_hour else 0
            },
            "velocity_commits_per_hour": round(velocity, 2)
        }
    
    def _analyze_contributors(self, commits: List[Commit]) -> Dict[str, Any]:
        """Analyze contributor patterns"""
        
        contributor_stats = defaultdict(lambda: {
            "commits": 0,
            "additions": 0,
            "deletions": 0,
            "files_changed": set(),
            "commit_types": defaultdict(int),
            "first_commit": None,
            "last_commit": None
        })
        
        for commit in commits:
            key = commit.author.email
            stats = contributor_stats[key]
            
            stats["commits"] += 1
            stats["additions"] += commit.additions
            stats["deletions"] += commit.deletions
            stats["files_changed"].update(f.filename for f in commit.files_changed)
            stats["commit_types"][commit.commit_type.value] += 1
            
            if stats["first_commit"] is None or commit.timestamp < stats["first_commit"]:
                stats["first_commit"] = commit.timestamp
            if stats["last_commit"] is None or commit.timestamp > stats["last_commit"]:
                stats["last_commit"] = commit.timestamp
        
        # Convert to serializable format
        result = {}
        for email, stats in contributor_stats.items():
            # Find the contributor name
            contributor_name = next(
                (c.author.name for c in commits if c.author.email == email),
                email.split('@')[0]
            )
            
            result[contributor_name] = {
                "email": email,
                "commits": stats["commits"],
                "additions": stats["additions"],
                "deletions": stats["deletions"],
                "files_changed": len(stats["files_changed"]),
                "dominant_type": max(stats["commit_types"].items(), key=lambda x: x[1])[0] if stats["commit_types"] else "unknown",
                "activity_span_hours": (stats["last_commit"] - stats["first_commit"]).total_seconds() / 3600 if stats["last_commit"] and stats["first_commit"] else 0
            }
        
        # Sort by commits
        sorted_contributors = sorted(result.items(), key=lambda x: x[1]["commits"], reverse=True)
        
        return {
            "total_contributors": len(result),
            "top_contributors": dict(sorted_contributors[:10]),
            "collaboration_score": len(result) / len(commits) if commits else 0
        }
    
    def _analyze_file_changes(self, commits: List[Commit]) -> Dict[str, Any]:
        """Analyze file change patterns"""
        
        file_stats = defaultdict(lambda: {
            "changes": 0,
            "commits": 0,
            "additions": 0,
            "deletions": 0,
            "contributors": set()
        })
        
        for commit in commits:
            for file_change in commit.files_changed:
                filename = file_change.filename
                stats = file_stats[filename]
                
                stats["changes"] += file_change.changes
                stats["commits"] += 1
                stats["additions"] += file_change.additions
                stats["deletions"] += file_change.deletions
                stats["contributors"].add(commit.author.email)
        
        # Convert to serializable format and find patterns
        file_analysis = {}
        file_extensions = defaultdict(int)
        directory_changes = defaultdict(int)
        
        for filename, stats in file_stats.items():
            # Extract file extension
            if '.' in filename:
                ext = filename.split('.')[-1].lower()
                file_extensions[ext] += stats["changes"]
            
            # Extract directory
            if '/' in filename:
                directory = '/'.join(filename.split('/')[:-1])
                directory_changes[directory] += stats["changes"]
            
            file_analysis[filename] = {
                "changes": stats["changes"],
                "commits": stats["commits"],
                "additions": stats["additions"],
                "deletions": stats["deletions"],
                "contributors": len(stats["contributors"]),
                "volatility": stats["changes"] / stats["commits"] if stats["commits"] > 0 else 0
            }
        
        # Find most changed files
        most_changed = sorted(file_analysis.items(), key=lambda x: x[1]["changes"], reverse=True)
        
        return {
            "total_files": len(file_analysis),
            "most_changed_files": dict(most_changed[:20]),
            "file_extensions": dict(sorted(file_extensions.items(), key=lambda x: x[1], reverse=True)[:10]),
            "directory_changes": dict(sorted(directory_changes.items(), key=lambda x: x[1], reverse=True)[:10]),
            "average_changes_per_file": sum(stats["changes"] for stats in file_analysis.values()) / len(file_analysis) if file_analysis else 0
        }
    
    def _analyze_commit_type_trends(self, commits: List[Commit]) -> Dict[str, Any]:
        """Analyze commit type trends over time"""
        
        type_counts = Counter(c.commit_type.value for c in commits)
        
        # Analyze type progression over time
        type_timeline = defaultdict(lambda: defaultdict(int))
        
        for commit in commits:
            day_key = commit.timestamp.strftime("%Y-%m-%d")
            type_timeline[day_key][commit.commit_type.value] += 1
        
        # Calculate type ratios
        total_commits = len(commits)
        type_ratios = {
            commit_type: count / total_commits 
            for commit_type, count in type_counts.items()
        } if total_commits > 0 else {}
        
        return {
            "type_distribution": dict(type_counts),
            "type_ratios": type_ratios,
            "dominant_type": type_counts.most_common(1)[0] if type_counts else None,
            "type_timeline": {day: dict(types) for day, types in type_timeline.items()},
            "development_phase": self._classify_development_phase(type_ratios)
        }
    
    def _classify_development_phase(self, type_ratios: Dict[str, float]) -> str:
        """Classify the current development phase based on commit types"""
        
        feature_ratio = type_ratios.get("feature", 0)
        bugfix_ratio = type_ratios.get("bugfix", 0)
        refactor_ratio = type_ratios.get("refactor", 0)
        
        if feature_ratio > 0.4:
            return "active_development"
        elif bugfix_ratio > 0.5:
            return "stabilization"
        elif refactor_ratio > 0.3:
            return "maintenance"
        elif feature_ratio > 0.2 and bugfix_ratio > 0.2:
            return "balanced_development"
        else:
            return "mixed_activity"
    
    def _analyze_commit_impact(self, commits: List[Commit]) -> Dict[str, Any]:
        """Analyze the impact and significance of commits"""
        
        # Classify commits by impact
        high_impact = []
        medium_impact = []
        low_impact = []
        
        for commit in commits:
            impact_score = self._calculate_impact_score(commit)
            
            if impact_score >= 0.7:
                high_impact.append(commit)
            elif impact_score >= 0.4:
                medium_impact.append(commit)
            else:
                low_impact.append(commit)
        
        # Security and breaking change analysis
        security_commits = [c for c in commits if c.affects_security]
        breaking_commits = [c for c in commits if c.is_breaking_change]
        
        return {
            "impact_distribution": {
                "high": len(high_impact),
                "medium": len(medium_impact),
                "low": len(low_impact)
            },
            "security_updates": len(security_commits),
            "breaking_changes": len(breaking_commits),
            "risk_assessment": self._assess_risk_level(commits),
            "notable_commits": [
                {
                    "sha": c.short_sha,
                    "message": c.message.split('\n')[0][:100],
                    "impact_score": self._calculate_impact_score(c),
                    "type": c.commit_type.value
                }
                for c in high_impact[:5]
            ]
        }
    
    def _calculate_impact_score(self, commit: Commit) -> float:
        """Calculate impact score for a commit (0-1)"""
        score = 0.0
        
        # File count impact
        if commit.files_count > 10:
            score += 0.3
        elif commit.files_count > 5:
            score += 0.2
        elif commit.files_count > 1:
            score += 0.1
        
        # Change volume impact
        if commit.total_changes > 500:
            score += 0.3
        elif commit.total_changes > 100:
            score += 0.2
        elif commit.total_changes > 20:
            score += 0.1
        
        # Type-based impact
        type_weights = {
            CommitType.SECURITY: 0.4,
            CommitType.FEATURE: 0.3,
            CommitType.BUGFIX: 0.2,
            CommitType.PERFORMANCE: 0.2,
            CommitType.REFACTOR: 0.1,
            CommitType.DOCUMENTATION: 0.05,
            CommitType.TEST: 0.05,
            CommitType.STYLE: 0.02,
            CommitType.CHORE: 0.02
        }
        
        score += type_weights.get(commit.commit_type, 0.05)
        
        # Breaking change bonus
        if commit.is_breaking_change:
            score += 0.2
        
        # Security bonus
        if commit.affects_security:
            score += 0.2
        
        return min(score, 1.0)
    
    def _assess_risk_level(self, commits: List[Commit]) -> str:
        """Assess overall risk level of the changes"""
        
        total_commits = len(commits)
        if total_commits == 0:
            return "no_changes"
        
        breaking_ratio = sum(1 for c in commits if c.is_breaking_change) / total_commits
        security_ratio = sum(1 for c in commits if c.affects_security) / total_commits
        high_impact_ratio = sum(1 for c in commits if self._calculate_impact_score(c) >= 0.7) / total_commits
        
        if breaking_ratio > 0.1 or security_ratio > 0.2:
            return "high"
        elif high_impact_ratio > 0.3 or breaking_ratio > 0:
            return "medium"
        else:
            return "low"
    
    def generate_insights(self, commits: CommitCollection) -> List[str]:
        """Generate human-readable insights from commit analysis"""
        
        insights = []
        analysis = self.analyze_commit_trends(commits.commits)
        
        if not analysis.get("summary"):
            return ["No commit data available for analysis."]
        
        summary = analysis["summary"]
        
        # Activity insights
        if summary["total_commits"] > 20:
            insights.append(f"🚀 High activity period with {summary['total_commits']} commits")
        elif summary["total_commits"] > 10:
            insights.append(f"📈 Moderate development activity with {summary['total_commits']} commits")
        else:
            insights.append(f"📝 Light development activity with {summary['total_commits']} commits")
        
        # Contributor insights
        if summary["unique_contributors"] > 5:
            insights.append(f"👥 Strong team collaboration with {summary['unique_contributors']} contributors")
        elif summary["unique_contributors"] > 2:
            insights.append(f"🤝 Good team collaboration with {summary['unique_contributors']} contributors")
        
        # File change insights
        if summary["files_affected"] > 50:
            insights.append(f"🔄 Extensive changes across {summary['files_affected']} files")
        elif summary["files_affected"] > 20:
            insights.append(f"📁 Moderate scope with {summary['files_affected']} files affected")
        
        # Type-specific insights
        types = analysis.get("types", {})
        if types.get("development_phase"):
            phase_messages = {
                "active_development": "🛠️ Active feature development phase",
                "stabilization": "🔧 Focus on bug fixes and stabilization",
                "maintenance": "🧹 Maintenance and refactoring period",
                "balanced_development": "⚖️ Balanced development approach",
                "mixed_activity": "🔀 Mixed development activities"
            }
            insights.append(phase_messages.get(types["development_phase"], "📊 Development activity detected"))
        
        # Impact insights
        impact = analysis.get("impact", {})
        if impact.get("security_updates", 0) > 0:
            insights.append(f"🔒 {impact['security_updates']} security updates included")
        
        if impact.get("breaking_changes", 0) > 0:
            insights.append(f"⚠️ {impact['breaking_changes']} breaking changes detected")
        
        # Risk assessment
        risk_level = impact.get("risk_assessment", "low")
        risk_messages = {
            "high": "🔴 High-risk changes - careful deployment recommended",
            "medium": "🟡 Medium-risk changes - standard review process",
            "low": "🟢 Low-risk changes - safe for deployment"
        }
        insights.append(risk_messages.get(risk_level, "📊 Changes assessed"))
        
        return insights[:8]  # Limit to top 8 insights