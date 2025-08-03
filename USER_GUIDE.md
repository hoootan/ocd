# OCD User Guide 🚀

**OCD (Organized Content Directory)** is an intelligent file and folder organization system that uses both offline and online AI to automatically categorize, rename, and structure your files based on their content, metadata, and your preferences.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [What OCD Does](#what-ocd-does)
- [Installation](#installation)
- [Basic Commands](#basic-commands)
- [Real-World Examples](#real-world-examples)
- [Safety Features](#safety-features)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

## 🚀 Quick Start

**Step 1:** Install OCD
```bash
# Download and run the installer
python install.py
```

**Step 2:** Analyze a directory with offline AI
```bash
# Activate the environment and analyze with local SLMs  
source .venv/bin/activate
ocd analyze ~/Desktop --mode local-only
```

**Step 3:** Organize files intelligently
```bash
# Let OCD organize your files automatically
ocd organize ~/Downloads --task "organize files by type" --dry-run
```

## 🤔 What OCD Does

Think of OCD as your **intelligent file organization assistant**. It can:

- **🤖 Organize automatically** using specialized offline AI models
- **🧠 Understand context** by analyzing file content and relationships  
- **📁 Create structure** by categorizing files intelligently by type, date, or project
- **🔍 Find duplicates** and handle them intelligently
- **🛡️ Keep you safe** with dry-run mode and comprehensive validation
- **🔒 Protect privacy** with complete local processing option
- **🌐 Work anywhere** - supports Windows, macOS, and Linux

### Real-World Use Cases

- **Messy Downloads**: "Organize my chaotic Downloads folder"
- **Photo Organization**: "Sort my photos by year and event"  
- **Document Management**: "Organize documents by type and importance"
- **Code Project Cleanup**: "Structure my development projects"
- **Privacy-First Processing**: "Organize sensitive files without cloud AI"
- **Duplicate Management**: "Find and handle duplicate files intelligently"

## 📦 Installation

### Automatic Installation (Recommended)

1. **Download** the OCD installer
2. **Run** the installer:
   ```bash
   python install.py
   ```
3. **Activate** the environment:
   ```bash
   source .venv/bin/activate  # macOS/Linux
   # or
   .venv\Scripts\activate     # Windows
   ```

The installer automatically:
- ✅ Creates a virtual environment
- ✅ Installs all dependencies
- ✅ Sets up the OCD package
- ✅ Handles platform-specific requirements

### Verify Installation

```bash
ocd --version
```

You should see: `OCD version 0.1.0`

## 🎯 Basic Commands

### 1. Analyze Directories with Offline AI

**Basic Analysis (Privacy-First):**
```bash
ocd analyze ~/Documents --mode local-only
```

**Advanced Analysis:**
```bash
# Multiple analysis types with local SLMs
ocd analyze ~/Projects --type structure --type content --mode local-only

# Save detailed analysis results
ocd analyze ~/Code --output analysis_report.json --format json --mode local-only

# Quick structure overview
ocd analyze ~/Desktop --type structure --provider local_slm
```

### 2. Intelligent File Organization

**Safe Organization (Always Start Here):**
```bash
# Always test with --dry-run first
ocd organize ~/Downloads --strategy smart --dry-run

# Then execute the actual organization
ocd organize ~/Downloads --strategy smart --execute
```

**Natural Language Commands:**
```bash
# Use natural language to describe what you want
ocd organize ~/Desktop --task "organize files by type and clean up duplicates" --dry-run

# Privacy-focused organization
ocd organize ~/Photos --mode local-only --task "organize photos by date" --dry-run

# Professional document organization
ocd organize ~/Documents --task "create folders by document type and importance" --execute
```

**Organization Strategies:**
```bash
# Organize by file type (documents, images, code, etc.)
ocd organize ~/folder --strategy by_type --dry-run

# Organize by creation/modification date
ocd organize ~/folder --strategy by_date --dry-run

# Smart organization using AI analysis
ocd organize ~/folder --strategy smart --dry-run
```

### 3. Configure AI Providers

```bash
# List available providers
ocd configure --list

# Set up OpenAI
ocd configure openai

# Test connection
ocd configure openai --test
```

### 4. Manage Templates

```bash
# List available templates
ocd templates list

# Create a new template
ocd templates create my_template --file template.txt --description "My custom template"

# Export templates
ocd templates export --file my_templates.json
```

## 🌟 Real-World Examples

### Example 1: Analyzing a New Project

**Scenario:** You just cloned a GitHub repository and want to understand it.

```bash
# Step 1: Basic analysis
ocd analyze ./new-project

# Step 2: Detailed analysis with output
ocd analyze ./new-project \
    --type structure,content,dependency \
    --output project_analysis.json \
    --format json

# Step 3: Get AI insights
ocd execute ./new-project \
    "Create a README summary of this project's structure and purpose" \
    --dry-run
```

**What you get:**
- 📁 Directory structure overview
- 📊 File type distribution
- 🔗 Dependencies and imports
- 💡 AI-generated insights

### Example 2: Organizing Downloaded Files

**Scenario:** Your Downloads folder is a mess, and you want to organize it.

```bash
# Step 1: Analyze the chaos
ocd analyze ~/Downloads --type structure,metadata

# Step 2: Create organization script (safely)
ocd execute ~/Downloads \
    "organize files by type into subdirectories" \
    --dry-run \
    --language bash

# Step 3: Review and run
# (Review the generated script first!)
ocd execute ~/Downloads \
    "organize files by type into subdirectories" \
    --language bash
```

**What happens:**
- 🔍 OCD analyzes file types and patterns
- 📝 Generates safe organization scripts
- 🛡️ Validates operations for safety
- ✅ Executes with full logging

### Example 3: Code Project Health Check

**Scenario:** You want to check if your Python project is well-structured.

```bash
# Comprehensive project analysis
ocd analyze ./my-python-project \
    --type structure,content,dependency \
    --include-content \
    --output health_check.yaml \
    --format yaml

# Generate improvement suggestions
ocd execute ./my-python-project \
    "analyze code quality and suggest improvements" \
    --language python \
    --dry-run
```

**Results include:**
- 🏗️ Project structure analysis
- 📦 Dependency mapping
- 🔍 Code pattern detection
- 💡 Improvement recommendations

### Example 4: Safe File Processing

**Scenario:** You need to process 1000+ image files safely.

```bash
# Step 1: Analyze the images
ocd analyze ./photo-collection --type metadata

# Step 2: Create processing script with safety checks
ocd execute ./photo-collection \
    "resize all JPEG images to 1920x1080 while preserving originals" \
    --dry-run \
    --language bash

# Step 3: Execute with monitoring
ocd execute ./photo-collection \
    "resize all JPEG images to 1920x1080 while preserving originals" \
    --language bash \
    --output processing_log.txt
```

**Safety features active:**
- 🛡️ Validates no destructive operations
- 📊 Resource monitoring (disk space, memory)
- 🏃‍♂️ Sandboxed execution
- 📝 Complete operation logging

## 🛡️ Safety Features

OCD prioritizes your safety with multiple protection layers:

### 1. Script Validation

**Dangerous commands are automatically detected:**
```bash
# ❌ This would be blocked:
# rm -rf /
# format C:
# chmod 777 /etc
```

**Safety levels:**
- **Permissive** - Basic validation
- **Balanced** - Standard protection (default)
- **Strict** - High security, blocks critical operations
- **Paranoid** - Maximum security, blocks high-risk operations

### 2. Sandboxed Execution

Every script runs in an isolated environment:
- 🏠 Separate temporary directory
- 🔒 Limited file system access
- ⏱️ Execution time limits
- 💾 Memory and disk usage limits

### 3. Dry Run Mode

**Always test first:**
```bash
# See what would happen without actually doing it
ocd execute . "any command" --dry-run
```

### 4. Resource Monitoring

Real-time tracking of:
- ⏱️ Execution time
- 💾 Memory usage
- 💿 Disk space usage
- 📁 Files created/modified

## ⚙️ Configuration

### Basic Configuration

```bash
# View current configuration
ocd configure --list

# Set default AI provider
ocd configure --set-default openai
```

### Advanced Configuration

Create a configuration file at `~/.ocd/config.toml`:

```toml
[general]
max_files_analysis = 1000
max_file_size = 10485760  # 10MB
default_temperature = 0.7

[providers]
default_provider = "openai"

[providers.openai]
model = "gpt-4"
api_key_env = "OPENAI_API_KEY"

[safety]
level = "balanced"
allow_network = false
allow_system_commands = false

[execution]
default_timeout = 300.0  # 5 minutes
use_sandbox = true
```

### API Key Setup

For AI providers, you'll need API keys:

```bash
# Set environment variables
export OPENAI_API_KEY="your-key-here"
export ANTHROPIC_API_KEY="your-key-here"

# Or use the configuration wizard
ocd configure openai
```

## 🔧 Troubleshooting

### Common Issues

**1. "Command not found: ocd"**
```bash
# Make sure you activated the virtual environment
source .venv/bin/activate
```

**2. "Permission denied" errors**
```bash
# Check file permissions
ls -la /path/to/file

# Run with appropriate permissions
# (OCD will warn you about dangerous operations)
```

**3. "API key not found"**
```bash
# Set your API key
export OPENAI_API_KEY="your-key-here"

# Or configure through OCD
ocd configure openai
```

**4. "Execution timed out"**
```bash
# Increase timeout for large operations
ocd execute . "big task" --timeout 600  # 10 minutes
```

### Getting Help

```bash
# General help
ocd --help

# Command-specific help
ocd analyze --help
ocd execute --help
ocd configure --help

# Check version
ocd --version

# Verbose output for debugging
ocd analyze . --verbose
```

### Safety Warnings

If you see safety warnings, **pay attention**:

```bash
⚠️  Safety violations detected:
  • Critical: rm -rf / detected
  • High: sudo commands found
  
❌ Execution blocked in strict mode
```

**What to do:**
1. **Review** the generated script carefully
2. **Understand** what each command does
3. **Modify** or **reject** dangerous operations
4. **Use** `--dry-run` to test safely

## 📚 Tips for Success

### 1. Start Small
```bash
# Begin with analysis
ocd analyze . 

# Then try simple tasks
ocd execute . "echo hello world" --dry-run
```

### 2. Use Dry Run
```bash
# ALWAYS test first
ocd execute . "any command" --dry-run
```

### 3. Check Output
```bash
# Save output for review
ocd execute . "command" --output results.txt
```

### 4. Monitor Resources
```bash
# For large operations, watch the logs
ocd execute . "big task" --verbose
```

### 5. Understand Safety
- 🔴 **Critical** violations = Dangerous to your system
- 🟠 **High** violations = Potentially risky operations  
- 🟡 **Medium** violations = Operations requiring attention
- 🔵 **Low** violations = Minor concerns

## 🎉 You're Ready!

OCD is designed to be **powerful yet safe**. Start with simple analysis tasks, always use `--dry-run` for new operations, and pay attention to safety warnings.

**Remember:**
- 🔍 **Analyze first** to understand your data
- 🧪 **Test with --dry-run** before executing
- 🛡️ **Trust the safety system** - it's protecting you
- 📝 **Review generated scripts** before running them
- 🆘 **Start small** and build confidence

Happy organizing! 🚀

---

**Need more help?** 
- Run `ocd --help` for command details
- Check the configuration at `~/.ocd/config.toml`
- Use `--verbose` for detailed output
- Use `--dry-run` when in doubt