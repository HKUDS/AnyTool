from __future__ import annotations

import asyncio
import traceback
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from anytool.agents import GroundingAgent
from anytool.llm import LLMClient
from anytool.grounding.core.grounding_client import GroundingClient
from anytool.config import get_config, load_config
from anytool.config.loader import get_agent_config
from anytool.recording import RecordingManager
from anytool.utils.logging import Logger

logger = Logger.get_logger(__name__)


@dataclass
class AnyToolConfig:
    # LLM Configuration
    llm_model: str = "openrouter/anthropic/claude-sonnet-4.5"
    llm_enable_thinking: bool = False
    llm_timeout: float = 120.0
    llm_max_retries: int = 3
    llm_rate_limit_delay: float = 0.0
    llm_kwargs: Dict[str, Any] = field(default_factory=dict)
    
    # Separate models for specific tasks (None = use llm_model)
    tool_retrieval_model: Optional[str] = None  # Model for tool retrieval LLM filter
    visual_analysis_model: Optional[str] = None  # Model for visual analysis
    
    # Grounding Configuration
    grounding_config_path: Optional[str] = None
    grounding_max_iterations: Optional[int] = None
    grounding_system_prompt: Optional[str] = None
    
    # Backend Configuration
    backend_scope: Optional[List[str]] = None  # None = All backends ["shell", "gui", "mcp", "web", "system"]
    
    # Workspace Configuration
    workspace_dir: Optional[str] = None
    
    # Recording Configuration
    enable_recording: bool = False
    recording_backends: Optional[List[str]] = None
    recording_log_dir: str = "./logs/recordings"
    enable_screenshot: bool = True
    enable_video: bool = True
    enable_conversation_log: bool = True  # Save LLM conversations to conversations.jsonl
    
    # Logging Configuration
    log_level: str = "INFO"
    log_to_file: bool = False
    log_file_path: Optional[str] = None
    
    def __post_init__(self):
        """Validate configuration"""
        self._grounding_max_iterations_explicit = self.grounding_max_iterations is not None
        if self.grounding_max_iterations is None:
            object.__setattr__(self, "grounding_max_iterations", 20)
        if not self.llm_model:
            raise ValueError("llm_model is required")
        
        logger.debug(f"AnyToolConfig initialized with model: {self.llm_model}")

    def __setattr__(self, name, value):
        if name == "grounding_max_iterations" and hasattr(self, "_grounding_max_iterations_explicit"):
            object.__setattr__(self, "_grounding_max_iterations_explicit", value is not None)
        object.__setattr__(self, name, value)


class AnyTool:
    def __init__(self, config: Optional[AnyToolConfig] = None):
        self.config = config or AnyToolConfig()
        
        self._llm_client: Optional[LLMClient] = None
        self._grounding_client: Optional[GroundingClient] = None
        self._grounding_agent: Optional[GroundingAgent] = None
        self._recording_manager: Optional[RecordingManager] = None
        
        self._initialized = False
        self._running = False
        
        logger.debug("AnyTool instance created")
    
    async def initialize(self) -> None:
        if self._initialized:
            logger.warning("AnyTool already initialized")
            return
        
        logger.info("Initializing AnyTool...")
        
        try:
            self._llm_client = LLMClient(
                model=self.config.llm_model,
                enable_thinking=self.config.llm_enable_thinking,
                rate_limit_delay=self.config.llm_rate_limit_delay,
                max_retries=self.config.llm_max_retries,
                timeout=self.config.llm_timeout,
                **self.config.llm_kwargs
            )
            logger.info(f"✓ LLM Client: {self.config.llm_model}")
            
            # Load grounding config
            # If custom config is provided, merge it with default configs
            # load_config supports multiple files and deep merges them (later files override earlier ones)
            if self.config.grounding_config_path:
                from anytool.config.loader import CONFIG_DIR
                from anytool.config.constants import CONFIG_GROUNDING, CONFIG_SECURITY
                # Load default configs + custom config (custom values will override defaults)
                grounding_config = load_config(
                    CONFIG_DIR / CONFIG_GROUNDING,
                    CONFIG_DIR / CONFIG_SECURITY,
                    self.config.grounding_config_path
                )
                logger.info(f"Merged custom grounding config: {self.config.grounding_config_path}")
            else:
                # Load default configs only
                grounding_config = get_config()
            
            self._grounding_client = GroundingClient(config=grounding_config)
            await self._grounding_client.initialize_all_providers()
            
            backends = list(self._grounding_client.list_providers().keys())
            logger.info(f"✓ Grounding Client: {len(backends)} backends")
            logger.debug(f"  Available backends: {[b.value for b in backends]}")
            
            if self.config.enable_recording:
                self._recording_manager = RecordingManager(
                    enabled=True,
                    task_id="",
                    log_dir=self.config.recording_log_dir,
                    backends=self.config.recording_backends,
                    enable_screenshot=self.config.enable_screenshot,
                    enable_video=self.config.enable_video,
                    enable_conversation_log=self.config.enable_conversation_log,
                    agent_name="AnyTool",
                )
                # Inject recording_manager to grounding_client for GUI intermediate steps
                self._grounding_client.recording_manager = self._recording_manager
                # Register to LLM client for auto-recording tool results
                self._recording_manager.register_to_llm(self._llm_client)
                logger.info(f"✓ Recording enabled: {len(self._recording_manager.backends or [])} backends")
            
            agent_config = get_agent_config("GroundingAgent")
            if agent_config:
                # Use config file values, but command-line args (self.config) take priority
                if self.config._grounding_max_iterations_explicit:
                    max_iterations = self.config.grounding_max_iterations
                else:
                    max_iterations = agent_config.get("max_iterations", 20)
                # Command-line backend_scope > config file > default
                backend_scope = self.config.backend_scope or agent_config.get("backend_scope") or ["gui", "shell", "mcp", "web", "system"]
                visual_analysis_timeout = agent_config.get("visual_analysis_timeout", 30.0)
                # Update config with values from config file
                object.__setattr__(self.config, "grounding_max_iterations", max_iterations)
                logger.info(f"Loaded GroundingAgent config from config_agents.json (max_iterations={max_iterations}, visual_analysis_timeout={visual_analysis_timeout}s)")
            else:
                # Fall back to AnyToolConfig values
                max_iterations = self.config.grounding_max_iterations if self.config.grounding_max_iterations is not None else 20
                backend_scope = self.config.backend_scope or ["gui", "shell", "mcp", "web", "system"]
                visual_analysis_timeout = 30.0
                logger.warning(f"config_agents.json not found, using default config (max_iterations={max_iterations})")
            
            # Create separate LLM client for tool retrieval if configured
            tool_retrieval_llm = None
            if self.config.tool_retrieval_model:
                tool_retrieval_llm = LLMClient(
                    model=self.config.tool_retrieval_model,
                    timeout=self.config.llm_timeout,
                    max_retries=self.config.llm_max_retries,
                )
                logger.info(f"✓ Tool retrieval LLM: {self.config.tool_retrieval_model}")
            
            self._grounding_agent = GroundingAgent(
                name="AnyTool-GroundingAgent",
                backend_scope=backend_scope,
                llm_client=self._llm_client,
                grounding_client=self._grounding_client,
                recording_manager=self._recording_manager,
                system_prompt=self.config.grounding_system_prompt,
                max_iterations=max_iterations,
                visual_analysis_timeout=visual_analysis_timeout,
                tool_retrieval_llm=tool_retrieval_llm,
                visual_analysis_model=self.config.visual_analysis_model,
            )
            logger.info(f"✓ GroundingAgent: {', '.join(backend_scope)}")
            
            self._initialized = True
            logger.info("="*60)
            logger.info("AnyTool ready to use!")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"Failed to initialize AnyTool: {e}")
            await self.cleanup()
            raise
    
    async def execute(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        workspace_dir: Optional[str] = None,
        max_iterations: Optional[int] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a task with AnyTool.
        
        Args:
            task: Task instruction
            context: Additional context
            workspace_dir: Working directory
            max_iterations: Max iterations override
            task_id: External task ID for recording/logging. If None, generates a random one.
                     This allows external callers (e.g., OSWorld) to specify their own task ID
                     so recordings can be easily matched with benchmark results.
        """
        if not self._initialized:
            raise RuntimeError(
                "AnyTool not initialized. "
                "Call await tool_layer.initialize() first or use async with."
            )
        
        if self._running:
            raise RuntimeError("AnyTool is already running a task.")
        
        logger.info("="*60)
        logger.info(f"Task: {task[:100]}...")
        logger.info("="*60)
        
        self._running = True
        start_time = asyncio.get_event_loop().time()
        # Use external task_id if provided, otherwise generate one
        if task_id is None:
            task_id = f"task_{uuid.uuid4().hex[:8]}"
        logger.info(f"Task ID: {task_id}")
        
        try:
            execution_context = context or {}
            execution_context["task_id"] = task_id
            execution_context["instruction"] = task
            
            if max_iterations is not None:
                execution_context["max_iterations"] = max_iterations
            
            if self._recording_manager:
                if self._recording_manager.recording_status:
                    await self._recording_manager.stop()
                    logger.debug("Stopped previous recording session")
                
                self._recording_manager.task_id = task_id
                await self._recording_manager.start()
                logger.info(f"Recording started: {task_id}")
            
            if workspace_dir:
                execution_context["workspace_dir"] = workspace_dir
                logger.info(f"Workspace: {workspace_dir}")
            elif self.config.workspace_dir:
                execution_context["workspace_dir"] = self.config.workspace_dir
                logger.info(f"Workspace: {self.config.workspace_dir}")
            elif self._recording_manager and self._recording_manager.trajectory_dir:
                execution_context["workspace_dir"] = self._recording_manager.trajectory_dir
                logger.info(f"Workspace: {execution_context['workspace_dir']}")
            else:
                import tempfile
                from pathlib import Path
                workspace = Path(tempfile.gettempdir()) / "anytool_workspace" / task_id
                workspace.mkdir(parents=True, exist_ok=True)
                execution_context["workspace_dir"] = str(workspace)
                logger.info(f"Workspace: {execution_context['workspace_dir']}")
            
            logger.info(f"Executing with GroundingAgent (max {max_iterations or self.config.grounding_max_iterations} iterations)...")
            
            result = await self._grounding_agent.process(execution_context)
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            final_result = {
                **result,
                "task_id": task_id,
                "execution_time": execution_time,
            }
            
            status = result.get('status', 'unknown')
            iterations = result.get('iterations', 0)
            tool_count = len(result.get('tool_executions', []))
            
            logger.info("="*60)
            if status == "success":
                logger.info(
                    f"Task completed successfully! "
                    f"({iterations} iterations, {tool_count} tool calls, {execution_time:.2f}s)"
                )
            elif status == "incomplete":
                logger.warning(
                    f"Task incomplete after {iterations} iterations. "
                    f"Consider increasing max_iterations."
                )
            else:
                logger.error(f"Task failed: {result.get('error', 'Unknown error')}")
            logger.info("="*60)
            
            return final_result
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            tb = traceback.format_exc(limit=10)
            logger.error(f"Task execution failed: {e}", exc_info=True)
            
            return {
                "status": "error",
                "error": str(e),
                "traceback": tb,
                "response": f"Task execution error: {str(e)}",
                "execution_time": execution_time,
                "task_id": task_id,
                "iterations": 0,
                "tool_executions": [],
            }
        
        finally:
            if self._recording_manager and self._recording_manager.recording_status:
                try:
                    await self._recording_manager.stop()
                    logger.debug(f"Recording stopped: {task_id}")
                except Exception as e:
                    logger.warning(f"Failed to stop recording: {e}")
            
            # Trigger quality evolution periodically
            await self._maybe_evolve_quality()
            
            self._running = False
    
    async def _maybe_evolve_quality(self) -> None:
        """Trigger quality evolution based on global execution count."""
        if not self._grounding_client or not self._grounding_client.quality_manager:
            return
        
        # Check if evolution should be triggered (every 10 global executions)
        if self._grounding_client.quality_manager.should_evolve():
            try:
                report = await self._grounding_client.evolve_quality()
                if report.get("recommendations"):
                    logger.info(f"Quality evolution: {report['recommendations']}")
            except Exception as e:
                logger.debug(f"Quality evolution skipped: {e}")
    
    async def cleanup(self) -> None:
        """
        Close all sessions and release resources.
        Automatically called when using context manager.
        """
        logger.info("Cleaning up AnyTool resources...")
        
        try:
            if self._grounding_client:
                await self._grounding_client.close_all_sessions()
                logger.debug("All grounding sessions closed")
            
            if self._recording_manager and self._recording_manager.recording_status:
                try:
                    await self._recording_manager.stop()
                    logger.debug("Recording manager stopped")
                except Exception as e:
                    logger.warning(f"Failed to stop recording: {e}")
            
            self._initialized = False
            self._running = False
            
            logger.info("AnyTool cleanup complete")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
    
    def is_initialized(self) -> bool:
        return self._initialized
    
    def is_running(self) -> bool:
        return self._running
    
    def get_config(self) -> AnyToolConfig:
        return self.config
    
    def list_backends(self) -> List[str]:
        if not self._initialized:
            raise RuntimeError("AnyTool not initialized")
        return [backend.value for backend in self._grounding_client.list_providers().keys()]
    
    def list_sessions(self) -> List[str]:
        if not self._initialized:
            raise RuntimeError("AnyTool not initialized")
        return self._grounding_client.list_sessions()
    
    async def __aenter__(self):
        """Context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.cleanup()
        return False
    
    def __repr__(self) -> str:
        status = "initialized" if self._initialized else "not initialized"
        if self._running:
            status = "running"
        backends = ", ".join(self.config.backend_scope) if self.config.backend_scope else "all"
        return f"<AnyTool(status={status}, backends={backends}, model={self.config.llm_model})>"
