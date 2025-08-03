# OCD - Organized Content Directory 🤖

**OCD (Organized Content Directory)** is an intelligent file and folder organization system that leverages both local and remote AI models to automatically categorize, rename, and structure files based on their content, metadata, and user preferences.

## ✨ Features

### 🧠 **AI-Powered Intelligence**
- **Offline SLMs**: Specialized Small Language Models for classification, similarity detection, and content analysis
- **LangChain Agents**: Autonomous file organization with natural language commands
- **Multiple AI Providers**: OpenAI, Anthropic, Ollama, and local models
- **Privacy-First**: Complete local processing option for sensitive files

### 🗂️ **Smart File Organization**
- **Intelligent Categorization**: Automatically organize files by type, date, project, or custom criteria
- **Pattern Recognition**: Detects naming conventions and file relationships
- **Duplicate Detection**: Finds and handles duplicate files intelligently
- **Natural Language Commands**: "Organize my photos by year and event"

### 🛡️ **Safety & Security**
- **Dry-Run Mode**: Preview all changes before execution
- **Safe Operations**: Comprehensive validation and rollback capabilities
- **Local Processing**: Keep sensitive files on your machine
- **Cross-Platform**: Works on Windows, macOS, and Linux

## 🚀 Quick Start

### Installation

```bash
# Clone and install with single command
git clone https://github.com/hoootan/ocd.git
cd ocd
python install.py  # Automatically installs all dependencies
```

### Basic Usage

```bash
# 1. Activate environment
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# 2. Analyze directories with offline AI
ocd analyze ~/Desktop --mode local-only

# 3. Organize files intelligently
ocd organize ~/Downloads --task "organize files by type" --dry-run

# 4. Execute with full AI agents (requires API keys)
ocd organize ~/Documents --provider openai --execute
```

### Real-World Examples

```bash
# Organize chaotic downloads folder
ocd organize ~/Downloads --strategy smart --dry-run

# Local-only photo organization for privacy
ocd organize ~/Photos --mode local-only --task "organize by date"

# Natural language file management
ocd organize ~/Desktop --task "make my desktop beautiful and organized"

# Professional document organization
ocd organize ~/Documents --strategy by_type --execute
```

## 🏗️ Architecture

### Specialized AI Models

#### 🔬 **Offline Small Language Models (SLMs)**
- **FileClassifierSLM**: Intelligent file type and category detection
- **SimilarityDetectorSLM**: Duplicate and similar file identification  
- **Resource Management**: Lazy loading, quantization (INT8/INT4), memory optimization
- **Privacy-First**: Complete local processing without internet requirements

#### 🤖 **LangChain AI Agents**
- **OrganizationAgent**: Autonomous file and directory organization
- **NamingAgent**: Intelligent file renaming with consistent conventions
- **CleanupAgent**: Smart cleanup of temporary files and duplicates
- **Natural Language**: Process commands like "organize my photos by year"

#### 🌐 **Remote AI Providers**
- **OpenAI**: GPT-4, GPT-3.5 for maximum intelligence
- **Anthropic**: Claude models for advanced reasoning
- **Ollama**: Local LLM serving for privacy + power
- **Hybrid Mode**: Combine local privacy with remote intelligence

### Core Components

```
src/ocd/
├── agents/         # LangChain-based autonomous agents
├── models/         # Specialized SLM implementations  
├── tools/          # Safe file operation tools
├── providers/      # AI provider implementations
├── analyzers/      # Directory and content analysis
├── core/           # Core types and utilities
└── cli.py          # Modern command-line interface
```

### AI Provider Modes

```bash
# Local-only processing (complete privacy)
ocd organize ~/folder --mode local-only

# Remote-only processing (maximum intelligence)  
ocd organize ~/folder --provider openai

# Hybrid processing (best of both worlds)
ocd organize ~/folder --mode hybrid --primary local_slm --fallback openai
```

## Development

### Project Structure
```
src/ocd/
├── core/           # Core types and exceptions
├── providers/      # AI provider implementations
├── analyzers/      # Directory and content analysis
├── credentials/    # Secure credential management
├── prompts/        # Template engine and management
├── config/         # Configuration system
└── cli.py          # Command-line interface
```

### Running Tests
```bash
pytest
pytest --cov=src/ocd --cov-report=html
```

### Code Quality
```bash
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
```

## Configuration

### Environment Variables
```bash
export OCD_DEFAULT_PROVIDER=openai
export OCD_MAX_FILES_ANALYSIS=5000
export OCD_LOG_LEVEL=DEBUG
```

### Configuration Files
- Global: `~/.ocd/config.toml`
- Project: `./ocd.toml`
- Custom: `--config path/to/config.toml`

### Example Configuration
```toml
default_provider = "openai"
max_files_analysis = 10000
log_level = "INFO"

[providers.openai]
name = "openai"
provider_type = "remote_api"
model_name = "gpt-4"
api_key_env_var = "OPENAI_API_KEY"
max_tokens = 2000
temperature = 0.7
```

## Security

- **Local Processing**: Option for complete local processing
- **Credential Security**: OS-native credential stores with encryption
- **Safe Execution**: Sandboxed script execution with permission controls
- **Privacy Options**: Local-only processing for sensitive files

## 📋 Examples

### Directory Analysis with Offline AI
```bash
# Privacy-first analysis using local SLMs
ocd analyze ~/Documents --mode local-only

# Comprehensive analysis with multiple types
ocd analyze ~/Projects --type structure --type content --provider local_slm

# Export detailed analysis results
ocd analyze ~/Code --format json --output analysis.json --mode local-only
```

### Intelligent File Organization
```bash
# Smart organization with AI decision-making
ocd organize ~/Downloads --strategy smart --dry-run

# Natural language commands
ocd organize ~/Desktop --task "organize files by project and clean up duplicates"

# Date-based photo organization
ocd organize ~/Pictures --strategy by_date --execute

# Type-based document organization  
ocd organize ~/Documents --strategy by_type --mode local-only
```

### Advanced AI Agent Usage
```bash
# Multi-step organization with cleanup
ocd organize ~/Desktop --task "create folders by file type, remove duplicates, and apply consistent naming"

# Project-specific organization
ocd organize ~/Code --task "organize code files by language and create standard project structures"

# Privacy-focused processing
ocd organize ~/Private --mode local-only --task "organize sensitive files locally"
```

### Real-World Workflows
```bash
# Clean up messy downloads
ocd organize ~/Downloads --task "organize by type, remove temp files, group similar files" --dry-run

# Prepare files for backup
ocd organize ~/Important --strategy by_date --task "organize for archival" --execute

# Developer workspace cleanup
ocd organize ~/Projects --task "organize projects by language, clean build files" --provider local_slm
```

## 🎯 What's Working Right Now

### ✅ **Fully Functional Features**
- **Offline SLM Analysis**: Complete file analysis using specialized local AI models
- **Smart File Organization**: Automatic categorization by type, date, and content
- **Pattern Recognition**: Detects naming conventions and file relationships
- **Duplicate Detection**: Finds similar and duplicate files using AI
- **Safe Operations**: Comprehensive dry-run mode and validation
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Privacy-First**: Complete local processing option

### ✅ **Current Capabilities**
- **45+ file types** automatically recognized and organized
- **8+ organization strategies** (by type, date, project, smart, etc.)
- **Natural language commands** processed and executed
- **Resource management** with automatic model loading/unloading
- **Comprehensive logging** and error handling
- **Fallback systems** ensure reliability

### 🔧 **Installation Status**
- **Single-command setup**: `python install.py` handles everything
- **All dependencies included**: SLMs, LangChain, agents, tools
- **Automatic environment setup**: Virtual environment and package installation
- **Cross-platform compatibility**: Tested on macOS, ready for Windows/Linux

### 🚀 **Performance Highlights**
- **Fast analysis**: Processes 45+ files in under 3 seconds
- **Memory efficient**: Automatic model loading/unloading
- **Privacy focused**: No data leaves your machine in local-only mode
- **Safe by default**: Dry-run mode prevents accidental changes

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run quality checks: `black src/ && flake8 src/ && mypy src/`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support & Community

- **Documentation**: [README.md](README.md) and [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/hoootan/ocd/issues)
- **Discussions**: [GitHub Discussions](https://github.com/hoootan/ocd/discussions)
- **Security**: See [SECURITY.md](SECURITY.md) for security policy
- **Changelog**: See [CHANGELOG.md](CHANGELOG.md) for version history

## ⭐ Star History

If you find OCD useful, please consider giving it a star on GitHub! ⭐

[![Star History Chart](https://api.star-history.com/svg?repos=hoootan/ocd&type=Date)](https://star-history.com/#hoootan/ocd&Date)