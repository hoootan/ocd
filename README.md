# OCD - Organized Content Directory

A cross-platform Python application that integrates both offline local SLMs (Small Language Models) and online LLMs to analyze directory structures and execute scripts based on intelligent prompts.

## Features

- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Multiple AI Providers**: Support for local SLMs, local LLMs, and remote APIs
- **Secure Credential Management**: OS-native credential storage with encrypted fallback
- **Intelligent Directory Analysis**: Comprehensive file structure and content analysis
- **Template-Based Prompts**: Jinja2-powered prompt templates for consistency
- **Safe Script Execution**: Sandboxed execution with safety checks
- **Zero-Friction Installation**: Single-script installation with dependency management

## Quick Start

### Installation

1. **Clone and Install**:
   ```bash
   git clone <repository-url>
   cd OCD
   python install.py --dev
   ```

2. **Activate Environment**:
   ```bash
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Verify Installation**:
   ```bash
   ocd --help
   ```

### Basic Usage

1. **Analyze a Directory**:
   ```bash
   ocd analyze /path/to/directory --type structure --type metadata
   ```

2. **Configure AI Providers**:
   ```bash
   ocd configure
   ```

3. **Execute AI-Powered Tasks**:
   ```bash
   ocd execute /path/to/directory "Organize files by type"
   ```

## Architecture

### Core Design Patterns

- **Strategy Pattern**: For different AI providers (OpenAI, Anthropic, Ollama, etc.)
- **Factory Pattern**: For creating AI service instances
- **Observer Pattern**: For progress tracking and updates
- **Command Pattern**: For undoable operations
- **Template Pattern**: For prompt management

### Components

- **AI Providers**: Pluggable AI service implementations
- **Directory Analyzers**: Content analysis and pattern extraction
- **Prompt Engine**: Jinja2-based template system
- **Credential Manager**: Secure cross-platform credential storage
- **Configuration System**: Hierarchical configuration management
- **CLI Interface**: Modern CLI with rich output formatting

## AI Provider Support

### Local SLMs (Small Language Models)
- File classification
- Content extraction
- Pattern recognition
- Local processing for privacy

### Remote APIs
- OpenAI GPT models
- Anthropic Claude
- Google Gemini
- Custom endpoints

### Configuration
```bash
# Set up OpenAI
ocd configure openai

# Set up Anthropic
ocd configure anthropic

# List providers
ocd configure --list
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

## Examples

### Directory Analysis
```bash
# Basic structure analysis
ocd analyze ~/Documents --type structure

# Comprehensive analysis with content
ocd analyze ~/Projects --type structure --type content --type metadata --content

# Export results
ocd analyze ~/Code --format json --output analysis.json
```

### Template Management
```bash
# List templates
ocd templates list

# Create template
ocd templates create my_template --file template.j2 --description "Custom analysis"

# Export templates
ocd templates export --file my_templates.json
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run quality checks
6. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

- Documentation: https://ocd.readthedocs.io/
- Issues: https://github.com/ocd-team/ocd/issues
- Discussions: https://github.com/ocd-team/ocd/discussions