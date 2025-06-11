import logging
from typing import Optional
from ..models.commit import CommitCollection, CommitType
from ..models.post import PostType, PostTemplate

logger = logging.getLogger(__name__)

class TemplateSelector:
    """Selects the most appropriate template based on commit analysis"""
    
    def __init__(self):
        self.template_rules = {
            # Security-focused commits
            "security": {
                "template": PostTemplate.SECURITY,
                "keywords": ["security", "vulnerability", "auth", "encrypt", "token"],
                "commit_types": [CommitType.SECURITY],
                "min_security_commits": 1
            },
            
            # Feature-focused commits
            "feature": {
                "template": PostTemplate.FEATURE,
                "keywords": ["feature", "add", "new", "implement", "create"],
                "commit_types": [CommitType.FEATURE],
                "min_feature_ratio": 0.3
            },
            
            # Performance-focused commits
            "performance": {
                "template": PostTemplate.PERFORMANCE,
                "keywords": ["performance", "optimize", "speed", "fast", "cache"],
                "commit_types": [CommitType.PERFORMANCE],
                "min_performance_ratio": 0.2
            },
            
            # Bug fix-focused commits
            "bugfix": {
                "template": PostTemplate.BUGFIX,
                "keywords": ["fix", "bug", "issue", "resolve", "correct"],
                "commit_types": [CommitType.BUGFIX],
                "min_bugfix_ratio": 0.4
            }
        }
    
    def select_template(self, commits: CommitCollection, force_template: Optional[PostTemplate] = None) -> PostTemplate:
        """Select the most appropriate template for the given commits"""
        
        if force_template:
            logger.info(f"Using forced template: {force_template}")
            return force_template
        
        if not commits.commits:
            logger.info("No commits found, using general template")
            return PostTemplate.GENERAL
        
        # Calculate scores for each template type
        scores = {}
        total_commits = len(commits.commits)
        
        for rule_name, rule in self.template_rules.items():
            score = self._calculate_template_score(commits, rule, total_commits)
            scores[rule_name] = score
            logger.debug(f"Template {rule_name} score: {score}")
        
        # Select template with highest score
        if scores:
            best_template_rule = max(scores.items(), key=lambda x: x[1])
            template_name, score = best_template_rule
            
            # Only use specialized template if score is above threshold
            if score > 0.3:
                selected_template = self.template_rules[template_name]["template"]
                logger.info(f"Selected template: {selected_template} (score: {score:.2f})")
                return selected_template
        
        # Default to general template
        logger.info("Using general template (no specialized template met threshold)")
        return PostTemplate.GENERAL
    
    def _calculate_template_score(self, commits: CommitCollection, rule: dict, total_commits: int) -> float:
        """Calculate how well a template rule matches the commits"""
        score = 0.0
        
        # Check commit type distribution
        for commit_type in rule.get("commit_types", []):
            type_count = commits.commit_types.get(commit_type, 0)
            type_ratio = type_count / total_commits if total_commits > 0 else 0
            score += type_ratio * 0.5  # Weight: 50%
        
        # Check keyword frequency in commit messages
        keyword_matches = 0
        total_words = 0
        
        for commit in commits.commits:
            words = commit.message.lower().split()
            total_words += len(words)
            
            for keyword in rule.get("keywords", []):
                keyword_matches += sum(1 for word in words if keyword in word)
        
        if total_words > 0:
            keyword_score = min(keyword_matches / total_words * 10, 0.3)  # Cap at 30%
            score += keyword_score
        
        # Check specific rule conditions
        if "min_security_commits" in rule:
            security_commits = commits.security_updates
            if security_commits >= rule["min_security_commits"]:
                score += 0.4  # High weight for security
        
        if "min_feature_ratio" in rule:
            feature_commits = commits.commit_types.get(CommitType.FEATURE, 0)
            feature_ratio = feature_commits / total_commits if total_commits > 0 else 0
            if feature_ratio >= rule["min_feature_ratio"]:
                score += 0.3
        
        if "min_performance_ratio" in rule:
            perf_commits = commits.commit_types.get(CommitType.PERFORMANCE, 0)
            perf_ratio = perf_commits / total_commits if total_commits > 0 else 0
            if perf_ratio >= rule["min_performance_ratio"]:
                score += 0.3
        
        if "min_bugfix_ratio" in rule:
            bugfix_commits = commits.commit_types.get(CommitType.BUGFIX, 0)
            bugfix_ratio = bugfix_commits / total_commits if total_commits > 0 else 0
            if bugfix_ratio >= rule["min_bugfix_ratio"]:
                score += 0.3
        
        # Bonus for breaking changes (suggests major feature)
        if commits.breaking_changes > 0 and CommitType.FEATURE in rule.get("commit_types", []):
            score += 0.2
        
        return min(score, 1.0)  # Cap at 1.0
    
    def get_template_recommendations(self, commits: CommitCollection) -> dict:
        """Get recommendations for all templates with their scores"""
        total_commits = len(commits.commits)
        recommendations = {}
        
        for rule_name, rule in self.template_rules.items():
            score = self._calculate_template_score(commits, rule, total_commits)
            recommendations[rule_name] = {
                "template": rule["template"],
                "score": score,
                "reasoning": self._get_template_reasoning(commits, rule, score)
            }
        
        return recommendations
    
    def _get_template_reasoning(self, commits: CommitCollection, rule: dict, score: float) -> str:
        """Generate human-readable reasoning for template selection"""
        reasons = []
        
        # Check commit types
        for commit_type in rule.get("commit_types", []):
            count = commits.commit_types.get(commit_type, 0)
            if count > 0:
                reasons.append(f"{count} {commit_type.value} commits")
        
        # Check special conditions
        if commits.security_updates > 0 and "min_security_commits" in rule:
            reasons.append(f"{commits.security_updates} security updates")
        
        if commits.breaking_changes > 0:
            reasons.append(f"{commits.breaking_changes} breaking changes")
        
        # Check keyword matches
        keyword_matches = []
        for commit in commits.commits[:5]:  # Check first 5 commits
            for keyword in rule.get("keywords", []):
                if keyword in commit.message.lower():
                    keyword_matches.append(keyword)
        
        if keyword_matches:
            unique_keywords = list(set(keyword_matches))
            reasons.append(f"Keywords: {', '.join(unique_keywords[:3])}")
        
        if not reasons:
            reasons.append("Low relevance score")
        
        return f"Score: {score:.2f} - " + "; ".join(reasons)