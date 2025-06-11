#!/usr/bin/env python3
"""
Scheduler for automated commit collection and post generation.
Runs as a separate process to collect commits hourly and generate posts.
"""

import os
import sys
import time
import logging
import schedule
import asyncio
from datetime import datetime, timedelta
from typing import List

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.core.github_collector import GitHubCollector
from app.core.post_generator import PostGenerator
from app.models.post import PostGenerationRequest

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GitHubScheduler:
    def __init__(self):
        self.github_collector = GitHubCollector()
        self.post_generator = PostGenerator()
        self.repositories = settings.github_repos
        self.running = False
        
    def collect_hourly_commits(self):
        """Collect commits from all repositories for the last hour"""
        logger.info("Starting hourly commit collection")
        
        collected_repos = []
        failed_repos = []
        
        for repo in self.repositories:
            try:
                logger.info(f"Collecting commits from {repo}")
                
                # Collect commits for the last hour
                commits = self.github_collector.get_commits_for_period(repo, hours=1)
                
                if commits.commits:
                    # Save to file
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                    filename = f"{repo.replace('/', '_')}_1h_{timestamp}.json"
                    filepath = os.path.join(settings.commit_data_dir, "hourly", filename)
                    
                    self.github_collector.save_commits_to_file(commits, filepath)
                    
                    collected_repos.append({
                        "repository": repo,
                        "commits": len(commits.commits),
                        "file": filepath
                    })
                    
                    logger.info(f"Collected {len(commits.commits)} commits from {repo}")
                else:
                    logger.info(f"No new commits found in {repo}")
                    collected_repos.append({
                        "repository": repo,
                        "commits": 0,
                        "file": None
                    })
                
            except Exception as e:
                logger.error(f"Failed to collect commits from {repo}: {e}")
                failed_repos.append({"repository": repo, "error": str(e)})
        
        logger.info(f"Hourly collection completed. Success: {len(collected_repos)}, Failed: {len(failed_repos)}")
        return collected_repos, failed_repos
    
    def generate_posts_for_period(self, time_period: str = "2h"):
        """Generate posts for all repositories for the specified time period"""
        logger.info(f"Starting post generation for {time_period} period")
        
        generated_posts = []
        failed_posts = []
        
        for repo in self.repositories:
            try:
                logger.info(f"Generating post for {repo} ({time_period})")
                
                # Parse time period
                hours = int(time_period.replace('h', ''))
                
                # Collect commits for the period
                commits = self.github_collector.get_commits_for_period(repo, hours)
                
                if not commits.commits:
                    logger.info(f"No commits found for {repo} in the last {hours} hours")
                    continue
                
                # Generate post
                request = PostGenerationRequest(
                    repository=repo,
                    time_period=time_period,
                    target_audience="general"
                )
                
                response = self.post_generator.generate_post(request, commits)
                
                if response.success:
                    generated_posts.append({
                        "repository": repo,
                        "post_id": response.post.id,
                        "file_path": response.post.output_file_path,
                        "commits_count": len(commits.commits)
                    })
                    logger.info(f"Generated post for {repo}: {response.post.output_file_path}")
                else:
                    failed_posts.append({
                        "repository": repo,
                        "error": response.error_message
                    })
                    logger.error(f"Failed to generate post for {repo}: {response.error_message}")
                
            except Exception as e:
                logger.error(f"Failed to generate post for {repo}: {e}")
                failed_posts.append({
                    "repository": repo,
                    "error": str(e)
                })
        
        logger.info(f"Post generation completed for {time_period}. Success: {len(generated_posts)}, Failed: {len(failed_posts)}")
        return generated_posts, failed_posts
    
    def cleanup_old_files(self, days_to_keep: int = 7):
        """Clean up old commit and post files"""
        logger.info(f"Cleaning up files older than {days_to_keep} days")
        
        cutoff_time = datetime.now() - timedelta(days=days_to_keep)
        
        # Clean up commit files
        commit_dirs = [
            os.path.join(settings.commit_data_dir, "hourly"),
            os.path.join(settings.commit_data_dir, "processed")
        ]
        
        cleaned_files = 0
        
        for directory in commit_dirs:
            if os.path.exists(directory):
                for filename in os.listdir(directory):
                    filepath = os.path.join(directory, filename)
                    if os.path.isfile(filepath):
                        file_time = datetime.fromtimestamp(os.path.getctime(filepath))
                        if file_time < cutoff_time:
                            os.remove(filepath)
                            cleaned_files += 1
                            logger.debug(f"Removed old file: {filepath}")
        
        # Clean up post files
        post_dirs = [
            os.path.join(settings.output_dir, "2h"),
            os.path.join(settings.output_dir, "24h")
        ]
        
        for directory in post_dirs:
            if os.path.exists(directory):
                for filename in os.listdir(directory):
                    filepath = os.path.join(directory, filename)
                    if os.path.isfile(filepath):
                        file_time = datetime.fromtimestamp(os.path.getctime(filepath))
                        if file_time < cutoff_time:
                            os.remove(filepath)
                            cleaned_files += 1
                            logger.debug(f"Removed old file: {filepath}")
        
        logger.info(f"Cleanup completed. Removed {cleaned_files} old files")
        return cleaned_files
    
    def check_api_rate_limits(self):
        """Check and log API rate limits"""
        try:
            github_rate_limit = self.github_collector.check_rate_limit()
            
            if github_rate_limit.get("core"):
                remaining = github_rate_limit["core"]["remaining"]
                limit = github_rate_limit["core"]["limit"]
                reset_time = github_rate_limit["core"]["reset"]
                
                logger.info(f"GitHub API rate limit: {remaining}/{limit} remaining, resets at {reset_time}")
                
                # Warning if rate limit is low
                if remaining < limit * 0.1:
                    logger.warning(f"GitHub API rate limit is low: {remaining}/{limit}")
            
        except Exception as e:
            logger.error(f"Error checking rate limits: {e}")
    
    def run_scheduled_jobs(self):
        """Run all scheduled jobs once"""
        logger.info("Running scheduled jobs")
        
        try:
            # Check rate limits first
            self.check_api_rate_limits()
            
            # Collect hourly commits
            collected, failed_collect = self.collect_hourly_commits()
            
            # Cleanup old files once per day at 2 AM
            current_hour = datetime.now().hour
            if current_hour == 2:
                self.cleanup_old_files()
        
        except Exception as e:
            logger.error(f"Error in scheduled jobs: {e}")
    
    def start(self):
        """Start the scheduler"""
        logger.info("Starting GitHub commit scheduler")
        
        if not self.repositories:
            logger.error("No repositories configured. Please check your .env file.")
            return
        
        # Schedule jobs
        schedule.every().hour.at(":00").do(self.collect_hourly_commits)
        schedule.every().hour.do(self.check_api_rate_limits)
        
        # Note: Post generation is ON-DEMAND via API calls, not scheduled
        
        self.running = True
        
        logger.info(f"Scheduler started. Monitoring {len(self.repositories)} repositories:")
        for repo in self.repositories:
            logger.info(f"  - {repo}")
        
        logger.info("IMPORTANT: Posts are generated ON-DEMAND via API calls")
        logger.info("Scheduler only collects commits automatically every hour")
        
        # Run initial collection
        logger.info("Running initial commit collection...")
        self.collect_hourly_commits()
        
        # Main loop
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal. Shutting down scheduler...")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Error in scheduler main loop: {e}")
                time.sleep(60)  # Wait before retrying
        
        logger.info("Scheduler stopped")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False

def main():
    """Main entry point"""
    logger.info("Initializing GitHub commit scheduler")
    
    scheduler = GitHubScheduler()
    
    try:
        scheduler.start()
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()