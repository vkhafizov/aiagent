import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        # GitHub Configuration
        self.github_token = os.getenv("GITHUB_TOKEN", "")
        self.github_username = os.getenv("GITHUB_USERNAME", "")
        github_repos_str = os.getenv("GITHUB_REPOS", "")
        self.github_repos = [repo.strip() for repo in github_repos_str.split(",") if repo.strip()] if github_repos_str else []
        
        # Claude AI Configuration
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.claude_model = os.getenv("CLAUDE_MODEL", "claude-3-sonnet-20240229")
        
        # App Configuration
        self.app_name = os.getenv("APP_NAME", "AI GitHub Explainer")
        self.debug = os.getenv("DEBUG", "False").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.max_commits_per_hour = int(os.getenv("MAX_COMMITS_PER_HOUR", "100"))
        
        # Commit collection interval
        self.commit_collection_interval = int(os.getenv("COMMIT_COLLECTION_INTERVAL", "3600"))
        
        # Output Configuration
        self.output_dir = os.getenv("OUTPUT_DIR", "./data/posts")
        self.commit_data_dir = os.getenv("COMMIT_DATA_DIR", "./data/commits")
        self.static_files_dir = os.getenv("STATIC_FILES_DIR", "./static")
        
        # Social Media Configuration
        self.max_post_length = int(os.getenv("MAX_POST_LENGTH", "280"))
        self.include_hashtags = os.getenv("INCLUDE_HASHTAGS", "True").lower() == "true"
        self.include_images = os.getenv("INCLUDE_IMAGES", "True").lower() == "true"
        
        # Template Configuration
        self.default_template = os.getenv("DEFAULT_TEMPLATE", "template_general")
        self.template_selection_auto = os.getenv("TEMPLATE_SELECTION_AUTO", "True").lower() == "true"
        
        self._validate_required_fields()
        self._create_directories()
    
    def _validate_required_fields(self):
        if not self.github_token:
            raise ValueError("GitHub token is required")
        if not self.anthropic_api_key:
            raise ValueError("Anthropic API key is required")
        if not self.github_repos:
            print("Warning: No GitHub repositories configured. Add GITHUB_REPOS to your .env file.")
    
    def _create_directories(self):
        directories = [
            self.output_dir,
            self.commit_data_dir,
            self.static_files_dir,
            os.path.join(self.output_dir, "2h"),
            os.path.join(self.output_dir, "24h"),
            os.path.join(self.commit_data_dir, "hourly"),
            os.path.join(self.commit_data_dir, "processed"),
            "logs",
            "app/templates",
            "app/prompts"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

# Global settings instance
settings = Settings()