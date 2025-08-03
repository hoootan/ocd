"""
LangChain Agent Demo
===================

Demonstrates the complete LangChain agent integration for intelligent
file organization using natural language commands.
"""

import asyncio
from pathlib import Path
import tempfile
import shutil

async def demo_organization_agent():
    """Demo the OrganizationAgent capabilities."""
    print("🤖 OCD LangChain Agent Demo")
    print("=" * 50)
    
    # Create a demo directory structure
    with tempfile.TemporaryDirectory() as temp_dir:
        demo_dir = Path(temp_dir) / "demo_files"
        await create_demo_files(demo_dir)
        
        print(f"📁 Demo directory created: {demo_dir}")
        print(f"📊 Files created: {count_files(demo_dir)}")
        
        # Import the organization agent
        try:
            from ocd.agents import OrganizationAgent
            from ocd.core.types import SafetyLevel
            
            # Create a mock LLM for demo
            mock_llm = create_demo_llm()
            
            # Initialize the agent
            agent = OrganizationAgent(
                llm_provider=mock_llm,
                safety_level=SafetyLevel.BALANCED,
                organization_style="smart",
                dry_run=True,  # Safe demo mode
                preserve_structure=True
            )
            
            await agent.initialize()
            print("✅ Agent initialized successfully")
            
            # Demo various organization tasks
            tasks = [
                "Organize all files by type into appropriate folders",
                "Find and handle any duplicate files",
                "Clean up temporary files and empty directories",
                "Apply consistent naming conventions to all files",
                "Create a logical project structure for code files"
            ]
            
            for i, task in enumerate(tasks, 1):
                print(f"\n🎯 Task {i}: {task}")
                
                context = {
                    "directory_path": str(demo_dir),
                    "preserve_existing": True,
                    "safety_first": True
                }
                
                result = await agent.execute_task(task, context)
                
                if result["success"]:
                    print(f"✅ {result['message']}")
                    if result.get('operations_count', 0) > 0:
                        print(f"   📋 Operations planned: {result['operations_count']}")
                else:
                    print(f"❌ Failed: {result.get('message', 'Unknown error')}")
                
                # Simulate processing time
                await asyncio.sleep(0.5)
            
            # Show operation history
            history = agent.get_operation_history()
            print(f"\n📊 Total operations tracked: {len(history)}")
            
            # Demo cleanup
            print(f"\n🧹 Demo complete. Files would remain organized in: {demo_dir}")
            print("   (In actual use, files would be moved/renamed as planned)")
            
        except ImportError as e:
            print(f"❌ LangChain not installed: {e}")
            print("💡 Install with: pip install ocd[agents]")
        except Exception as e:
            print(f"❌ Demo failed: {e}")


async def create_demo_files(demo_dir: Path):
    """Create a sample directory structure for demonstration."""
    demo_dir.mkdir(parents=True, exist_ok=True)
    
    # Sample files by category
    files_to_create = {
        "documents": [
            "project_spec.pdf", "meeting_notes.docx", "readme.txt", 
            "requirements.md", "design_doc.pdf"
        ],
        "images": [
            "logo.png", "screenshot.jpg", "diagram.svg", 
            "photo_2024_01_15.jpg", "icon.ico"
        ],
        "code": [
            "main.py", "utils.js", "styles.css", "index.html", 
            "config.json", "package.json", "setup.py"
        ],
        "data": [
            "users.csv", "config.xml", "data.json", 
            "backup.sql", "metrics.xlsx"
        ],
        "temporary": [
            "temp_file.tmp", "cache.cache", "debug.log", 
            "backup.bak", ".DS_Store"
        ],
        "duplicates": [
            "important_doc.pdf", "important_doc_copy.pdf",  # Duplicates
            "image.jpg", "image (1).jpg"  # Duplicates
        ]
    }
    
    # Create the files
    for category, filenames in files_to_create.items():
        category_content = f"Sample {category} file content.\nCreated for OCD demo.\nTimestamp: 2024-01-15"
        
        for filename in filenames:
            file_path = demo_dir / filename
            
            # Create some nested structure
            if category == "code" and filename.endswith(('.py', '.js')):
                nested_dir = demo_dir / "src"
                nested_dir.mkdir(exist_ok=True)
                file_path = nested_dir / filename
            elif category == "documents" and filename.endswith('.pdf'):
                nested_dir = demo_dir / "docs"
                nested_dir.mkdir(exist_ok=True)
                file_path = nested_dir / filename
            
            # Write file content
            file_path.write_text(category_content)
    
    # Create some empty directories
    (demo_dir / "empty_folder1").mkdir(exist_ok=True)
    (demo_dir / "empty_folder2").mkdir(exist_ok=True)
    
    # Create a project structure
    project_dir = demo_dir / "web_project"
    project_dir.mkdir(exist_ok=True)
    (project_dir / "package.json").write_text('{"name": "demo-project", "version": "1.0.0"}')
    (project_dir / "index.html").write_text('<html><head><title>Demo</title></head></html>')
    (project_dir / "main.js").write_text('console.log("Demo project");')


def count_files(directory: Path) -> int:
    """Count total files in directory."""
    return len([f for f in directory.rglob("*") if f.is_file()])


def create_demo_llm():
    """Create a demo LLM that provides realistic responses."""
    class DemoLLM:
        def __init__(self):
            self.responses = {
                "organize": [
                    "I'll analyze the directory structure and organize files by type into logical folders.",
                    "Creating folders: Documents, Images, Code, Data, Temporary",
                    "Moving files to appropriate categories based on extensions and content"
                ],
                "duplicate": [
                    "Scanning for duplicate files using hash comparison",
                    "Found 4 duplicate files that can be consolidated",
                    "Moving duplicates to _Duplicates folder for review"
                ],
                "clean": [
                    "Identifying temporary files: .tmp, .cache, .log, .bak files",
                    "Found 5 temporary files and 2 empty directories",
                    "Cleaning up safely while preserving important files"
                ],
                "naming": [
                    "Analyzing current naming conventions",
                    "Applying consistent snake_case naming to files",
                    "Renaming files to follow standard conventions"
                ],
                "project": [
                    "Detected web project structure with package.json",
                    "Creating standard project folders: src/, docs/, tests/",
                    "Organizing code files into appropriate project structure"
                ]
            }
        
        def invoke(self, messages):
            message = str(messages).lower()
            
            # Determine response type based on message content
            for key, responses in self.responses.items():
                if key in message:
                    import random
                    return random.choice(responses)
            
            return "I'll analyze the files and suggest the best organization approach."
        
        async def ainvoke(self, messages):
            return self.invoke(messages)
    
    return DemoLLM()


async def demo_cli_usage():
    """Demo CLI usage examples."""
    print("\n🖥️  CLI Usage Examples")
    print("=" * 30)
    
    examples = [
        "# Analyze directory structure",
        "ocd analyze ~/Documents --mode local-only",
        "",
        "# Organize files intelligently (dry run)",
        "ocd organize ~/Downloads --strategy smart --dry-run",
        "",
        "# Execute organization with specific strategy",
        "ocd organize ~/Desktop --strategy by_type --execute --safety balanced",
        "",
        "# Natural language organization",
        'ocd organize ~/Photos --task "organize photos by year and event"',
        "",
        "# Clean up with specific provider",
        "ocd organize ~/Projects --provider local_slm --task 'clean up temp files and organize by project type'",
    ]
    
    for example in examples:
        if example.startswith("#"):
            print(f"\n💡 {example}")
        elif example.strip():
            print(f"   $ {example}")
        else:
            print()


if __name__ == "__main__":
    print("🚀 Starting OCD LangChain Agent Demo\n")
    
    asyncio.run(demo_organization_agent())
    asyncio.run(demo_cli_usage())
    
    print("\n✨ Demo completed!")
    print("💡 To use with real LangChain providers:")
    print("   pip install ocd[full]")
    print("   export OPENAI_API_KEY=your_key")
    print("   ocd organize ~/your_directory --provider openai --execute")