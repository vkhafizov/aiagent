import os
import logging
import asyncio
from datetime import datetime, timedelta
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

# NEW ENDPOINT FOR FRONTEND - Generate posts and return JSON data
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
        
        # Collect commits
        commits = github_collector.get_commits_for_period(request.repository, hours)
        
        if not commits.commits:
            # Return empty but successful response
            return PostsResponse(
                success=True,
                posts=[],
                metadata={
                    "repository": request.repository,
                    "time_period": request.time_period,
                    "commits_count": 0,
                    "message": f"No commits found in the last {hours} hours"
                }
            )
        
        # Generate post
        post_request = PostGenerationRequest(
            repository=request.repository,
            time_period=request.time_period,
            target_audience="general"
        )
        
        response = post_generator.generate_post(post_request, commits)
        
        if not response.success:
            return PostsResponse(
                success=False,
                error_message=response.error_message or "Failed to generate post"
            )
        
        # Convert backend post to frontend format
        posts_data = []
        if response.post and response.post.content:
            post_content = response.post.content
            
            # Create multiple social media posts from the generated content
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
            
            # Add code snippet post if available
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
@app.post("/generate-post", response_model=PostGenerationResponse)
async def generate_post(request: PostGenerationRequest):
    """Generate a post for a specific repository and time period"""
    
    try:
        logger.info(f"Generating post for {request.repository} ({request.time_period})")
        
        # Parse time period
        if request.time_period.endswith('h'):
            hours = int(request.time_period[:-1])
        else:
            raise HTTPException(status_code=400, detail="Invalid time period format. Use format like '2h' or '24h'")
        
        # Collect commits
        commits = github_collector.get_commits_for_period(request.repository, hours)
        
        if not commits.commits:
            raise HTTPException(status_code=404, detail=f"No commits found for {request.repository} in the last {hours} hours")
        
        # Generate post
        response = post_generator.generate_post(request, commits)
        
        if not response.success:
            raise HTTPException(status_code=500, detail=response.error_message)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating post: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/collect-commits/{repository:path}")
@app.get("/collect-commits/{repository:path}")
async def collect_commits(repository: str, hours: int = 2):
    """Collect commits from a repository for the specified time period"""
    
    try:
        logger.info(f"Collecting commits from {repository} for last {hours} hours")
        
        commits = github_collector.get_commits_for_period(repository, hours)
        
        # Save to file - FIXED path separators
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{repository.replace('/', '_')}_{hours}h_{timestamp}.json"
        hourly_dir = os.path.join(settings.commit_data_dir, "hourly")
        os.makedirs(hourly_dir, exist_ok=True)
        filepath = os.path.join(hourly_dir, filename)
        
        github_collector.save_commits_to_file(commits, filepath)
        
        return {
            "repository": repository,
            "time_period": f"{hours}h",
            "commits_count": len(commits.commits),
            "start_time": commits.start_time,
            "end_time": commits.end_time,
            "file_path": filepath
        }
        
    except Exception as e:
        logger.error(f"Error collecting commits: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )