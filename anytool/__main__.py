import asyncio
import argparse
import sys
import logging
from typing import Optional

from anytool.tool_layer import AnyTool, AnyToolConfig
from anytool.utils.logging import Logger
from anytool.utils.ui import create_ui, AnyToolUI
from anytool.utils.ui_integration import UIIntegration
from anytool.utils.cli_display import CLIDisplay
from anytool.utils.display import colorize

logger = Logger.get_logger(__name__)


class UIManager:
    def __init__(self, ui: Optional[AnyToolUI], ui_integration: Optional[UIIntegration]):
        self.ui = ui
        self.ui_integration = ui_integration
        self._original_log_levels = {}
    
    async def start_live_display(self):
        if not self.ui or not self.ui_integration:
            return
        
        print()
        print(colorize("  ▣ Starting real-time visualization...", 'c'))
        print()
        await asyncio.sleep(1)
        
        self._suppress_logs()
        
        await self.ui.start_live_display()
        await self.ui_integration.start_monitoring(poll_interval=2.0)
    
    async def stop_live_display(self):
        if not self.ui or not self.ui_integration:
            return
        
        await self.ui_integration.stop_monitoring()
        await self.ui.stop_live_display()
        
        self._restore_logs()
    
    def print_summary(self, result: dict):
        if self.ui:
            self.ui.print_summary(result)
        else:
            CLIDisplay.print_result_summary(result)
    
    def _suppress_logs(self):
        log_names = ["anytool", "anytool.grounding", "anytool.agents"]
        for name in log_names:
            log = logging.getLogger(name)
            self._original_log_levels[name] = log.level
            log.setLevel(logging.CRITICAL)
    
    def _restore_logs(self):
        for name, level in self._original_log_levels.items():
            logging.getLogger(name).setLevel(level)
        self._original_log_levels.clear()


async def _execute_task(anytool: AnyTool, query: str, ui_manager: UIManager):
    await ui_manager.start_live_display()
    result = await anytool.execute(query)
    await ui_manager.stop_live_display()
    ui_manager.print_summary(result)
    return result


async def interactive_mode(anytool: AnyTool, ui_manager: UIManager):
    CLIDisplay.print_interactive_header()
    
    while True:
        try:
            prompt = colorize(">>> ", 'c', bold=True)
            query = input(f"\n{prompt}").strip()
            
            if not query:
                continue
            
            if query.lower() in ['exit', 'quit', 'q']:
                print("\nExiting...")
                break

            if query.lower() == 'status':
                _print_status(anytool)
                continue
            
            if query.lower() == 'help':
                CLIDisplay.print_help()
                continue

            CLIDisplay.print_task_header(query)
            await _execute_task(anytool, query, ui_manager)
            
        except KeyboardInterrupt:
            print("\n\nInterrupt signal detected, exiting...")
            break
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            print(f"\nError: {e}")


async def single_query_mode(anytool: AnyTool, query: str, ui_manager: UIManager):
    CLIDisplay.print_task_header(query, title="▶ Single Query Execution")
    await _execute_task(anytool, query, ui_manager)


def _print_status(anytool: AnyTool):
    """Print system status"""
    from anytool.utils.display import Box, BoxStyle
    
    box = Box(width=70, style=BoxStyle.ROUNDED, color='bl')
    print()
    print(box.text_line(colorize("System Status", 'bl', bold=True), 
                      align='center', indent=4, text_color=''))
    print(box.separator_line(indent=4))
    
    status_lines = [
        f"Initialized: {colorize('Yes' if anytool.is_initialized() else 'No', 'g' if anytool.is_initialized() else 'rd')}",
        f"Running: {colorize('Yes' if anytool.is_running() else 'No', 'y' if anytool.is_running() else 'g')}",
        f"Model: {colorize(anytool.config.llm_model, 'c')}",
    ]
    
    if anytool.is_initialized():
        backends = anytool.list_backends()
        status_lines.append(f"Backends: {colorize(', '.join(backends), 'c')}")
        
        sessions = anytool.list_sessions()
        status_lines.append(f"Active Sessions: {colorize(str(len(sessions)), 'y')}")
    
    for line in status_lines:
        print(box.text_line(f"  {line}", indent=4, text_color=''))
    
    print(box.bottom_line(indent=4))
    print()


def _create_argument_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser"""
    parser = argparse.ArgumentParser(
        description='AnyTool - Universal Tool-Use Layer for AI Agents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    # Basic arguments
    parser.add_argument('--config', '-c', type=str, help='Configuration file path (JSON format)')
    parser.add_argument('--query', '-q', type=str, help='Single query mode: execute query directly')
    
    # LLM arguments
    parser.add_argument('--model', '-m', type=str, help='LLM model name')
    
    # Logging arguments
    parser.add_argument('--log-level', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='Log level')
    
    # Execution arguments
    parser.add_argument('--max-iterations', type=int, help='Maximum iteration count')
    parser.add_argument('--timeout', type=float, help='LLM API call timeout (seconds)')
    
    # UI arguments
    parser.add_argument('--interactive', '-i', action='store_true', help='Force interactive mode')
    parser.add_argument('--no-ui', action='store_true', help='Disable visualization UI')
    parser.add_argument('--ui-compact', action='store_true', help='Use compact UI layout')
    
    return parser


def _load_config(args) -> AnyToolConfig:
    """Load configuration"""
    cli_overrides = {}
    if args.model:
        cli_overrides['llm_model'] = args.model
    if args.max_iterations is not None:
        cli_overrides['grounding_max_iterations'] = args.max_iterations
    if args.timeout is not None:
        cli_overrides['llm_timeout'] = args.timeout
    if args.log_level:
        cli_overrides['log_level'] = args.log_level
    
    try:
        # Load from config file if provided
        if args.config:
            import json
            with open(args.config, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            
            # Apply CLI overrides
            config_dict.update(cli_overrides)
            config = AnyToolConfig(**config_dict)
            
            print(f"✓ Loaded from config file: {args.config}")
        else:
            # Use default config + CLI overrides
            config = AnyToolConfig(**cli_overrides)
            print("✓ Using default configuration")
        
        if cli_overrides:
            print(f"✓ CLI overrides: {', '.join(cli_overrides.keys())}")
        
        if args.log_level:
            Logger.set_level(args.log_level)
        
        return config
        
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)


def _setup_ui(args) -> tuple[Optional[AnyToolUI], Optional[UIIntegration]]:
    if args.no_ui:
        CLIDisplay.print_banner()
        return None, None
    
    ui = create_ui(enable_live=True, compact=args.ui_compact)
    ui.print_banner()
    ui_integration = UIIntegration(ui)
    return ui, ui_integration


async def _initialize_anytool(config: AnyToolConfig, args) -> AnyTool:
    anytool = AnyTool(config)
    
    init_steps = [("Initializing AnyTool...", "loading")]
    CLIDisplay.print_initialization_progress(init_steps, show_header=False)
    
    if not args.config:
        original_log_level = Logger.get_logger("anytool").level
        for log_name in ["anytool", "anytool.grounding", "anytool.agents"]:
            Logger.get_logger(log_name).setLevel(logging.WARNING)
    
    await anytool.initialize()
    
    # Restore log level
    if not args.config:
        for log_name in ["anytool", "anytool.grounding", "anytool.agents"]:
            Logger.get_logger(log_name).setLevel(original_log_level)
    
    # Print initialization results
    backends = anytool.list_backends()
    init_steps = [
        ("LLM Client", "ok"),
        (f"Grounding Backends ({len(backends)} available)", "ok"),
        ("Grounding Agent", "ok"),
    ]
    
    if config.enable_recording:
        init_steps.append(("Recording Manager", "ok"))
    
    CLIDisplay.print_initialization_progress(init_steps, show_header=True)
    
    return anytool


async def main():
    parser = _create_argument_parser()
    args = parser.parse_args()
    
    # Load configuration
    config = _load_config(args)
    
    # Setup UI
    ui, ui_integration = _setup_ui(args)
    
    # Print configuration
    CLIDisplay.print_configuration(config)
    
    anytool = None
    
    try:
        # Initialize AnyTool
        anytool = await _initialize_anytool(config, args)
        
        # Connect UI (if enabled)
        if ui_integration:
            ui_integration.attach_llm_client(anytool._llm_client)
            ui_integration.attach_grounding_client(anytool._grounding_client)
            CLIDisplay.print_system_ready()
        
        ui_manager = UIManager(ui, ui_integration)
        
        # Run appropriate mode
        if args.query:
            await single_query_mode(anytool, args.query, ui_manager)
        else:
            await interactive_mode(anytool, ui_manager)
        
    except KeyboardInterrupt:
        print("\n\nInterrupt signal detected")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        print(f"\nError: {e}")
        return 1
    finally:
        if anytool:
            print("\nCleaning up resources...")
            await anytool.cleanup()
    
    print("\nGoodbye!")
    return 0


def run_main():
    """Run main function"""
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nProgram interrupted")
        sys.exit(0)


if __name__ == "__main__":
    run_main()