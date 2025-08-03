# LangChain AI Agents for File Organization

OCD integrates with LangChain to provide intelligent AI agents that can autonomously organize, rename, and structure your files based on natural language instructions.

## Overview

The AI agent system transforms OCD from a passive analysis tool into an active, intelligent file organization assistant that can:

- **Understand natural language commands**: "Organize my photos by year and event"
- **Make intelligent decisions**: Contextual understanding of file relationships
- **Execute complex workflows**: Multi-step organization with reasoning
- **Ensure safety**: Comprehensive validation and dry-run capabilities
- **Learn patterns**: Adapt to your preferences and existing structures

## Architecture

### Agent Types

#### 🗂️ **OrganizationAgent**
The primary agent for intelligent file and directory organization.

**Capabilities:**
- Analyzes directory structures and file patterns
- Creates logical folder hierarchies
- Organizes files by type, date, project, or custom criteria
- Handles naming conflicts intelligently
- Respects existing project structures
- Learns from user preferences

```python
from ocd.agents import OrganizationAgent

agent = OrganizationAgent(
    llm_provider=your_llm,
    organization_style="smart",  # smart, by_type, by_date, by_project
    safety_level=SafetyLevel.BALANCED
)

result = await agent.execute_task(
    "Organize my project files by type and create a logical structure",
    context={"directory_path": "/path/to/organize"}
)
```

#### 🏷️ **NamingAgent**
Specialized agent for generating meaningful, consistent file and folder names.

**Capabilities:**
- Analyzes file content to generate descriptive names
- Applies consistent naming conventions
- Handles name conflicts intelligently
- Supports various naming styles (snake_case, camelCase, etc.)
- Generates batch renaming suggestions

```python
from ocd.agents import NamingAgent

agent = NamingAgent(
    llm_provider=your_llm,
    naming_style="descriptive",
    case_style="snake_case"
)

result = await agent.execute_task(
    "Rename all files to follow descriptive naming conventions"
)
```

#### 🧹 **CleanupAgent**
Intelligent cleanup operations for disk space optimization.

**Capabilities:**
- Identifies and handles duplicate files
- Removes temporary and cache files safely
- Cleans up empty directories
- Optimizes disk space usage
- Handles old backups and logs

```python
from ocd.agents import CleanupAgent

agent = CleanupAgent(
    llm_provider=your_llm,
    preserve_recent=30,  # days
    aggressive_cleanup=False
)

result = await agent.execute_task(
    "Clean up temporary files and find duplicates"
)
```

## Getting Started

### Installation

Install OCD with agent support:

```bash
# Core + Agents
pip install ocd[agents]

# Everything (SLMs + Agents + All Providers)
pip install ocd[full]
```

### Basic Usage

#### CLI Commands

```bash
# Organize with intelligent agent
ocd organize ~/Downloads --strategy smart --dry-run

# Natural language organization
ocd organize ~/Photos --task "organize photos by date and event"

# Execute with specific provider
ocd organize ~/Documents --provider openai --execute --safety maximum

# Local-only processing for privacy
ocd organize ~/Private --mode local-only --provider local_slm
```

#### Python API

```python
import asyncio
from ocd.agents import OrganizationAgent
from ocd.core.types import SafetyLevel
from langchain_openai import ChatOpenAI

async def organize_files():
    # Initialize with your preferred LLM
    llm = ChatOpenAI(model="gpt-4")
    
    agent = OrganizationAgent(
        llm_provider=llm,
        safety_level=SafetyLevel.BALANCED,
        dry_run=True  # Preview first
    )
    
    await agent.initialize()
    
    result = await agent.execute_task(
        "Organize my project files into a logical structure with separate folders for docs, code, and assets",
        context={"directory_path": "/path/to/project"}
    )
    
    print(f"Success: {result['success']}")
    print(f"Operations: {result['operations_count']}")

asyncio.run(organize_files())
```

## Safety & Security

The agent system includes comprehensive safety mechanisms:

### Safety Levels

- **MINIMAL**: Basic validation, allows most operations
- **BALANCED**: Standard safety checks, prevents dangerous operations
- **MAXIMUM**: Strict validation, requires confirmation for all changes

### Safety Features

- **Dry Run Mode**: Preview all changes before execution
- **Operation Validation**: Check safety of each file operation
- **Backup System**: Automatic backups before destructive operations
- **Rollback Capability**: Undo operations if needed
- **Permission Checking**: Validate file system permissions
- **Path Validation**: Block operations on system directories

### Example with Safety

```python
agent = OrganizationAgent(
    llm_provider=llm,
    safety_level=SafetyLevel.MAXIMUM,
    dry_run=True,  # Always preview first
    max_operations=100,  # Limit operations per session
    require_confirmation=True  # Ask before executing
)

# Preview operations
result = await agent.execute_task("organize my files")

# Review and approve
if result['success'] and input("Execute? (y/n): ").lower() == 'y':
    agent.dry_run = False
    await agent.execute_task("organize my files")
```

## Provider Support

### Local Providers (Privacy-First)

**Local SLM Provider**: Uses our specialized Small Language Models
```bash
ocd organize ~/Documents --mode local-only --provider local_slm
```

**Ollama**: Local LLM via Ollama
```bash
ocd organize ~/Documents --provider ollama --model llama2
```

### Remote Providers

**OpenAI**: GPT models for maximum capability
```bash
export OPENAI_API_KEY=your_key
ocd organize ~/Documents --provider openai --model gpt-4
```

**Anthropic**: Claude models
```bash
export ANTHROPIC_API_KEY=your_key
ocd organize ~/Documents --provider anthropic --model claude-3-sonnet
```

### Hybrid Mode

Combine local privacy with remote intelligence:
```bash
ocd organize ~/Documents --mode hybrid --primary local_slm --fallback openai
```

## Natural Language Commands

The agents understand natural language instructions:

### Organization Examples

```bash
# By file type
ocd organize ~/Downloads --task "organize files by type into folders"

# By date
ocd organize ~/Photos --task "organize photos by year and month"

# By project
ocd organize ~/Code --task "organize code files by programming language and project"

# Complex instructions
ocd organize ~/Documents --task "create folders for work and personal docs, organize by year, and clean up duplicates"
```

### Naming Examples

```bash
# Descriptive naming
ocd organize ~/Files --task "rename files with descriptive names based on content"

# Convention application
ocd organize ~/Code --task "apply snake_case naming to all Python files"

# Batch operations
ocd organize ~/Photos --task "rename photos with date and location information"
```

### Cleanup Examples

```bash
# General cleanup
ocd organize ~/Downloads --task "clean up temporary files and remove duplicates"

# Specific cleanup
ocd organize ~/Projects --task "remove build artifacts and cache files, keep source code"

# Space optimization
ocd organize ~/Documents --task "find large files and suggest compression or removal"
```

## Advanced Features

### Multi-Agent Workflows

Combine multiple agents for complex tasks:

```python
async def comprehensive_organization(directory):
    # Step 1: Clean up first
    cleanup_agent = CleanupAgent(llm_provider=llm)
    await cleanup_agent.execute_task("remove temporary files and duplicates")
    
    # Step 2: Organize structure
    org_agent = OrganizationAgent(llm_provider=llm)
    await org_agent.execute_task("create logical folder structure")
    
    # Step 3: Apply naming conventions
    naming_agent = NamingAgent(llm_provider=llm)
    await naming_agent.execute_task("apply consistent naming conventions")
```

### Custom Tools

Extend agents with custom tools:

```python
from langchain.tools import Tool

def custom_file_analyzer(file_path: str) -> str:
    """Custom analysis logic"""
    return f"Analysis of {file_path}"

custom_tool = Tool(
    name="custom_analyzer",
    func=custom_file_analyzer,
    description="Perform custom file analysis"
)

agent = OrganizationAgent(llm_provider=llm)
agent.tools.append(custom_tool)
```

### Operation History & Rollback

```python
# Get operation history
history = agent.get_operation_history()
print(f"Performed {len(history)} operations")

# Rollback last 5 operations
await agent.rollback_operations(count=5)

# Rollback all operations in session
await agent.rollback_operations()
```

## Configuration

### Agent Configuration Files

Create `~/.ocd/agents.yaml`:

```yaml
organization:
  default_strategy: "smart"
  preserve_structure: true
  max_operations: 1000
  
naming:
  default_style: "descriptive"
  case_style: "snake_case"
  max_name_length: 100
  
cleanup:
  preserve_recent_days: 30
  aggressive_cleanup: false
  backup_before_delete: true

safety:
  default_level: "balanced"
  always_dry_run_first: true
  require_confirmation: true
```

### Provider Preferences

```yaml
providers:
  preferred_mode: "hybrid"
  local_provider: "local_slm"
  remote_provider: "openai"
  fallback_chain: ["local_slm", "ollama", "openai"]
  
  openai:
    model: "gpt-4"
    temperature: 0.7
    
  anthropic:
    model: "claude-3-sonnet-20240229"
    
  local_slm:
    models: ["classifier", "similarity"]
    quantization: "int8"
```

## Examples & Use Cases

### Personal File Organization

```bash
# Organize personal files
ocd organize ~/Desktop --task "organize personal files into folders by type and importance"

# Photo organization
ocd organize ~/Pictures --task "organize photos by year, month, and event, rename with dates"

# Document management
ocd organize ~/Documents --task "create folders for work, personal, and archive, organize by year"
```

### Developer Workflows

```bash
# Project organization
ocd organize ~/Code --task "organize code projects by language, create standard folder structures"

# Cleanup development files
ocd organize ~/Projects --task "remove build files, organize source code, clean up dependencies"

# Documentation organization
ocd organize ~/Docs --task "organize documentation by project, convert naming to markdown standards"
```

### Business Use Cases

```bash
# Client file organization
ocd organize ~/ClientFiles --task "organize files by client name and project, apply professional naming"

# Report organization
ocd organize ~/Reports --task "organize reports by quarter and department, standardize naming"

# Asset management
ocd organize ~/Assets --task "organize creative assets by project and type, optimize file names"
```

## Troubleshooting

### Common Issues

**Agent not responding:**
```bash
# Check LLM provider connectivity
ocd configure --test --provider openai

# Use local provider as fallback
ocd organize ~/files --mode local-only
```

**Operations blocked by safety:**
```bash
# Lower safety level
ocd organize ~/files --safety minimal

# Use dry-run to understand what's blocked
ocd organize ~/files --dry-run --verbose
```

**Performance issues:**
```bash
# Use local providers for speed
ocd organize ~/files --provider local_slm

# Limit operation count
ocd organize ~/files --max-operations 50
```

### Debug Mode

```bash
# Enable verbose logging
export OCD_LOG_LEVEL=DEBUG
ocd organize ~/files --task "organize files" --dry-run
```

## Contributing

The agent system is designed to be extensible:

1. **Custom Agents**: Inherit from `BaseAgent`
2. **Custom Tools**: Create LangChain-compatible tools
3. **Custom Providers**: Implement LLM provider wrappers
4. **Custom Strategies**: Add organization strategies

See `examples/custom_agent.py` for implementation examples.

## Limitations

- **LLM Dependencies**: Requires LangChain and LLM providers
- **Performance**: Complex operations may be slower than direct SLM calls  
- **Cost**: Remote LLM usage incurs API costs
- **Internet**: Remote providers require internet connectivity
- **Context Limits**: Large directories may hit LLM context limits

## Roadmap

- **Multi-modal Analysis**: Support for image and document content
- **Learning System**: Improve from user feedback and corrections
- **Collaboration**: Multi-user file organization workflows
- **Integration**: Support for cloud storage providers
- **Mobile Support**: React Native agents for mobile file management