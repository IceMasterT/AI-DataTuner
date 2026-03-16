#!/usr/bin/env python3
"""
Command-line interface for the secure text processing system.
Provides comprehensive security filtering and sanitization capabilities.
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

from secure_text_processor import SecureTextProcessor
from security_config import SecurityConfigManager, SecurityLevel
from quarantine_system import QuarantineManager


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Secure Text Processing System - Advanced sanitization for LLM training data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process single file with balanced security
  python secure_cli.py process input.txt -o output.txt

  # Process with strict security level
  python secure_cli.py process input.txt --security-level strict

  # Batch process directory
  python secure_cli.py batch-process data/ -o clean_data/

  # Review quarantined content
  python secure_cli.py quarantine list

  # Generate security report
  python secure_cli.py report --days 30

  # Configure security settings
  python secure_cli.py config --security-level paranoid --save my_config.yaml
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Process command
    process_parser = subparsers.add_parser('process', help='Process single file or text')
    process_parser.add_argument('input', help='Input file or text (use "-" for stdin)')
    process_parser.add_argument('-o', '--output', help='Output file path')
    process_parser.add_argument('-f', '--format', default='qwen', 
                               help='Output conversation format')
    process_parser.add_argument('--security-level', choices=['permissive', 'balanced', 'strict', 'paranoid'],
                               default='balanced', help='Security level')
    process_parser.add_argument('--aggressive', action='store_true',
                               help='Enable aggressive filtering mode')
    process_parser.add_argument('--no-quarantine', action='store_true',
                               help='Disable quarantine system')
    process_parser.add_argument('--config', help='Custom configuration file')
    process_parser.add_argument('--validate-markup', action='store_true', default=True,
                               help='Validate markup content')
    
    # Batch process command
    batch_parser = subparsers.add_parser('batch-process', help='Process multiple files')
    batch_parser.add_argument('input_dir', help='Input directory')
    batch_parser.add_argument('-o', '--output-dir', help='Output directory')
    batch_parser.add_argument('-f', '--format', default='qwen',
                             help='Output conversation format')
    batch_parser.add_argument('--security-level', choices=['permissive', 'balanced', 'strict', 'paranoid'],
                             default='balanced', help='Security level')
    batch_parser.add_argument('--aggressive', action='store_true',
                             help='Enable aggressive filtering mode')
    batch_parser.add_argument('--no-quarantine', action='store_true',
                             help='Disable quarantine system')
    batch_parser.add_argument('--config', help='Custom configuration file')
    batch_parser.add_argument('--recursive', action='store_true',
                             help='Process directories recursively')
    batch_parser.add_argument('--report', help='Generate processing report file')
    
    # Quarantine management commands
    quarantine_parser = subparsers.add_parser('quarantine', help='Manage quarantined content')
    quarantine_subparsers = quarantine_parser.add_subparsers(dest='quarantine_action')
    
    # List quarantined items
    list_parser = quarantine_subparsers.add_parser('list', help='List quarantined content')
    list_parser.add_argument('--threat-level', choices=['suspicious', 'dangerous', 'critical'],
                            help='Filter by threat level')
    list_parser.add_argument('--status', choices=['pending', 'approved', 'rejected'],
                            help='Filter by review status')
    list_parser.add_argument('--limit', type=int, default=50, help='Maximum items to show')
    
    # Review quarantined item
    review_parser = quarantine_subparsers.add_parser('review', help='Review quarantined content')
    review_parser.add_argument('entry_id', help='Quarantine entry ID')
    review_parser.add_argument('action', choices=['approve', 'reject', 'pending'],
                              help='Review action')
    review_parser.add_argument('--notes', help='Review notes')
    
    # Show quarantined item details
    show_parser = quarantine_subparsers.add_parser('show', help='Show quarantine entry details')
    show_parser.add_argument('entry_id', help='Quarantine entry ID')
    
    # Export quarantined data
    export_parser = quarantine_subparsers.add_parser('export', help='Export quarantine data')
    export_parser.add_argument('output_file', help='Output file path')
    export_parser.add_argument('--format', choices=['json', 'csv'], default='json',
                              help='Export format')
    export_parser.add_argument('--threat-level', help='Filter by threat level')
    export_parser.add_argument('--status', help='Filter by review status')
    
    # Configuration commands
    config_parser = subparsers.add_parser('config', help='Manage security configuration')
    config_parser.add_argument('--security-level', choices=['permissive', 'balanced', 'strict', 'paranoid'],
                              help='Set security level')
    config_parser.add_argument('--load', help='Load configuration from file')
    config_parser.add_argument('--save', help='Save current configuration to file')
    config_parser.add_argument('--show', action='store_true', help='Show current configuration')
    config_parser.add_argument('--template', help='Export configuration template')
    config_parser.add_argument('--validate', action='store_true', help='Validate current configuration')
    config_parser.add_argument('--list-profiles', action='store_true', help='List available profiles')
    
    # Reporting commands
    report_parser = subparsers.add_parser('report', help='Generate security reports')
    report_parser.add_argument('--days', type=int, default=7, help='Report period in days')
    report_parser.add_argument('--output', help='Save report to file')
    report_parser.add_argument('--format', choices=['json', 'yaml'], default='json',
                              help='Report format')
    
    # Statistics command
    stats_parser = subparsers.add_parser('stats', help='Show processing statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        if args.command == 'process':
            return handle_process_command(args)
        elif args.command == 'batch-process':
            return handle_batch_process_command(args)
        elif args.command == 'quarantine':
            return handle_quarantine_command(args)
        elif args.command == 'config':
            return handle_config_command(args)
        elif args.command == 'report':
            return handle_report_command(args)
        elif args.command == 'stats':
            return handle_stats_command(args)
        else:
            print(f"Unknown command: {args.command}")
            return 1
    
    except Exception as e:
        print(f"Error: {e}")
        return 1


def handle_process_command(args):
    """Handle single file processing."""
    # Setup configuration
    config_manager = SecurityConfigManager()
    
    if args.config:
        if not config_manager.load_config_from_file(args.config):
            print(f"Failed to load configuration: {args.config}")
            return 1
    else:
        security_level = SecurityLevel(args.security_level)
        config_manager.load_security_level(security_level)
    
    # Create processor
    processor = SecureTextProcessor(
        output_format=args.format,
        aggressive_mode=args.aggressive,
        quarantine_enabled=not args.no_quarantine
    )
    
    # Get input text
    if args.input == '-':
        text = sys.stdin.read()
        source_file = None
    else:
        try:
            with open(args.input, 'r', encoding='utf-8') as f:
                text = f.read()
            source_file = args.input
        except FileNotFoundError:
            print(f"Error: File not found: {args.input}")
            return 1
        except Exception as e:
            print(f"Error reading file: {e}")
            return 1
    
    # Process text
    result = processor.process_text(text, source_file, args.validate_markup)
    
    # Handle result
    if result['success']:
        output_text = result['processed_text']
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_text)
            print(f"✓ Processed successfully: {args.output}")
        else:
            print(output_text)
        
        if result['warnings']:
            print("\nWarnings:", file=sys.stderr)
            for warning in result['warnings']:
                print(f"  - {warning}", file=sys.stderr)
    
    else:
        print("✗ Processing failed:")
        for error in result['errors']:
            print(f"  - {error}")
        
        if result['quarantine_id']:
            print(f"Content quarantined with ID: {result['quarantine_id']}")
        
        return 1
    
    return 0


def handle_batch_process_command(args):
    """Handle batch processing."""
    input_path = Path(args.input_dir)
    
    if not input_path.exists():
        print(f"Error: Input directory not found: {args.input_dir}")
        return 1
    
    # Setup configuration
    config_manager = SecurityConfigManager()
    
    if args.config:
        if not config_manager.load_config_from_file(args.config):
            print(f"Failed to load configuration: {args.config}")
            return 1
    else:
        security_level = SecurityLevel(args.security_level)
        config_manager.load_security_level(security_level)
    
    # Create processor
    processor = SecureTextProcessor(
        output_format=args.format,
        aggressive_mode=args.aggressive,
        quarantine_enabled=not args.no_quarantine
    )
    
    # Find input files
    if args.recursive:
        input_files = list(input_path.rglob("*.txt")) + list(input_path.rglob("*.md"))
    else:
        input_files = list(input_path.glob("*.txt")) + list(input_path.glob("*.md"))
    
    input_files = [str(f) for f in input_files]
    
    if not input_files:
        print("No input files found")
        return 1
    
    print(f"Processing {len(input_files)} files...")
    
    # Process files
    results = processor.batch_process(input_files, args.output_dir)
    
    # Print summary
    print(f"\nProcessing complete:")
    print(f"  Total files: {results['total_files']}")
    print(f"  Successful: {results['successful']}")
    print(f"  Failed: {results['failed']}")
    print(f"  Quarantined: {results['quarantined']}")
    print(f"  Rejected: {results['rejected']}")
    
    # Save report if requested
    if args.report:
        with open(args.report, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Report saved: {args.report}")
    
    return 0 if results['failed'] == 0 else 1


def handle_quarantine_command(args):
    """Handle quarantine management commands."""
    quarantine_manager = QuarantineManager()
    
    if args.quarantine_action == 'list':
        entries = quarantine_manager.database.search_entries(
            threat_level=args.threat_level,
            review_status=args.status,
            limit=args.limit
        )
        
        if not entries:
            print("No quarantined entries found")
            return 0
        
        print(f"Quarantined entries ({len(entries)}):")
        print("-" * 80)
        
        for entry in entries:
            print(f"ID: {entry.id}")
            print(f"Timestamp: {entry.timestamp}")
            print(f"Threat Level: {entry.threat_level}")
            print(f"Threats: {', '.join(entry.threats_detected)}")
            print(f"Status: {entry.review_status}")
            print(f"Source: {entry.source_file or 'N/A'}")
            print(f"Preview: {entry.original_content[:100]}...")
            print("-" * 80)
    
    elif args.quarantine_action == 'review':
        success = quarantine_manager.review_entry(args.entry_id, args.action, args.notes)
        if success:
            print(f"✓ Entry {args.entry_id} marked as {args.action}")
        else:
            print(f"✗ Failed to review entry {args.entry_id}")
            return 1
    
    elif args.quarantine_action == 'show':
        entry = quarantine_manager.database.get_entry(args.entry_id)
        if entry:
            print(f"Quarantine Entry: {entry.id}")
            print(f"Timestamp: {entry.timestamp}")
            print(f"Threat Level: {entry.threat_level}")
            print(f"Threats Detected: {', '.join(entry.threats_detected)}")
            print(f"Source File: {entry.source_file or 'N/A'}")
            print(f"Review Status: {entry.review_status}")
            print(f"Action Taken: {entry.action_taken}")
            print("\nOriginal Content:")
            print("-" * 40)
            print(entry.original_content)
            print("-" * 40)
            
            if entry.sanitized_content:
                print("\nSanitized Content:")
                print("-" * 40)
                print(entry.sanitized_content)
                print("-" * 40)
            
            print("\nThreat Details:")
            print(json.dumps(entry.details, indent=2))
        else:
            print(f"Entry not found: {args.entry_id}")
            return 1
    
    elif args.quarantine_action == 'export':
        success = quarantine_manager.export_entries(
            args.output_file,
            threat_level=args.threat_level,
            review_status=args.status,
            format=args.format
        )
        if success:
            print(f"✓ Quarantine data exported to: {args.output_file}")
        else:
            print(f"✗ Failed to export quarantine data")
            return 1
    
    return 0


def handle_config_command(args):
    """Handle configuration commands."""
    config_manager = SecurityConfigManager()
    
    if args.security_level:
        security_level = SecurityLevel(args.security_level)
        config_manager.load_security_level(security_level)
        print(f"✓ Security level set to: {args.security_level}")
    
    if args.load:
        if config_manager.load_config_from_file(args.load):
            print(f"✓ Configuration loaded from: {args.load}")
        else:
            print(f"✗ Failed to load configuration: {args.load}")
            return 1
    
    if args.save:
        if config_manager.save_config_to_file(args.save):
            print(f"✓ Configuration saved to: {args.save}")
        else:
            print(f"✗ Failed to save configuration: {args.save}")
            return 1
    
    if args.template:
        if config_manager.export_config_template(args.template):
            print(f"✓ Configuration template exported to: {args.template}")
        else:
            print(f"✗ Failed to export template: {args.template}")
            return 1
    
    if args.show:
        summary = config_manager.get_config_summary()
        print("Current Configuration:")
        print(json.dumps(summary, indent=2))
    
    if args.validate:
        issues = config_manager.validate_config()
        if issues:
            print("Configuration issues found:")
            for issue in issues:
                print(f"  - {issue}")
            return 1
        else:
            print("✓ Configuration is valid")
    
    if args.list_profiles:
        profiles = config_manager.list_available_profiles()
        print("Available configuration profiles:")
        for profile in profiles:
            print(f"  - {profile}")
    
    return 0


def handle_report_command(args):
    """Handle report generation."""
    processor = SecureTextProcessor()
    report = processor.generate_security_report(args.days)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            if args.format == 'yaml':
                import yaml
                yaml.dump(report, f, default_flow_style=False, indent=2)
            else:
                json.dump(report, f, indent=2, default=str)
        print(f"✓ Report saved to: {args.output}")
    else:
        if args.format == 'yaml':
            import yaml
            print(yaml.dump(report, default_flow_style=False, indent=2))
        else:
            print(json.dumps(report, indent=2, default=str))
    
    return 0


def handle_stats_command(args):
    """Handle statistics display."""
    processor = SecureTextProcessor()
    stats = processor.get_processing_statistics()
    
    print("Processing Statistics:")
    print(f"  Total processed: {stats['total_processed']}")
    print(f"  Clean content: {stats['clean_content']}")
    print(f"  Sanitized content: {stats['sanitized_content']}")
    print(f"  Quarantined content: {stats['quarantined_content']}")
    print(f"  Rejected content: {stats['rejected_content']}")
    
    if stats['total_processed'] > 0:
        print(f"  Success rate: {stats.get('success_rate', 0):.1f}%")
        print(f"  Quarantine rate: {stats.get('quarantine_rate', 0):.1f}%")
        print(f"  Rejection rate: {stats.get('rejection_rate', 0):.1f}%")
        print(f"  Avg processing time: {stats.get('avg_processing_time', 0):.3f}s")
    
    return 0


if __name__ == "__main__":
    exit(main())
