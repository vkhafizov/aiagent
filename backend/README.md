# AI GitHub Explainer

An intelligent system that transforms GitHub repository changes into engaging, understandable social media posts. This tool automatically collects commits every hour, analyzes them, and generates beautiful HTML posts explaining technical changes in accessible language for non-technical audiences.

## 🌟 Features

- **🤖 Fully Automatic**: AI analyzes commits and chooses the right template automatically
- **⚡ Ready to Use**: Just add your API keys and run - no configuration needed!
- **🕐 Hourly Collection**: Automatically collects commits every hour
- **🎨 Smart Templates**: AI picks between 5 templates based on commit content
- **📱 Social Media Ready**: Generates engaging posts for non-technical audiences
- **📊 Rich Content**: Charts, progress bars, code snippets, all automatic
- **⏰ Flexible Periods**: 2-hour and 24-hour post generation
- **🔄 Zero Maintenance**: Set it and forget it!

## 🏗️ Architecture

```
ai-github-explainer/
├── app/
│   ├── core/                 # Core business logic
│   │   ├── github_collector.py   # GitHub API integration
│   │   ├── claude_client.py       # Claude AI integration
│   │   ├── post_generator.py      # Post generation orchestration
│   │   └── config.py             # Configuration management
│   ├── models/               # Data models
│   │   ├── commit.py             # Commit data structures
│   │   └── post.py               # Post data structures
│   ├── templates/            # HTML templates
│   │   ├── template_feature.html
│   │   ├── template_bugfix.html
│   │   ├── template_security.html
│   │   ├── template_performance.html
│   │   └── template_general.html
│   ├── prompts/              # AI prompts
│   │   ├── base_prompt.txt
│   │   ├── feature_prompt.txt
│   │   ├── bugfix_prompt.txt
│   │   ├── security_prompt.txt
│   │   └── performance_prompt.txt
│   ├── utils/                # Utility functions
│   │   ├── template_selector.py   # Template selection logic
│   │   ├── html_generator.py      # HTML generation
│   │   ├── chart_generator.py     # Chart generation
│   │   └── data_processor.py      # Data analysis
│   └── main.py               # FastAPI application
├── data/                     # Data storage
│   ├── commits/              # Stored commit data
│   └── posts/                # Generated posts
├── logs/                     # Application logs
├── scheduler.py              # Automated scheduling
├── docker-compose.yml        # Docker deployment
├── Dockerfile               # Container definition
└── requirements.txt         # Python dependencies
```

## 🚀 Quick Start (3 Steps!)

### 1. Clone & Install
```bash
git clone https://github.com/your-org/ai-github-explainer.git
cd ai-github-explainer
pip install -r requirements.txt
```

### 2. Add Your API Keys
```bash
cp .env.example .env
# Edit .env and add:
# GITHUB_TOKEN=your_token_here
# ANTHROPIC_API_KEY=your_claude_key_here  
# GITHUB_REPOS=owner/repo1,owner/repo2
```

### 3. Run!
```bash
python run.py
```

**That's it!** The AI will automatically:
- ✅ Analyze your commits
- ✅ Choose the right template (Feature/Bug/Security/Performance/General)  
- ✅ Generate engaging posts
- ✅ Save beautiful HTML files
- ✅ Run hourly collection

Visit `http://localhost:8000/docs` to see all endpoints!

### Example: Generate a Post
```bash
curl -X POST "http://localhost:8000/generate-post" \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "facebook/react",
    "time_period": "2h"
  }'
```

The AI will automatically:
1. 🔍 Analyze the last 2 hours of commits
2. 🧠 Determine if it's mostly features, bugs, security, performance, or mixed
3. 🎨 Choose the perfect template
4. ✍️ Write an engaging explanation
5. 📄 Generate a beautiful HTML post

**No configuration, no template selection, no prompts to write - just pure automation!**

## 📖 Usage

### Manual Post Generation

Generate a post for a specific repository:

```bash
curl -X POST "http://localhost:8000/generate-post" \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "facebook/react",
    "time_period": "2h",
    "target_audience": "general"
  }'
```

### Batch Post Generation

Generate posts for all configured repositories:

```bash
curl -X POST "http://localhost:8000/generate-posts-batch" \
  -H "Content-Type: application/json" \
  -d '{
    "time_periods": ["2h", "24h"],
    "target_audience": "general"
  }'
```

### View Generated Posts

List posts:
```bash
curl http://localhost:8000/posts/2h
```

View a specific post:
```
http://localhost:8000/posts/2h/react_2h_20241210_143022.html
```

### Collect Commits Manually

```bash
curl -X POST "http://localhost:8000/collect-commits/facebook/react?hours=24"
```

## 🎨 Post Templates

The system includes 5 specialized templates that are automatically selected based on commit analysis:

### 1. Feature Template
- **Use Case**: New features, enhancements, major additions
- **Design**: Vibrant gradient banners, feature highlight cards
- **Focus**: User benefits, new capabilities

### 2. Bug Fix Template
- **Use Case**: Bug fixes, improvements, reliability updates
- **Design**: Green success theme, improvement checklists
- **Focus**: Quality improvements, reliability metrics

### 3. Security Template
- **Use Case**: Security updates, vulnerability fixes
- **Design**: Professional purple theme, protection indicators
- **Focus**: Security posture, compliance badges

### 4. Performance Template
- **Use Case**: Performance optimizations, speed improvements
- **Design**: Orange energy theme, speed metrics
- **Focus**: Performance gains, efficiency improvements

### 5. General Template
- **Use Case**: Mixed changes, general updates
- **Design**: Blue professional theme, balanced layout
- **Focus**: Overall development progress, activity timeline

## 🔧 Configuration

### Core Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `GITHUB_TOKEN` | GitHub personal access token | Required |
| `GITHUB_REPOS` | Comma-separated list of repositories | Required |
| `ANTHROPIC_API_KEY` | Claude AI API key | Required |
| `POST_GENERATION_INTERVAL` | Seconds between post generations | 3600 |
| `MAX_COMMITS_PER_HOUR` | Rate limiting for commit collection | 100 |

### Template Selection

The system automatically selects templates based on:
- **Commit message keywords** (e.g., "feat:", "fix:", "security:")
- **File patterns** (e.g., test files, documentation)
- **Change magnitude** (lines added/removed)
- **Security indicators** (authentication, encryption keywords)
- **Performance indicators** (optimization, caching keywords)

You can override automatic selection:

```python
{
  "repository": "owner/repo",
  "time_period": "2h",
  "force_template": "template_security"
}
```

## 📊 Monitoring & Analytics

### Health Monitoring

```bash
# Check system health
curl http://localhost:8000/health

# View analytics summary
curl http://localhost:8000/analytics/summary

# Repository-specific analytics
curl http://localhost:8000/analytics/repository/owner/repo
```

### Logs

Application logs are stored in the `logs/` directory:
- `app.log` - Main application logs
- `scheduler.log` - Scheduler and automation logs

### Metrics

The system tracks:
- Post generation success rates
- Commit collection statistics
- API rate limit usage
- Template selection effectiveness

## 🔧 Development

### Project Structure

- **`app/core/`**: Business logic and external integrations
- **`app/models/`**: Data models and schemas
- **`app/templates/`**: Jinja2 HTML templates
- **`app/prompts/`**: AI prompt templates
- **`app/utils/`**: Utility functions and helpers

### Adding New Templates

1. Create HTML template in `app/templates/`
2. Add corresponding prompt in `app/prompts/`
3. Update template selection logic in `app/utils/template_selector.py`
4. Add template enum in `app/models/post.py`

### Extending Functionality

The system is designed for easy extension:

- **New Output Formats**: Extend `HTMLGenerator` class
- **Additional AI Providers**: Implement new client in `app/core/`
- **Custom Analytics**: Add processors in `app/utils/data_processor.py`
- **New Commit Sources**: Extend `GitHubCollector` or create new collectors

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt

# Format code (optional)
pip install black flake8
black .
flake8 .
```

## 📝 API Documentation

Full API documentation is available at `/docs` when running the application.

### Key Endpoints

- `GET /health` - System health check
- `POST /generate-post` - Generate single post
- `POST /generate-posts-batch` - Generate multiple posts
- `POST /collect-commits/{repository}` - Collect commits
- `GET /posts/{time_period}` - List posts
- `GET /posts/{time_period}/{filename}` - View specific post

## 🔒 Security

- Store sensitive tokens in environment variables
- Use GitHub fine-grained personal access tokens
- Implement rate limiting for API endpoints
- Regular security updates for dependencies
- Log security-relevant events

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Anthropic Claude](https://www.anthropic.com/) for AI-powered explanations
- [GitHub API](https://docs.github.com/en/rest) for commit data
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [Jinja2](https://jinja.palletsprojects.com/) for templating

## 📞 Support

For support, please:
1. Check the [documentation](README.md)
2. Search [existing issues](https://github.com/your-org/ai-github-explainer/issues)
3. Create a [new issue](https://github.com/your-org/ai-github-explainer/issues/new)

---

Made with ❤️ for the open source community