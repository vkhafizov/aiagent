import os
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .core.config import settings
from .core.github_collector import GitHubCollector
from .core.claude_client import ClaudeClient
from .core.post_generator import PostGenerator
from .models.post import PostGenerationRequest, PostGenerationResponse, PostTemplate
from .models.commit import CommitCollection

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="AI-powered GitHub repository changes explainer",
    version="1.0.0",
    debug=settings.debug
)

# Add CORS middleware - FIXED for frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files if directory exists
if os.path.exists(settings.static_files_dir):
    app.mount("/static", StaticFiles(directory=settings.static_files_dir), name="static")

# Initialize core components
github_collector = GitHubCollector()
claude_client = ClaudeClient()
post_generator = PostGenerator()

# NEW MODELS FOR FRONTEND API
class GeneratePostsRequest(BaseModel):
    repository: str = "QuantumFusion-network/qf-polkavm-sdk"
    time_period: str  # "2h" or "24h"
    format: str = "posts"  # "posts" or "article"

class PostData(BaseModel):
    id: str
    title: str
    content: str
    hashtags: List[str] = []
    timestamp: str
    type: str = "social_post"

class PostsResponse(BaseModel):
    success: bool
    posts: List[PostData] = []
    metadata: dict = {}
    error_message: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.app_name}")
    
    # Create required directories - FIXED path issues
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data/commits/hourly", exist_ok=True)
    os.makedirs("data/posts/2h", exist_ok=True)
    os.makedirs("data/posts/24h", exist_ok=True)
    
    # Test connections
    try:
        rate_limit = github_collector.check_rate_limit()
        logger.info(f"GitHub API rate limit: {rate_limit}")
        
        claude_connected = claude_client.test_connection()
        logger.info(f"Claude API connected: {claude_connected}")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")

@app.get("/health")
async def health_check():
    """Check the health of the application"""
    services = {}
    
    # Check GitHub API
    try:
        rate_limit = github_collector.check_rate_limit()
        services["github"] = {
            "status": "healthy",
            "rate_limit_remaining": rate_limit.get("core", {}).get("remaining", 0)
        }
    except Exception as e:
        services["github"] = {"status": "unhealthy", "error": str(e)}
    
    # Check Claude API
    try:
        claude_connected = claude_client.test_connection()
        services["claude"] = {"status": "healthy" if claude_connected else "unhealthy"}
    except Exception as e:
        services["claude"] = {"status": "unhealthy", "error": str(e)}
    
    return {
        "status": "healthy" if all(s.get("status") == "healthy" for s in services.values()) else "degraded",
        "timestamp": datetime.now().isoformat(),
        "services": services
    }


# NEW ENDPOINT - Get existing posts data for frontend
@app.get("/api/posts-data/{time_period}")
async def get_posts_data(time_period: str):
    """Get existing posts as JSON data for frontend"""
    
    try:
        if time_period not in ["2h", "24h"]:
            raise HTTPException(status_code=400, detail="Time period must be '2h' or '24h'")
        
        posts_dir = os.path.join(settings.output_dir, time_period)
        
        if not os.path.exists(posts_dir):
            return {"posts": [], "count": 0}
        
        posts = []
        for filename in os.listdir(posts_dir):
            if filename.endswith('.html'):
                file_path = os.path.join(posts_dir, filename)
                stat = os.stat(file_path)
                
                # Read HTML file and extract basic info
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    
                    posts.append({
                        "id": filename.replace('.html', ''),
                        "filename": filename,
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "size": stat.st_size,
                        "url": f"/posts/{time_period}/{filename}",
                        "html_content": html_content
                    })
                except Exception as e:
                    logger.error(f"Error reading file {filename}: {e}")
        
        # Sort by creation time, newest first
        posts.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {"posts": posts, "count": len(posts)}
        
    except Exception as e:
        logger.error(f"Error getting posts data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# EXISTING ENDPOINTS (FIXED)
@app.post("/api/generate-posts", response_model=PostsResponse)
async def generate_posts_for_frontend(request: GeneratePostsRequest):
    """Generate posts for frontend - returns JSON data instead of HTML files"""
    
    try:
        logger.info(f"Frontend requesting posts for {request.repository} ({request.time_period})")
        
        # Validate time period
        if request.time_period not in ["2h", "24h"]:
            return PostsResponse(
                success=False,
                error_message="Time period must be '2h' or '24h'"
            )
        
        # Parse time period
        hours = int(request.time_period.replace('h', ''))
        
        # Collect commits from ALL branches by default
        commits = github_collector.get_commits_for_period(request.repository, hours, all_branches=True)
        
        if not commits.commits:
            # Return empty but successful response
            return PostsResponse(
                success=True,
                posts=[],
                metadata={
                    "repository": request.repository,
                    "time_period": request.time_period,
                    "commits_count": 0,
                    "all_branches": True,
                    "message": f"No commits found in the last {hours} hours across all branches"
                }
            )
        
        # Get branch statistics
        branch_stats = {}
        for commit in commits.commits:
            branch_name = commit.branch
            if branch_name not in branch_stats:
                branch_stats[branch_name] = 0
            branch_stats[branch_name] += 1
        
        # Generate post (rest of the method stays the same...)
        post_request = PostGenerationRequest(
            repository=request.repository,
            time_period=request.time_period,
            target_audience="general"
        )
        
        response = await post_generator.generate_post(post_request, commits)
        
        if not response.success:
            return PostsResponse(
                success=False,
                error_message=response.error_message or "Failed to generate post"
            )
        
        # Convert backend post to frontend format (same as before...)
        posts_data = []
        if response.post and response.post.content:
            post_content = response.post.content
            
            posts_data = [
                PostData(
                    id=f"summary_{response.post.id}",
                    title=post_content.title,
                    content=post_content.summary,
                    hashtags=post_content.hashtags,
                    timestamp=response.post.created_at.isoformat(),
                    type="summary"
                ),
                PostData(
                    id=f"technical_{response.post.id}",
                    title="🔧 Technical Highlights",
                    content="\n".join([f"• {highlight}" for highlight in post_content.technical_highlights]),
                    hashtags=post_content.hashtags,
                    timestamp=response.post.created_at.isoformat(),
                    type="technical"
                ),
                PostData(
                    id=f"benefits_{response.post.id}",
                    title="✨ Key Benefits",
                    content="\n".join([f"✅ {benefit}" for benefit in post_content.user_benefits]),
                    hashtags=post_content.hashtags,
                    timestamp=response.post.created_at.isoformat(),
                    type="benefits"
                )
            ]
            
            if post_content.code_snippets:
                snippet = post_content.code_snippets[0]
                posts_data.append(PostData(
                    id=f"code_{response.post.id}",
                    title="💻 Code Spotlight",
                    content=f"{snippet.get('description', 'Code update')}\n\n```{snippet.get('language', 'text')}\n{snippet.get('code', '')}\n```",
                    hashtags=post_content.hashtags,
                    timestamp=response.post.created_at.isoformat(),
                    type="code"
                ))
        
        return PostsResponse(
            success=True,
            posts=posts_data,
            metadata={
                "repository": request.repository,
                "time_period": request.time_period,
                "commits_count": len(commits.commits),
                "all_branches": True,
                "branch_statistics": branch_stats,
                "generated_at": datetime.now().isoformat(),
                "template_used": response.post.template.value if response.post else None
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating posts for frontend: {e}")
        return PostsResponse(
            success=False,
            error_message=f"Internal server error: {str(e)}"
        )

@app.post("/collect-commits/{repository:path}")
@app.get("/collect-commits/{repository:path}")
async def collect_commits(repository: str, hours: int = 2, all_branches: bool = True):
    """Collect commits from a repository for the specified time period"""
    
    try:
        branch_info = "all branches" if all_branches else "default branch only"
        logger.info(f"Collecting commits from {repository} ({branch_info}) for last {hours} hours")
        
        commits = github_collector.get_commits_for_period(repository, hours, all_branches=all_branches)
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        branch_suffix = "_all_branches" if all_branches else "_default_branch"
        filename = f"{repository.replace('/', '_')}_{hours}h{branch_suffix}_{timestamp}.json"
        hourly_dir = os.path.join(settings.commit_data_dir, "hourly")
        os.makedirs(hourly_dir, exist_ok=True)
        filepath = os.path.join(hourly_dir, filename)
        
        github_collector.save_commits_to_file(commits, filepath)
        
        # Get branch statistics
        branch_stats = {}
        for commit in commits.commits:
            branch_name = commit.branch
            if branch_name not in branch_stats:
                branch_stats[branch_name] = 0
            branch_stats[branch_name] += 1
        
        return {
            "success": True,
            "repository": repository,
            "time_period": f"{hours}h",
            "all_branches": all_branches,
            "commits_count": len(commits.commits),
            "branch_statistics": branch_stats,
            "start_time": commits.start_time,
            "end_time": commits.end_time,
            "file_path": filepath
        }
        
    except Exception as e:
        logger.error(f"Error collecting commits: {e}")
        return {
            "success": False,
            "error": str(e),
            "repository": repository,
            "time_period": f"{hours}h",
            "all_branches": all_branches
        }


@app.get("/posts/{time_period}/{filename}")
async def get_post_file(time_period: str, filename: str):
    """Serve generated post HTML files"""
    
    file_path = os.path.join(settings.output_dir, time_period, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Post file not found")
    
    return FileResponse(file_path, media_type="text/html")

@app.get("/posts/{time_period}")
async def list_posts(time_period: str):
    """List all posts for a time period"""
    
    posts_dir = os.path.join(settings.output_dir, time_period)
    
    if not os.path.exists(posts_dir):
        return {"posts": []}
    
    posts = []
    for filename in os.listdir(posts_dir):
        if filename.endswith('.html'):
            file_path = os.path.join(posts_dir, filename)
            stat = os.stat(file_path)
            
            posts.append({
                "filename": filename,
                "created_at": datetime.fromtimestamp(stat.st_ctime),
                "size": stat.st_size,
                "url": f"/posts/{time_period}/{filename}"
            })
    
    # Sort by creation time, newest first
    posts.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {"posts": posts}

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with API documentation"""
    return """
    <html>
        <head>
            <title>AI GitHub Explainer</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
                .method { font-weight: bold; color: #0066cc; }
                .new { background: #e8f5e8; border-left: 4px solid #4caf50; }
            </style>
        </head>
        <body>
            <h1>AI GitHub Explainer API</h1>
            <p>Transform GitHub commits into engaging social media posts!</p>
            
            <h2>Frontend API Endpoints (NEW):</h2>
            
            <div class="endpoint new">
                <span class="method">POST</span> /api/generate-posts - Generate posts for frontend (JSON)
            </div>
            
            <div class="endpoint new">
                <span class="method">GET</span> /api/posts-data/{time_period} - Get posts data (JSON)
            </div>
            
            <h2>Original Endpoints:</h2>
            
            <div class="endpoint">
                <span class="method">GET</span> /health - Health check
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> /collect-commits/{repository} - Collect commits
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> /generate-post - Generate a post
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> /posts/{time_period} - List posts
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> /posts/{time_period}/{filename} - View post
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> /docs - Interactive API documentation
            </div>
            
            <p><a href="/docs">View Interactive API Documentation</a></p>
            <p><strong>Frontend should connect to: <code>/api/generate-posts</code></strong></p>
        </body>
    </html>
    """
@app.get("/debug/commits-simple/{repository:path}")
async def debug_commits_simple(repository: str):
    """Simple test of repository access and recent commits"""
    
    try:
        repo = github_collector.github.get_repo(repository)
        
        # Get last 5 commits
        commits = list(repo.get_commits()[:5])
        
        result = {
            "repository": repository,
            "accessible": True,
            "total_commits_found": len(commits),
            "commits": []
        }
        
        for commit in commits:
            commit_date = commit.commit.author.date
            if commit_date.tzinfo is None:
                commit_date = commit_date.replace(tzinfo=timezone.utc)
            
            hours_ago = (datetime.now(timezone.utc) - commit_date).total_seconds() / 3600
            
            result["commits"].append({
                "sha": commit.sha[:7],
                "message": commit.commit.message.split('\n')[0][:100],
                "date": commit_date.isoformat(),
                "hours_ago": round(hours_ago, 1)
            })
        
        return result
        
    except Exception as e:
        return {
            "repository": repository,
            "accessible": False,
            "error": str(e)
        }

@app.get("/debug/commits-detailed/{repository:path}")
async def debug_commits_detailed(repository: str, hours: int = 2):
    """Detailed debug of commit collection process"""
    
    debug_info = {
        "step": "starting",
        "repository": repository,
        "hours_requested": hours,
        "errors": []
    }
    
    try:
        # Step 1: Test basic repository access
        debug_info["step"] = "accessing_repository"
        repo = github_collector.github.get_repo(repository)
        debug_info["repo_access"] = {
            "success": True,
            "name": repo.full_name,
            "private": repo.private
        }
        
        # Step 2: Get recent commits WITHOUT time filter
        debug_info["step"] = "getting_recent_commits_no_filter"
        all_recent_commits = list(repo.get_commits()[:10])
        
        recent_commits_info = []
        for commit in all_recent_commits:
            commit_date = commit.commit.author.date
            if commit_date.tzinfo is None:
                commit_date = commit_date.replace(tzinfo=timezone.utc)
            
            hours_ago = (datetime.now(timezone.utc) - commit_date).total_seconds() / 3600
            
            recent_commits_info.append({
                "sha": commit.sha[:7],
                "message": commit.commit.message.split('\n')[0][:80],
                "author": commit.author.login if commit.author else "Unknown",
                "date": commit_date.isoformat(),
                "hours_ago": round(hours_ago, 1)
            })
        
        debug_info["recent_commits"] = {
            "total_found": len(all_recent_commits),
            "commits": recent_commits_info
        }
        
        # Step 3: Test time range calculation
        debug_info["step"] = "calculating_time_range"
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)
        
        debug_info["time_range"] = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "hours_span": hours
        }
        
        # Step 4: Test GitHub API with time filter
        debug_info["step"] = "testing_github_api_with_filter"
        
        # Test 1: exactly as our code does it
        filtered_commits_1 = list(repo.get_commits(since=start_time, until=end_time))
        debug_info["github_api_test_1"] = {
            "method": "get_commits(since=start_time, until=end_time)",
            "results": len(filtered_commits_1)
        }
        
        # Test 2: only since parameter
        filtered_commits_2 = list(repo.get_commits(since=start_time))
        debug_info["github_api_test_2"] = {
            "method": "get_commits(since=start_time)",
            "results": len(filtered_commits_2)
        }
        
        # Step 5: Test our actual method
        debug_info["step"] = "testing_our_method"
        try:
            our_result = github_collector.get_commits_for_period(repository, hours)
            debug_info["our_method_result"] = {
                "success": True,
                "commits_count": len(our_result.commits),
                "start_time": our_result.start_time.isoformat(),
                "end_time": our_result.end_time.isoformat()
            }
        except Exception as e:
            debug_info["our_method_result"] = {
                "success": False,
                "error": str(e)
            }
        
        return debug_info
        
    except Exception as e:
        debug_info["step"] = "error"
        debug_info["error"] = str(e)
        debug_info["errors"].append(str(e))
        return debug_info
    
@app.get("/debug/test-all-branches/{repository:path}")
async def debug_test_all_branches(repository: str, hours: int = 24):
    """Test commit collection from all branches vs default branch only"""
    
    try:
        # Test default branch only
        logger.info(f"Testing default branch only for {repository}")
        default_commits = github_collector.get_commits_for_period(repository, hours, all_branches=False)
        
        # Test all branches
        logger.info(f"Testing all branches for {repository}")
        all_branches_commits = github_collector.get_commits_for_period(repository, hours, all_branches=True)
        
        # Analyze differences
        default_shas = set(c.sha for c in default_commits.commits)
        all_shas = set(c.sha for c in all_branches_commits.commits)
        
        only_in_branches = all_shas - default_shas
        branch_only_commits = [c for c in all_branches_commits.commits if c.sha in only_in_branches]
        
        # Branch statistics for all branches
        branch_stats = {}
        for commit in all_branches_commits.commits:
            branch_name = commit.branch
            if branch_name not in branch_stats:
                branch_stats[branch_name] = {
                    "count": 0,
                    "commits": []
                }
            branch_stats[branch_name]["count"] += 1
            branch_stats[branch_name]["commits"].append({
                "sha": commit.sha[:7],
                "message": commit.message.split('\n')[0][:80],
                "hours_ago": round((datetime.now(timezone.utc) - commit.timestamp).total_seconds() / 3600, 1)
            })
        
        return {
            "repository": repository,
            "time_period": f"{hours}h",
            "comparison": {
                "default_branch_only": {
                    "count": len(default_commits.commits),
                    "commits": [
                        {
                            "sha": c.sha[:7],
                            "message": c.message.split('\n')[0][:80],
                            "branch": c.branch,
                            "hours_ago": round((datetime.now(timezone.utc) - c.timestamp).total_seconds() / 3600, 1)
                        } for c in default_commits.commits[:10]  # First 10
                    ]
                },
                "all_branches": {
                    "count": len(all_branches_commits.commits),
                    "commits": [
                        {
                            "sha": c.sha[:7],
                            "message": c.message.split('\n')[0][:80],
                            "branch": c.branch,
                            "hours_ago": round((datetime.now(timezone.utc) - c.timestamp).total_seconds() / 3600, 1)
                        } for c in all_branches_commits.commits[:10]  # First 10
                    ]
                },
                "branch_only_commits": {
                    "count": len(branch_only_commits),
                    "commits": [
                        {
                            "sha": c.sha[:7],
                            "message": c.message.split('\n')[0][:80],
                            "branch": c.branch,
                            "hours_ago": round((datetime.now(timezone.utc) - c.timestamp).total_seconds() / 3600, 1)
                        } for c in branch_only_commits[:10]  # First 10
                    ]
                }
            },
            "branch_statistics": branch_stats,
            "summary": {
                "additional_commits_found": len(only_in_branches),
                "branches_with_commits": len(branch_stats),
                "most_active_branch": max(branch_stats.items(), key=lambda x: x[1]["count"])[0] if branch_stats else None
            }
        }
        
    except Exception as e:
        return {"error": str(e)}

@app.get("/debug/deep-analysis/{repository:path}")
async def debug_deep_analysis(repository: str):
    """Deep analysis of GitHub repository and API responses"""
    
    try:
        repo = github_collector.github.get_repo(repository)
        
        # Current time info
        now_utc = datetime.now(timezone.utc)
        now_local = datetime.now()
        
        # Get raw repository info
        repo_info = {
            "name": repo.full_name,
            "default_branch": repo.default_branch,
            "private": repo.private,
            "pushed_at": repo.pushed_at.isoformat() if repo.pushed_at else None,
            "created_at": repo.created_at.isoformat() if repo.created_at else None,
            "updated_at": repo.updated_at.isoformat() if repo.updated_at else None
        }
        
        # Get the very latest commits WITHOUT any filters
        latest_commits_raw = []
        try:
            for commit in repo.get_commits()[:20]:  # Get 20 most recent commits
                commit_date = commit.commit.author.date
                
                # Calculate time difference in multiple ways
                if commit_date.tzinfo is None:
                    commit_utc = commit_date.replace(tzinfo=timezone.utc)
                else:
                    commit_utc = commit_date
                
                hours_ago_utc = (now_utc - commit_utc).total_seconds() / 3600
                
                latest_commits_raw.append({
                    "sha": commit.sha[:7],
                    "message": commit.commit.message.split('\n')[0][:100],
                    "author": commit.author.login if commit.author else "Unknown",
                    "date_original": commit_date.isoformat(),
                    "date_timezone": str(commit_date.tzinfo),
                    "date_utc": commit_utc.isoformat(),
                    "hours_ago": round(hours_ago_utc, 1),
                    "minutes_ago": round(hours_ago_utc * 60, 1),
                    "is_within_24h": hours_ago_utc <= 24,
                    "is_within_1h": hours_ago_utc <= 1
                })
        except Exception as e:
            latest_commits_raw = [{"error": str(e)}]
        
        # Test different time filters manually
        time_tests = {}
        
        # Test 1: Last 24 hours
        try:
            last_24h = now_utc - timedelta(hours=24)
            commits_24h = list(repo.get_commits(since=last_24h))
            time_tests["last_24_hours"] = {
                "since": last_24h.isoformat(),
                "count": len(commits_24h),
                "commits": [{"sha": c.sha[:7], "date": c.commit.author.date.isoformat()} for c in commits_24h[:5]]
            }
        except Exception as e:
            time_tests["last_24_hours"] = {"error": str(e)}
        
        return {
            "repository": repository,
            "analysis_time": {
                "utc": now_utc.isoformat(),
                "local": now_local.isoformat(),
                "timezone": str(now_local.astimezone().tzinfo)
            },
            "repository_info": repo_info,
            "latest_commits_raw": latest_commits_raw,
            "time_filter_tests": time_tests,
            "summary": {
                "commits_within_24h": len([c for c in latest_commits_raw if isinstance(c, dict) and c.get("is_within_24h")]),
                "api_finds_24h": time_tests.get("last_24_hours", {}).get("count", 0)
            }
        }
        
    except Exception as e:
        return {
            "repository": repository,
            "error": str(e),
            "error_type": type(e).__name__
        }

@app.get("/debug/recent-commits/{repository:path}")
async def debug_recent_commits(repository: str, count: int = 10):
    """Get recent commits with detailed timestamp info"""
    
    try:
        repo = github_collector.github.get_repo(repository)
        commits = list(repo.get_commits()[:count])
        
        now_utc = datetime.now(timezone.utc)
        
        result = []
        for commit in commits:
            commit_date = commit.commit.author.date
            if commit_date.tzinfo is None:
                commit_date = commit_date.replace(tzinfo=timezone.utc)
            
            hours_ago = (now_utc - commit_date).total_seconds() / 3600
            
            result.append({
                "sha": commit.sha[:7],
                "message": commit.commit.message.split('\n')[0][:100],
                "author": commit.author.login if commit.author else "Unknown",
                "date": commit_date.isoformat(),
                "hours_ago": round(hours_ago, 1),
                "days_ago": round(hours_ago / 24, 1)
            })
        
        return {
            "repository": repository,
            "current_time_utc": now_utc.isoformat(),
            "commits": result
        }
        
    except Exception as e:
        return {"error": str(e)}
    
@app.get("/debug/repository-events/{repository:path}")
async def debug_repository_events(repository: str):
    """Check repository events to see what was pushed"""
    
    try:
        repo = github_collector.github.get_repo(repository)
        
        # Get recent events
        events = list(repo.get_events()[:20])
        
        recent_events = []
        for event in events:
            event_date = event.created_at
            if event_date.tzinfo is None:
                event_date = event_date.replace(tzinfo=timezone.utc)
            
            hours_ago = (datetime.now(timezone.utc) - event_date).total_seconds() / 3600
            
            recent_events.append({
                "type": event.type,
                "created_at": event_date.isoformat(),
                "hours_ago": round(hours_ago, 1),
                "actor": event.actor.login if event.actor else "Unknown",
                "payload": {
                    "ref": getattr(event.payload, 'ref', None),
                    "size": getattr(event.payload, 'size', None),
                    "commits": len(getattr(event.payload, 'commits', []))
                }
            })
        
        return {
            "repository": repository,
            "pushed_at": repo.pushed_at.isoformat(),
            "hours_since_push": round((datetime.now(timezone.utc) - repo.pushed_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600, 1),
            "recent_events": recent_events,
            "events_within_24h": len([e for e in recent_events if e["hours_ago"] <= 24])
        }
        
    except Exception as e:
        return {"error": str(e)}

@app.get("/debug/all-branches/{repository:path}")
async def debug_all_branches(repository: str):
    """Check ALL branches for recent commits"""
    
    try:
        repo = github_collector.github.get_repo(repository)
        
        # Get ALL branches
        all_branches = list(repo.get_branches())
        
        branch_analysis = {}
        recent_activity = []
        
        for branch in all_branches:
            try:
                # Get latest commit from this branch
                latest_commit = repo.get_commits(sha=branch.name)[0]
                commit_date = latest_commit.commit.author.date
                
                if commit_date.tzinfo is None:
                    commit_date = commit_date.replace(tzinfo=timezone.utc)
                
                hours_ago = (datetime.now(timezone.utc) - commit_date).total_seconds() / 3600
                
                branch_info = {
                    "name": branch.name,
                    "latest_commit": {
                        "sha": latest_commit.sha[:7],
                        "message": latest_commit.commit.message.split('\n')[0][:100],
                        "author": latest_commit.author.login if latest_commit.author else "Unknown",
                        "date": commit_date.isoformat(),
                        "hours_ago": round(hours_ago, 1)
                    }
                }
                
                branch_analysis[branch.name] = branch_info
                
                # If commit is within 24 hours, add to recent activity
                if hours_ago <= 24:
                    recent_activity.append(branch_info)
                    
            except Exception as e:
                branch_analysis[branch.name] = {"error": str(e)}
        
        return {
            "repository": repository,
            "total_branches": len(all_branches),
            "branches_analyzed": len(branch_analysis),
            "recent_activity_24h": recent_activity,
            "all_branches": branch_analysis
        }
        
    except Exception as e:
        return {"error": str(e)}

@app.get("/debug/test-specific-branches/{repository:path}")
async def debug_test_specific_branches(repository: str, hours: int = 24):
    """Test specific branches that should have recent commits"""
    
    try:
        repo = github_collector.github.get_repo(repository)
        
        # Test specific branches we know have recent commits
        target_branches = [
            "khssnv/qf-polkavm-runtime-api",
            "feat/srtool-ci", 
            "main"
        ]
        
        now_utc = datetime.now(timezone.utc)
        cutoff_time = now_utc - timedelta(hours=hours)
        
        results = {}
        
        for branch_name in target_branches:
            try:
                # Test 1: Get commits without time filter
                all_commits = list(repo.get_commits(sha=branch_name)[:5])
                
                # Test 2: Get commits WITH time filter
                filtered_commits = list(repo.get_commits(sha=branch_name, since=cutoff_time))
                
                # Test 3: Manual time check
                manual_check = []
                for commit in all_commits:
                    commit_date = commit.commit.author.date
                    if commit_date.tzinfo is None:
                        commit_date = commit_date.replace(tzinfo=timezone.utc)
                    
                    hours_ago = (now_utc - commit_date).total_seconds() / 3600
                    is_recent = hours_ago <= hours
                    
                    manual_check.append({
                        "sha": commit.sha[:7],
                        "message": commit.commit.message.split('\n')[0][:80],
                        "date": commit_date.isoformat(),
                        "hours_ago": round(hours_ago, 1),
                        "should_be_included": is_recent
                    })
                
                results[branch_name] = {
                    "all_commits_count": len(all_commits),
                    "filtered_commits_count": len(filtered_commits),
                    "manual_check": manual_check,
                    "should_have_recent": len([c for c in manual_check if c["should_be_included"]]),
                    "api_finds_recent": len(filtered_commits)
                }
                
            except Exception as e:
                results[branch_name] = {"error": str(e)}
        
        # Test our method on specific branch
        try:
            test_branch = "khssnv/qf-polkavm-runtime-api"
            our_method_result = github_collector.get_commits(
                repository, 
                since=cutoff_time, 
                until=now_utc, 
                all_branches=True
            )
            
            our_method_test = {
                "total_commits_found": len(our_method_result),
                "commits": [
                    {
                        "sha": c.sha[:7],
                        "branch": c.branch,
                        "message": c.message.split('\n')[0][:80],
                        "hours_ago": round((now_utc - c.timestamp).total_seconds() / 3600, 1)
                    } for c in our_method_result[:10]
                ]
            }
        except Exception as e:
            our_method_test = {"error": str(e)}
        
        return {
            "repository": repository,
            "time_range": {
                "cutoff": cutoff_time.isoformat(),
                "now": now_utc.isoformat(),
                "hours": hours
            },
            "branch_tests": results,
            "our_method_test": our_method_test,
            "summary": {
                "branches_tested": len(target_branches),
                "branches_with_recent_commits": len([b for b in results.values() if isinstance(b, dict) and b.get("should_have_recent", 0) > 0]),
                "api_working_correctly": all(
                    b.get("should_have_recent") == b.get("api_finds_recent") 
                    for b in results.values() 
                    if isinstance(b, dict) and "should_have_recent" in b
                )
            }
        }
        
    except Exception as e:
        return {"error": str(e)}
    
@app.get("/debug/test-our-method/{repository:path}")
async def debug_test_our_method(repository: str, hours: int = 24):
    """Direct test of our get_commits_all_branches method"""
    
    try:
        # Test with all_branches=True
        result_all_branches = github_collector.get_commits_for_period(
            repository, hours, all_branches=True
        )
        
        # Test with all_branches=False  
        result_default_only = github_collector.get_commits_for_period(
            repository, hours, all_branches=False
        )
        
        return {
            "repository": repository,
            "hours": hours,
            "all_branches_result": {
                "commits_count": len(result_all_branches.commits),
                "start_time": result_all_branches.start_time.isoformat(),
                "end_time": result_all_branches.end_time.isoformat(),
                "commits": [
                    {
                        "sha": c.sha[:7],
                        "branch": c.branch,
                        "message": c.message.split('\n')[0][:80],
                        "author": c.author.username,
                        "hours_ago": round((datetime.now(timezone.utc) - c.timestamp).total_seconds() / 3600, 1)
                    } for c in result_all_branches.commits
                ]
            },
            "default_only_result": {
                "commits_count": len(result_default_only.commits),
                "commits": [
                    {
                        "sha": c.sha[:7],
                        "branch": c.branch,
                        "hours_ago": round((datetime.now(timezone.utc) - c.timestamp).total_seconds() / 3600, 1)
                    } for c in result_default_only.commits
                ]
            }
        }
        
    except Exception as e:
        return {"error": str(e)}
    
@app.get("/debug/claude-response/{repository:path}")
async def debug_claude_response(repository: str, hours: int = 24):
    """Debug what Claude API returns"""
    
    try:
        # Collect commits
        commits = github_collector.get_commits_for_period(repository, hours, all_branches=True)
        
        if not commits.commits:
            return {"error": "No commits found"}
        
        # Test Claude API directly
        claude_response = claude_client.generate_post_content(
            commits=commits,
            target_audience="general",
            force_template=None
        )
        
        return {
            "repository": repository,
            "commits_count": len(commits.commits),
            "commits_sample": [
                {
                    "sha": c.sha[:7],
                    "message": c.message.split('\n')[0][:100],
                    "branch": c.branch
                } for c in commits.commits[:5]
            ],
            "claude_raw_response": claude_response,
            "claude_response_type": type(claude_response).__name__,
            "claude_response_keys": list(claude_response.keys()) if isinstance(claude_response, dict) else "Not a dict"
        }
        
    except Exception as e:
        return {"error": str(e)}
    
@app.post("/debug/generate-posts", response_model=PostsResponse)
async def debug_generate_posts(request: GeneratePostsRequest):
    """Debug version of generate posts with detailed logging"""
    
    try:
        logger.info(f"Debug: Frontend requesting posts for {request.repository} ({request.time_period})")
        
        # Parse time period
        hours = int(request.time_period.replace('h', ''))
        
        # Collect commits
        commits = github_collector.get_commits_for_period(request.repository, hours, all_branches=True)
        logger.info(f"Debug: Found {len(commits.commits)} commits")
        
        if not commits.commits:
            return PostsResponse(
                success=True,
                posts=[],
                metadata={
                    "repository": request.repository,
                    "time_period": request.time_period,
                    "commits_count": 0,
                    "message": f"No commits found in the last {hours} hours across all branches"
                }
            )
        
        # Generate post
        post_request = PostGenerationRequest(
            repository=request.repository,
            time_period=request.time_period,
            target_audience="general"
        )
        
        response = await post_generator.generate_post(post_request, commits)
        logger.info(f"Debug: Post generation success: {response.success}")
        
        if not response.success:
            logger.error(f"Debug: Post generation error: {response.error_message}")
            return PostsResponse(
                success=False,
                error_message=response.error_message or "Failed to generate post"
            )
        
        # Log the generated content
        if response.post and response.post.content:
            post_content = response.post.content
            logger.info(f"Debug: Generated title: {post_content.title}")
            logger.info(f"Debug: Generated summary: {post_content.summary[:100]}...")
            logger.info(f"Debug: Technical highlights count: {len(post_content.technical_highlights)}")
            logger.info(f"Debug: User benefits count: {len(post_content.user_benefits)}")
        else:
            logger.error("Debug: No post content generated!")
        
        # Convert to frontend format
        posts_data = []
        if response.post and response.post.content:
            post_content = response.post.content
            
            posts_data = [
                PostData(
                    id=f"summary_{response.post.id}",
                    title=post_content.title,
                    content=post_content.summary,
                    hashtags=post_content.hashtags,
                    timestamp=response.post.created_at.isoformat(),
                    type="summary"
                ),
                PostData(
                    id=f"technical_{response.post.id}",
                    title="🔧 Technical Highlights",
                    content="\n".join([f"• {highlight}" for highlight in post_content.technical_highlights]),
                    hashtags=post_content.hashtags,
                    timestamp=response.post.created_at.isoformat(),
                    type="technical"
                ),
                PostData(
                    id=f"benefits_{response.post.id}",
                    title="✨ Key Benefits",
                    content="\n".join([f"✅ {benefit}" for benefit in post_content.user_benefits]),
                    hashtags=post_content.hashtags,
                    timestamp=response.post.created_at.isoformat(),
                    type="benefits"
                )
            ]
        
        logger.info(f"Debug: Returning {len(posts_data)} posts to frontend")
        for i, post in enumerate(posts_data):
            logger.info(f"Debug: Post {i+1} - Title: {post.title}, Content length: {len(post.content)}")
        
        return PostsResponse(
            success=True,
            posts=posts_data,
            metadata={
                "repository": request.repository,
                "time_period": request.time_period,
                "commits_count": len(commits.commits),
                "generated_at": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Debug: Error generating posts: {e}")
        return PostsResponse(
            success=False,
            error_message=f"Internal server error: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )