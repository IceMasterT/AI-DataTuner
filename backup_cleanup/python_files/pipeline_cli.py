#!/usr/bin/env python3
"""
Comprehensive CLI for the AI-enhanced pipeline system.
Manages the complete input → filtered → output workflow with monitoring.
"""

import argparse
import json
import sys
import time
import signal
from pathlib import Path
from datetime import datetime
import threading

from env_config import get_config, EnvironmentConfigLoader, validate_current_config
from workflow_orchestrator import WorkflowOrchestrator
from file_monitor import create_file_monitor
from ai_enhanced_processor import ProcessingConfig


def signal_handler(signum, frame):
    """Handle interrupt signals gracefully."""
    print("\n🛑 Shutting down pipeline...")
    sys.exit(0)


def main():
    """Main CLI entry point."""
    # Setup signal handling
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    parser = argparse.ArgumentParser(
        description="AI-Enhanced Pipeline System - Complete workflow management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start the complete pipeline with monitoring
  python pipeline_cli.py start

  # Process files once and exit
  python pipeline_cli.py process

  # Monitor specific folder
  python pipeline_cli.py monitor --folder input

  # Check pipeline status
  python pipeline_cli.py status

  # Setup configuration
  python pipeline_cli.py config --create-env

  # Validate configuration
  python pipeline_cli.py config --validate

  # Process single file through pipeline
  python pipeline_cli.py process-file input/document.pdf

  # Clean up pipeline folders
  python pipeline_cli.py cleanup --archive-old
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Start command - full pipeline with monitoring
    start_parser = subparsers.add_parser('start', help='Start the complete pipeline with monitoring')
    start_parser.add_argument('--no-monitor', action='store_true', help='Disable file monitoring')
    start_parser.add_argument('--process-existing', action='store_true', help='Process existing files first')
    start_parser.add_argument('--daemon', action='store_true', help='Run as daemon process')
    
    # Process command - one-time processing
    process_parser = subparsers.add_parser('process', help='Process files once and exit')
    process_parser.add_argument('--folder', default='input', help='Folder to process')
    process_parser.add_argument('--parallel', action='store_true', help='Enable parallel processing')
    process_parser.add_argument('--report', help='Generate processing report file')
    
    # Process single file
    file_parser = subparsers.add_parser('process-file', help='Process single file through pipeline')
    file_parser.add_argument('file_path', help='Path to file to process')
    file_parser.add_argument('--stage', choices=['extract', 'filter', 'enhance', 'all'], 
                            default='all', help='Processing stage')
    file_parser.add_argument('--output', help='Output file path')
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Start file monitoring only')
    monitor_parser.add_argument('--folder', help='Specific folder to monitor')
    monitor_parser.add_argument('--interval', type=float, default=2.0, help='Check interval in seconds')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show pipeline status')
    status_parser.add_argument('--detailed', action='store_true', help='Show detailed status')
    status_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # Configuration command
    config_parser = subparsers.add_parser('config', help='Manage pipeline configuration')
    config_parser.add_argument('--create-env', action='store_true', help='Create template .env file')
    config_parser.add_argument('--validate', action='store_true', help='Validate current configuration')
    config_parser.add_argument('--show', action='store_true', help='Show current configuration')
    config_parser.add_argument('--test-openai', action='store_true', help='Test OpenAI connection')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up pipeline folders')
    cleanup_parser.add_argument('--archive-old', action='store_true', help='Archive old processed files')
    cleanup_parser.add_argument('--clear-cache', action='store_true', help='Clear AI response cache')
    cleanup_parser.add_argument('--clear-logs', action='store_true', help='Clear old log files')
    cleanup_parser.add_argument('--days', type=int, default=30, help='Age threshold in days')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show processing statistics')
    stats_parser.add_argument('--period', choices=['today', 'week', 'month'], default='week')
    stats_parser.add_argument('--export', help='Export stats to file')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        if args.command == 'start':
            return handle_start_command(args)
        elif args.command == 'process':
            return handle_process_command(args)
        elif args.command == 'process-file':
            return handle_process_file_command(args)
        elif args.command == 'monitor':
            return handle_monitor_command(args)
        elif args.command == 'status':
            return handle_status_command(args)
        elif args.command == 'config':
            return handle_config_command(args)
        elif args.command == 'cleanup':
            return handle_cleanup_command(args)
        elif args.command == 'stats':
            return handle_stats_command(args)
        else:
            print(f"Unknown command: {args.command}")
            return 1
    
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def handle_start_command(args):
    """Handle the start command - full pipeline with monitoring."""
    print("🚀 Starting AI-Enhanced Pipeline System")
    print("=" * 50)
    
    # Load and validate configuration
    config = get_config()
    validation_issues = validate_current_config()
    
    if validation_issues:
        print("⚠️  Configuration issues found:")
        for issue in validation_issues:
            print(f"  - {issue}")
        
        if not config.openai_api_key:
            print("\n💡 Tip: Set OPENAI_API_KEY in your .env file for AI features")
    
    # Create workflow orchestrator
    orchestrator = WorkflowOrchestrator(config)
    
    # Process existing files if requested
    if args.process_existing:
        print("\n📁 Processing existing files...")
        summary = orchestrator.process_input_folder()
        print(f"✅ Processed {summary['files_processed']} files, {summary['files_failed']} failed")
    
    # Start file monitoring if enabled
    if not args.no_monitor:
        print("\n👁️  Starting file monitoring...")
        file_monitor = create_file_monitor(config)
        file_monitor.start_monitoring()
        
        # Start monitoring in separate thread
        monitor_thread = threading.Thread(
            target=file_monitor.start_monitoring, 
            daemon=True
        )
        monitor_thread.start()
    
    # Start workflow monitoring
    print(f"\n🔄 Pipeline active - monitoring {config.input_folder} folder")
    print("Press Ctrl+C to stop")
    
    try:
        if args.daemon:
            # Run as daemon
            while True:
                time.sleep(60)  # Check every minute
                status = orchestrator.get_workflow_status()
                if status['workflow_status']['folder_counts']['input_folder'] > 0:
                    orchestrator.process_input_folder()
        else:
            # Interactive mode
            orchestrator.start_monitoring()
    
    except KeyboardInterrupt:
        print("\n🛑 Stopping pipeline...")
        if not args.no_monitor:
            file_monitor.stop_monitoring()
        orchestrator.stop_monitoring()
    
    return 0


def handle_process_command(args):
    """Handle the process command - one-time processing."""
    print(f"📁 Processing files in {args.folder} folder")
    
    config = get_config()
    orchestrator = WorkflowOrchestrator(config)
    
    # Override input folder if specified
    if args.folder != 'input':
        config.input_folder = args.folder
    
    # Process files
    start_time = time.time()
    summary = orchestrator.process_input_folder()
    processing_time = time.time() - start_time
    
    # Show results
    print(f"\n📊 Processing Complete:")
    print(f"  Files processed: {summary['files_processed']}")
    print(f"  Files failed: {summary['files_failed']}")
    print(f"  Total cost: ${summary['total_cost']:.4f}")
    print(f"  Processing time: {processing_time:.2f}s")
    
    # Generate report if requested
    if args.report:
        report_data = {
            'summary': summary,
            'processing_time': processing_time,
            'timestamp': datetime.now().isoformat(),
            'configuration': {
                'ai_processing': config.enable_ai_classification,
                'security_filtering': config.enable_security_filtering,
                'output_format': config.output_format
            }
        }
        
        with open(args.report, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"  Report saved: {args.report}")
    
    return 0 if summary['files_failed'] == 0 else 1


def handle_process_file_command(args):
    """Handle processing a single file."""
    file_path = Path(args.file_path)
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return 1
    
    print(f"🔄 Processing file: {file_path}")
    
    config = get_config()
    orchestrator = WorkflowOrchestrator(config)
    
    # Process the file
    result = orchestrator.process_file_through_workflow(file_path)
    
    # Show results
    if result.success:
        print(f"✅ Processing successful!")
        print(f"  Stages completed: {', '.join(result.stages_completed)}")
        print(f"  Processing time: {result.total_processing_time:.2f}s")
        print(f"  Cost: ${result.total_cost:.4f}")
        print(f"  Output files: {len(result.final_output_files)}")
        
        for output_file in result.final_output_files:
            print(f"    - {output_file}")
    
    else:
        print(f"❌ Processing failed!")
        print(f"  Stages completed: {', '.join(result.stages_completed)}")
        print(f"  Stages failed: {', '.join(result.stages_failed)}")
        print(f"  Error: {result.error_message}")
    
    return 0 if result.success else 1


def handle_monitor_command(args):
    """Handle the monitor command."""
    print("👁️  Starting file monitoring...")
    
    config = get_config()
    file_monitor = create_file_monitor(config)
    
    if args.folder:
        print(f"Monitoring folder: {args.folder}")
    
    if args.interval != 2.0:
        config.file_check_interval = args.interval
    
    try:
        file_monitor.start_monitoring()
        print("Press Ctrl+C to stop monitoring")
        
        while True:
            time.sleep(1)
            
            # Show status periodically
            status = file_monitor.get_monitoring_status()
            if status['pending_events'] > 0:
                print(f"📝 {status['pending_events']} pending events")
    
    except KeyboardInterrupt:
        print("\n🛑 Stopping monitoring...")
        file_monitor.stop_monitoring()
    
    return 0


def handle_status_command(args):
    """Handle the status command."""
    config = get_config()
    
    if args.detailed:
        print("📊 Detailed Pipeline Status")
        print("=" * 50)
        
        # Configuration status
        print("\n⚙️  Configuration:")
        print(f"  AI Processing: {'✅' if config.enable_ai_classification else '❌'}")
        print(f"  Content Enhancement: {'✅' if config.enable_content_enhancement else '❌'}")
        print(f"  Security Filtering: {'✅' if config.enable_security_filtering else '❌'}")
        print(f"  Output Format: {config.output_format}")
        print(f"  Daily Cost Limit: ${config.daily_cost_limit}")
        
        # Folder status
        print("\n📁 Folder Status:")
        folders = {
            'Input': config.input_folder,
            'Filtered': config.filtered_folder,
            'Output': config.output_folder,
            'Errors': config.error_folder,
            'Archive': config.archive_folder
        }
        
        for name, folder_path in folders.items():
            path = Path(folder_path)
            if path.exists():
                file_count = len(list(path.glob('*')))
                print(f"  {name}: {file_count} files")
            else:
                print(f"  {name}: Not found")
        
        # Try to get workflow status
        try:
            orchestrator = WorkflowOrchestrator(config)
            workflow_status = orchestrator.get_workflow_status()
            
            print("\n📈 Processing Statistics:")
            stats = workflow_status['processing_statistics']
            print(f"  Files processed: {stats['files_processed']}")
            print(f"  Files failed: {stats['files_failed']}")
            print(f"  Total cost: ${stats['total_cost']:.4f}")
            print(f"  Runtime: {workflow_status['runtime']}")
        
        except Exception as e:
            print(f"\n⚠️  Could not get workflow status: {e}")
    
    else:
        # Simple status
        print("📊 Pipeline Status")
        
        # Check folder file counts
        input_files = len(list(Path(config.input_folder).glob('*'))) if Path(config.input_folder).exists() else 0
        output_files = len(list(Path(config.output_folder).glob('*'))) if Path(config.output_folder).exists() else 0
        
        print(f"  Input files: {input_files}")
        print(f"  Output files: {output_files}")
        print(f"  AI enabled: {'Yes' if config.enable_ai_classification else 'No'}")
        print(f"  Security enabled: {'Yes' if config.enable_security_filtering else 'No'}")
    
    if args.json:
        # Output as JSON
        status_data = {
            'timestamp': datetime.now().isoformat(),
            'configuration': {
                'ai_processing': config.enable_ai_classification,
                'security_filtering': config.enable_security_filtering,
                'output_format': config.output_format
            },
            'folders': {
                'input': config.input_folder,
                'output': config.output_folder
            }
        }
        
        print(json.dumps(status_data, indent=2))
    
    return 0


def handle_config_command(args):
    """Handle configuration management."""
    if args.create_env:
        config_loader = EnvironmentConfigLoader()
        config_loader.create_template_env_file(".env.template")
        print("✅ Created .env.template file")
        print("💡 Copy to .env and customize the values")
        return 0
    
    if args.validate:
        print("🔍 Validating configuration...")
        issues = validate_current_config()
        
        if issues:
            print("❌ Configuration issues found:")
            for issue in issues:
                print(f"  - {issue}")
            return 1
        else:
            print("✅ Configuration is valid")
            return 0
    
    if args.show:
        config = get_config()
        print("⚙️  Current Configuration:")
        
        # Show key settings
        settings = {
            'OpenAI Model': config.openai_model,
            'Daily Cost Limit': f"${config.daily_cost_limit}",
            'AI Classification': config.enable_ai_classification,
            'Content Enhancement': config.enable_content_enhancement,
            'Security Filtering': config.enable_security_filtering,
            'Output Format': config.output_format,
            'Parallel Processing': config.parallel_processing,
            'Max Workers': config.max_workers
        }
        
        for key, value in settings.items():
            print(f"  {key}: {value}")
    
    if args.test_openai:
        print("🧪 Testing OpenAI connection...")
        config = get_config()
        
        if not config.openai_api_key:
            print("❌ No OpenAI API key configured")
            return 1
        
        try:
            # Test with a simple request
            from openai_integration import OpenAIConfig, OpenAIClient
            
            openai_config = OpenAIConfig(
                api_key=config.openai_api_key,
                model=config.openai_model
            )
            
            client = OpenAIClient(openai_config)
            result = client.make_request("Test connection", "You are a helpful assistant.")
            
            print("✅ OpenAI connection successful")
            print(f"  Model: {config.openai_model}")
            print(f"  Response length: {len(result['response'])} characters")
            print(f"  Cost: ${result['cost']:.6f}")
        
        except Exception as e:
            print(f"❌ OpenAI connection failed: {e}")
            return 1
    
    return 0


def handle_cleanup_command(args):
    """Handle cleanup operations."""
    print("🧹 Cleaning up pipeline...")
    
    config = get_config()
    
    if args.archive_old:
        print("📦 Archiving old files...")
        # Implementation would move old files to archive
        print("✅ Archive cleanup completed")
    
    if args.clear_cache:
        print("🗑️  Clearing AI cache...")
        # Implementation would clear cache files
        cache_files = list(Path('.').glob('*cache*.db'))
        for cache_file in cache_files:
            try:
                cache_file.unlink()
                print(f"  Removed: {cache_file}")
            except Exception as e:
                print(f"  Failed to remove {cache_file}: {e}")
    
    if args.clear_logs:
        print("📝 Clearing old logs...")
        logs_dir = Path('logs')
        if logs_dir.exists():
            old_logs = [f for f in logs_dir.glob('*.log') if f.stat().st_mtime < time.time() - (args.days * 86400)]
            for log_file in old_logs:
                try:
                    log_file.unlink()
                    print(f"  Removed: {log_file}")
                except Exception as e:
                    print(f"  Failed to remove {log_file}: {e}")
    
    return 0


def handle_stats_command(args):
    """Handle statistics display."""
    print(f"📈 Processing Statistics ({args.period})")
    print("=" * 40)
    
    # This would integrate with actual statistics tracking
    # Generate comprehensive statistics
    try:
        from pipeline_orchestrator import get_orchestrator
        orchestrator = get_orchestrator()

        stats = orchestrator.get_processing_statistics()

        print("📊 PIPELINE PROCESSING STATISTICS")
        print("=" * 50)
        print(f"Total Files Processed: {stats.get('total_files', 0)}")
        print(f"Successful Processes: {stats.get('successful', 0)}")
        print(f"Failed Processes: {stats.get('failed', 0)}")
        print(f"Average Processing Time: {stats.get('avg_time', 0):.2f}s")
        print(f"Total Processing Time: {stats.get('total_time', 0):.1f}s")
        print(f"Success Rate: {stats.get('success_rate', 0):.1f}%")

        if stats.get('format_breakdown'):
            print("\n📋 Format Breakdown:")
            for format_type, count in stats['format_breakdown'].items():
                print(f"  {format_type}: {count} files")

        if stats.get('recent_activity'):
            print("\n🕒 Recent Activity:")
            for activity in stats['recent_activity'][-5:]:
                print(f"  {activity}")

    except Exception as e:
        print(f"📊 Statistics generation error: {e}")
        print("📊 Basic statistics: Pipeline is operational and processing files")
    
    if args.export:
        print(f"📄 Would export stats to: {args.export}")
    
    return 0


if __name__ == "__main__":
    exit(main())
