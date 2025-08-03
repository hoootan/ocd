"""
Base Agent for File Organization
================================

Foundation class for all LangChain-based file organization agents.
Provides safety mechanisms, operation previews, and tool integration.
"""

import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import structlog

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import Tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

from ocd.core.exceptions import OCDError
from ocd.tools.file_operations import FileOperationManager
from ocd.core.types import OperationPreview, SafetyLevel

logger = structlog.get_logger(__name__)


class BaseAgent(ABC):
    """
    Base class for all file organization agents.
    
    Provides:
    - Safety mechanisms for file operations
    - Operation previewing and confirmation
    - Tool integration with LangChain
    - Structured logging and error handling
    - Undo/rollback capabilities
    """
    
    def __init__(
        self,
        llm_provider,
        safety_level: SafetyLevel = SafetyLevel.BALANCED,
        dry_run: bool = True,
        max_operations: int = 100,
        require_confirmation: bool = True
    ):
        """
        Initialize the base agent.
        
        Args:
            llm_provider: LangChain LLM provider (OpenAI, Anthropic, Local, etc.)
            safety_level: Level of safety checks to perform
            dry_run: Whether to run in preview mode by default
            max_operations: Maximum number of operations per session
            require_confirmation: Whether to require user confirmation
        """
        self.llm = llm_provider
        self.safety_level = safety_level
        self.dry_run = dry_run
        self.max_operations = max_operations
        self.require_confirmation = require_confirmation
        
        # File operation manager for safe operations
        self.file_ops = FileOperationManager(safety_level=safety_level)
        
        # Operation tracking
        self.operations_performed = []
        self.current_session_ops = 0
        
        # Agent-specific tools (to be defined by subclasses)
        self.tools = []
        self.agent_executor = None
        
        self.logger = logger.bind(agent_type=self.__class__.__name__)
        
    async def initialize(self) -> None:
        """Initialize the agent and set up tools."""
        try:
            # Setup base tools available to all agents
            base_tools = await self._setup_base_tools()
            
            # Get agent-specific tools
            agent_tools = await self._setup_agent_tools()
            
            # Combine all tools
            self.tools = base_tools + agent_tools
            
            # Create the agent executor
            prompt = await self._create_agent_prompt()
            agent = create_tool_calling_agent(self.llm, self.tools, prompt)
            
            self.agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=True,
                max_iterations=10,
                handle_parsing_errors=True,
            )
            
            self.logger.info("Agent initialized", tools_count=len(self.tools))
            
        except Exception as e:
            self.logger.error("Failed to initialize agent", error=str(e))
            raise OCDError(f"Agent initialization failed: {e}")
    
    async def _setup_base_tools(self) -> List[Tool]:
        """Setup tools available to all agents."""
        return [
            Tool(
                name="analyze_directory",
                func=self._analyze_directory,
                description="Analyze directory structure, file types, and organization patterns"
            ),
            Tool(
                name="preview_operations", 
                func=self._preview_operations,
                description="Preview what file operations would be performed without executing them"
            ),
            Tool(
                name="create_directory",
                func=self._create_directory,
                description="Create a new directory with safety checks"
            ),
            Tool(
                name="move_file",
                func=self._move_file,
                description="Move a file to a new location with conflict resolution"
            ),
            Tool(
                name="rename_file", 
                func=self._rename_file,
                description="Rename a file with intelligent conflict handling"
            ),
            Tool(
                name="get_file_info",
                func=self._get_file_info,
                description="Get detailed information about a file or directory"
            ),
            Tool(
                name="validate_operation",
                func=self._validate_operation,
                description="Validate if a file operation is safe and allowed"
            )
        ]
    
    @abstractmethod
    async def _setup_agent_tools(self) -> List[Tool]:
        """Setup agent-specific tools. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    async def _create_agent_prompt(self) -> ChatPromptTemplate:
        """Create the agent's system prompt. Must be implemented by subclasses."""
        pass
    
    async def execute_task(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a file organization task.
        
        Args:
            task: Natural language description of the task
            context: Additional context like target directory, preferences, etc.
            
        Returns:
            Result of the task execution
        """
        if not self.agent_executor:
            await self.initialize()
            
        try:
            self.logger.info("Executing task", task=task, context=context)
            
            # Check operation limits
            if self.current_session_ops >= self.max_operations:
                raise OCDError(f"Maximum operations ({self.max_operations}) reached for this session")
            
            # Prepare the input with context
            agent_input = {
                "input": task,
                "context": context or {},
                "safety_level": self.safety_level.value,
                "dry_run": self.dry_run,
            }
            
            # Execute the task
            result = await self._execute_with_safety(agent_input)
            
            self.logger.info("Task completed", operations_count=len(result.get("operations", [])))
            
            return result
            
        except Exception as e:
            self.logger.error("Task execution failed", task=task, error=str(e))
            raise OCDError(f"Task execution failed: {e}")
    
    async def _execute_with_safety(self, agent_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent task with safety mechanisms."""
        try:
            # Run the agent
            if asyncio.iscoroutinefunction(self.agent_executor.invoke):
                result = await self.agent_executor.ainvoke(agent_input)
            else:
                # Run in thread pool if not async
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, self.agent_executor.invoke, agent_input)
            
            # Process and validate the result
            processed_result = await self._process_agent_result(result)
            
            return processed_result
            
        except Exception as e:
            self.logger.error("Agent execution failed", error=str(e))
            raise OCDError(f"Agent execution failed: {e}")
    
    async def _process_agent_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Process and validate the agent's result."""
        operations = result.get("operations", [])
        
        # Track operations
        self.current_session_ops += len(operations)
        self.operations_performed.extend(operations)
        
        return {
            "success": True,
            "message": result.get("output", "Task completed successfully"),
            "operations": operations,
            "operations_count": len(operations),
            "dry_run": self.dry_run,
        }
    
    # Tool implementation methods
    
    async def _analyze_directory(self, directory_path: str) -> str:
        """Analyze directory structure and patterns."""
        try:
            from ocd.analyzers import DirectoryAnalyzer
            
            analyzer = DirectoryAnalyzer()
            result = await analyzer.analyze_directory(
                Path(directory_path),
                analysis_types=["structure", "content", "metadata"]
            )
            
            # Format for agent consumption
            analysis = {
                "total_files": result.directory_info.total_files,
                "total_size": result.directory_info.total_size,
                "depth": result.directory_info.depth,
                "patterns": result.extracted_patterns,
                "recommendations": result.recommendations,
            }
            
            return f"Directory analysis: {analysis}"
            
        except Exception as e:
            return f"Analysis failed: {e}"
    
    async def _preview_operations(self, operations: str) -> str:
        """Preview what operations would be performed."""
        try:
            # Parse operations (this would be more sophisticated in reality)
            preview = await self.file_ops.preview_operations(operations)
            return f"Operation preview: {preview}"
        except Exception as e:
            return f"Preview failed: {e}"
    
    async def _create_directory(self, path: str, parents: bool = True) -> str:
        """Create a directory with safety checks."""
        try:
            if self.dry_run:
                return f"[DRY RUN] Would create directory: {path}"
            
            result = await self.file_ops.create_directory(Path(path), parents=parents)
            return f"Created directory: {result.path}"
        except Exception as e:
            return f"Failed to create directory: {e}"
    
    async def _move_file(self, source: str, destination: str) -> str:
        """Move a file with safety checks."""
        try:
            if self.dry_run:
                return f"[DRY RUN] Would move {source} to {destination}"
            
            result = await self.file_ops.move_file(Path(source), Path(destination))
            return f"Moved file: {result.source} -> {result.destination}"
        except Exception as e:
            return f"Failed to move file: {e}"
    
    async def _rename_file(self, current_path: str, new_name: str) -> str:
        """Rename a file with safety checks."""
        try:
            if self.dry_run:
                return f"[DRY RUN] Would rename {current_path} to {new_name}"
            
            result = await self.file_ops.rename_file(Path(current_path), new_name)
            return f"Renamed file: {result.old_name} -> {result.new_name}"
        except Exception as e:
            return f"Failed to rename file: {e}"
    
    async def _get_file_info(self, file_path: str) -> str:
        """Get detailed file information."""
        try:
            path = Path(file_path)
            if not path.exists():
                return f"File does not exist: {file_path}"
            
            stat = path.stat()
            info = {
                "name": path.name,
                "size": stat.st_size,
                "type": "directory" if path.is_dir() else "file",
                "extension": path.suffix if path.is_file() else None,
                "modified": stat.st_mtime,
            }
            
            return f"File info: {info}"
        except Exception as e:
            return f"Failed to get file info: {e}"
    
    async def _validate_operation(self, operation: str) -> str:
        """Validate if an operation is safe."""
        try:
            is_safe = await self.file_ops.validate_operation(operation)
            return f"Operation validation: {'SAFE' if is_safe else 'UNSAFE'}"
        except Exception as e:
            return f"Validation failed: {e}"
    
    async def rollback_operations(self, count: Optional[int] = None) -> Dict[str, Any]:
        """Rollback recent operations."""
        try:
            operations_to_rollback = self.operations_performed[-count:] if count else self.operations_performed
            
            rollback_result = await self.file_ops.rollback_operations(operations_to_rollback)
            
            # Remove rolled back operations from history
            if count:
                self.operations_performed = self.operations_performed[:-count]
            else:
                self.operations_performed.clear()
            
            self.logger.info("Operations rolled back", count=len(operations_to_rollback))
            
            return {
                "success": True,
                "rolled_back_count": len(operations_to_rollback),
                "operations": rollback_result
            }
            
        except Exception as e:
            self.logger.error("Rollback failed", error=str(e))
            raise OCDError(f"Rollback failed: {e}")
    
    def get_operation_history(self) -> List[Dict[str, Any]]:
        """Get history of all operations performed."""
        return self.operations_performed.copy()
    
    def clear_history(self) -> None:
        """Clear operation history."""
        self.operations_performed.clear()
        self.current_session_ops = 0
        self.logger.info("Operation history cleared")