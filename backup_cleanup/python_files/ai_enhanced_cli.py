#!/usr/bin/env python3
"""
AI-Enhanced Command Line Interface for text processing with OpenAI integration.
Provides advanced AI-powered classification, enhancement, and optimization features.
"""

import argparse
import json
import sys
import os
from pathlib import Path
from datetime import datetime

from ai_enhanced_processor import AIEnhancedTextProcessor, ProcessingConfig
from ai_config import AIConfigManager, ProcessingMode, AIModel
from cost_optimizer import CostOptimizer
from openai_integration import OpenAIConfig


def normalize_mode_value(value: str) -> str:
    """Accept both hyphenated and underscored mode values."""
    return value.replace("-", "_") if value else value


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AI-Enhanced Text Processing System with OpenAI Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic AI-enhanced processing
  python ai_enhanced_cli.py process input.txt --ai-classification

  # Full AI enhancement with content improvement
  python ai_enhanced_cli.py process input.txt --ai-classification --content-enhancement

  # Cost-optimized processing
  python ai_enhanced_cli.py process input.txt --mode cost-optimized

  # Quality-optimized processing
  python ai_enhanced_cli.py process input.txt --mode quality-optimized --model gpt-4

  # Batch processing with AI
  python ai_enhanced_cli.py batch-process data/ --ai-classification --daily-limit 5.0

  # Cost analysis and optimization
  python ai_enhanced_cli.py cost-analysis --optimize

  # AI configuration management
  python ai_enhanced_cli.py config --mode balanced --save-profile my_profile
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Process command
    process_parser = subparsers.add_parser(
        "process", help="Process single file with AI enhancement"
    )
    process_parser.add_argument("input", help='Input file or text (use "-" for stdin)')
    process_parser.add_argument("-o", "--output", help="Output file path")
    process_parser.add_argument(
        "-f", "--format", default="qwen", help="Output conversation format"
    )

    # AI features
    process_parser.add_argument(
        "--ai-classification",
        action="store_true",
        help="Enable AI-powered classification",
    )
    process_parser.add_argument(
        "--content-enhancement",
        action="store_true",
        help="Enable AI content enhancement",
    )
    process_parser.add_argument(
        "--model", choices=[m.value for m in AIModel], help="OpenAI model to use"
    )
    mode_choices = sorted(
        set(
            [m.value for m in ProcessingMode]
            + [m.value.replace("_", "-") for m in ProcessingMode]
        )
    )

    process_parser.add_argument(
        "--mode", choices=mode_choices, default="balanced", help="Processing mode"
    )

    # Cost controls
    process_parser.add_argument(
        "--daily-limit", type=float, default=10.0, help="Daily cost limit in USD"
    )
    process_parser.add_argument(
        "--no-cache", action="store_true", help="Disable response caching"
    )

    # Security
    process_parser.add_argument(
        "--security-level",
        choices=["permissive", "balanced", "strict", "paranoid"],
        default="balanced",
        help="Security level",
    )
    process_parser.add_argument(
        "--no-security", action="store_true", help="Disable security filtering"
    )

    # Batch process command
    batch_parser = subparsers.add_parser(
        "batch-process", help="Process multiple files with AI"
    )
    batch_parser.add_argument("input_dir", help="Input directory")
    batch_parser.add_argument("-o", "--output-dir", help="Output directory")
    batch_parser.add_argument(
        "-f", "--format", default="qwen", help="Output conversation format"
    )
    batch_parser.add_argument("--ai-classification", action="store_true")
    batch_parser.add_argument("--content-enhancement", action="store_true")
    batch_parser.add_argument("--model", choices=[m.value for m in AIModel])
    batch_parser.add_argument("--mode", choices=mode_choices, default="balanced")
    batch_parser.add_argument("--daily-limit", type=float, default=10.0)
    batch_parser.add_argument(
        "--batch-size", type=int, default=10, help="Batch size for processing"
    )
    batch_parser.add_argument("--report", help="Generate processing report file")

    # Cost analysis command
    cost_parser = subparsers.add_parser(
        "cost-analysis", help="Analyze and optimize costs"
    )
    cost_parser.add_argument(
        "--days", type=int, default=7, help="Analysis period in days"
    )
    cost_parser.add_argument(
        "--optimize", action="store_true", help="Apply optimization recommendations"
    )
    cost_parser.add_argument("--report", help="Save cost report to file")

    # Configuration command
    config_parser = subparsers.add_parser("config", help="Manage AI configuration")
    config_parser.add_argument(
        "--mode", choices=mode_choices, help="Set processing mode"
    )
    config_parser.add_argument(
        "--model", choices=[m.value for m in AIModel], help="Set default model"
    )
    config_parser.add_argument("--daily-limit", type=float, help="Set daily cost limit")
    config_parser.add_argument(
        "--show", action="store_true", help="Show current configuration"
    )
    config_parser.add_argument("--save-profile", help="Save current config as profile")
    config_parser.add_argument("--load-profile", help="Load configuration profile")
    config_parser.add_argument(
        "--list-models", action="store_true", help="List available models"
    )
    config_parser.add_argument(
        "--validate-key", action="store_true", help="Validate OpenAI API key"
    )

    # Enhancement command
    enhance_parser = subparsers.add_parser(
        "enhance", help="Enhance content quality with AI"
    )
    enhance_parser.add_argument("input", help="Input file or text")
    enhance_parser.add_argument("-o", "--output", help="Output file path")
    enhance_parser.add_argument(
        "--type",
        choices=["grammar", "clarity", "structure", "completeness"],
        default="auto",
        help="Enhancement type",
    )
    enhance_parser.add_argument("--model", choices=[m.value for m in AIModel])
    enhance_parser.add_argument(
        "--preserve-meaning",
        action="store_true",
        default=True,
        help="Strictly preserve original meaning",
    )

    # Statistics command
    stats_parser = subparsers.add_parser(
        "stats", help="Show processing and cost statistics"
    )
    stats_parser.add_argument(
        "--detailed", action="store_true", help="Show detailed statistics"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Check for OpenAI API key
    if args.command in ["process", "batch-process", "enhance"] and not os.getenv(
        "OPENAI_API_KEY"
    ):
        print(
            "Warning: OPENAI_API_KEY environment variable not set. AI features will be disabled."
        )

    try:
        if args.command == "process":
            return handle_process_command(args)
        elif args.command == "batch-process":
            return handle_batch_process_command(args)
        elif args.command == "cost-analysis":
            return handle_cost_analysis_command(args)
        elif args.command == "config":
            return handle_config_command(args)
        elif args.command == "enhance":
            return handle_enhance_command(args)
        elif args.command == "stats":
            return handle_stats_command(args)
        else:
            print(f"Unknown command: {args.command}")
            return 1

    except Exception as e:
        print(f"Error: {e}")
        return 1


def handle_process_command(args):
    """Handle single file processing with AI enhancement."""
    # Create processing configuration
    config = ProcessingConfig(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=args.model or "gpt-4o",
        daily_cost_limit=args.daily_limit,
        enable_ai_classification=args.ai_classification,
        enable_content_enhancement=args.content_enhancement,
        enable_security_filtering=not args.no_security,
        security_level=args.security_level,
        enable_caching=not args.no_cache,
    )

    # Apply processing mode
    if args.mode != "balanced":
        config_manager = AIConfigManager()
        config_manager.load_mode(ProcessingMode(normalize_mode_value(args.mode)))
        mode_config = config_manager.current_config

        # Update config with mode settings
        config.enable_ai_classification = mode_config.enable_ai_classification
        config.enable_content_enhancement = mode_config.enable_content_enhancement
        config.openai_model = args.model or mode_config.classification_model
        config.daily_cost_limit = mode_config.daily_cost_limit

    # Create processor
    processor = AIEnhancedTextProcessor(config, args.format)

    # Get input text
    if args.input == "-":
        text = sys.stdin.read()
        source_file = None
    else:
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                text = f.read()
            source_file = args.input
        except FileNotFoundError:
            print(f"Error: File not found: {args.input}")
            return 1

    # Process text
    print("🤖 Processing with AI enhancement...")
    result = processor.process_text(text, source_file)

    # Handle result
    if result.success:
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(result.processed_text)
            print(f"✅ Processed successfully: {args.output}")
        else:
            print(result.processed_text)

        # Show processing details
        print(f"\n📊 Processing Details:")
        print(
            f"  Classification: {result.classification_method} (confidence: {result.classification_confidence:.2f})"
        )
        print(
            f"  Enhancement: {'Applied' if result.enhancement_applied else 'Not needed'}"
        )
        print(f"  Security: {result.security_action}")
        print(f"  Cost: ${result.total_cost:.4f}")
        print(f"  Tokens: {result.total_tokens}")
        print(f"  Time: {result.processing_time:.2f}s")

        if result.warnings:
            print(f"\n⚠️  Warnings:")
            for warning in result.warnings:
                print(f"  - {warning}")

    else:
        print("❌ Processing failed:")
        for error in result.errors:
            print(f"  - {error}")
        return 1

    return 0


def handle_batch_process_command(args):
    """Handle batch processing with AI enhancement."""
    input_path = Path(args.input_dir)

    if not input_path.exists():
        print(f"Error: Input directory not found: {args.input_dir}")
        return 1

    # Create processing configuration
    config = ProcessingConfig(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        daily_cost_limit=args.daily_limit,
        enable_ai_classification=args.ai_classification,
        enable_content_enhancement=args.content_enhancement,
        batch_size=args.batch_size,
    )

    # Apply processing mode
    if args.mode != "balanced":
        config_manager = AIConfigManager()
        config_manager.load_mode(ProcessingMode(normalize_mode_value(args.mode)))
        mode_config = config_manager.current_config

        config.enable_ai_classification = mode_config.enable_ai_classification
        config.enable_content_enhancement = mode_config.enable_content_enhancement
        config.openai_model = args.model or mode_config.classification_model

    # Create processor
    processor = AIEnhancedTextProcessor(config, args.format)

    # Find input files
    input_files = list(input_path.glob("*.txt")) + list(input_path.glob("*.md"))
    input_files = [str(f) for f in input_files]

    if not input_files:
        print("No input files found")
        return 1

    print(f"🤖 Processing {len(input_files)} files with AI enhancement...")

    # Read all files
    texts = []
    for file_path in input_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                texts.append(f.read())
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
            texts.append("")

    # Process files
    results = processor.batch_process(texts, input_files)

    # Save results
    if args.output_dir:
        output_path = Path(args.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for i, (result, input_file) in enumerate(zip(results, input_files)):
            if result.success:
                input_name = Path(input_file).stem
                output_file = output_path / f"{input_name}_ai_enhanced.txt"

                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(result.processed_text)

    # Print summary
    successful = sum(1 for r in results if r.success)
    total_cost = sum(r.total_cost for r in results)
    total_tokens = sum(r.total_tokens for r in results)

    print(f"\n📊 Batch Processing Complete:")
    print(f"  Total files: {len(results)}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {len(results) - successful}")
    print(f"  Total cost: ${total_cost:.4f}")
    print(f"  Total tokens: {total_tokens}")

    # Generate report
    if args.report:
        report = processor.get_processing_report()
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"  Report saved: {args.report}")

    return 0 if successful == len(results) else 1


def handle_cost_analysis_command(args):
    """Handle cost analysis and optimization."""
    optimizer = CostOptimizer()

    print("💰 Analyzing AI usage costs...")

    # Get optimization report
    report = optimizer.get_optimization_report()

    print(f"\n📊 Cost Summary (Last {args.days} days):")
    cost_summary = report["cost_summary"]
    print(f"  Total cost: ${cost_summary['total_cost']:.2f}")
    print(f"  Total requests: {cost_summary['total_requests']}")
    print(f"  Average daily cost: ${cost_summary['average_daily_cost']:.2f}")
    print(
        f"  Cost per request: ${cost_summary['total_cost'] / max(1, cost_summary['total_requests']):.4f}"
    )

    print(f"\n🎯 Cache Performance:")
    cache_perf = report["cache_performance"]["current_session"]
    print(f"  Hit rate: {cache_perf['hit_rate']:.1%}")
    print(f"  Hits: {cache_perf['hits']}")
    print(f"  Misses: {cache_perf['misses']}")

    print(f"\n💡 Optimization Recommendations:")
    for rec in report["recommendations"]:
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        print(f"  {priority_emoji.get(rec['priority'], '⚪')} {rec['description']}")
        print(f"     Potential savings: ${rec['potential_savings']:.2f}")

    # Apply optimizations if requested
    if args.optimize:
        print(f"\n🔧 Applying optimizations...")
        for rec in report["recommendations"]:
            if rec["priority"] in ["high", "medium"]:
                # Create recommendation object (simplified)
                from cost_optimizer import OptimizationRecommendation

                recommendation = OptimizationRecommendation(
                    type=rec["type"],
                    description=rec["description"],
                    potential_savings=rec["potential_savings"],
                    implementation_effort="low",
                    priority=rec["priority"],
                )

                result = optimizer.implement_optimization(recommendation)
                if result["implemented"]:
                    print(f"  ✅ {rec['type']}: {result['details']}")
                else:
                    print(f"  ⚠️  {rec['type']}: {result['details']}")

    # Save report if requested
    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n📄 Report saved: {args.report}")

    return 0


def handle_config_command(args):
    """Handle AI configuration management."""
    config_manager = AIConfigManager()

    if args.mode:
        config_manager.load_mode(ProcessingMode(normalize_mode_value(args.mode)))
        print(f"✅ Loaded {args.mode} processing mode")

    if args.model:
        config_manager.current_config.classification_model = args.model
        config_manager.current_config.enhancement_model = args.model
        print(f"✅ Set model to {args.model}")

    if args.daily_limit:
        config_manager.current_config.daily_cost_limit = args.daily_limit
        print(f"✅ Set daily limit to ${args.daily_limit}")

    if args.save_profile:
        success = config_manager.create_custom_profile(args.save_profile)
        if success:
            print(f"✅ Saved profile: {args.save_profile}")
        else:
            print(f"❌ Failed to save profile: {args.save_profile}")

    if args.load_profile:
        profile_file = f"config/ai_profile_{args.load_profile}.yaml"
        success = config_manager.load_config_from_file(profile_file)
        if success:
            print(f"✅ Loaded profile: {args.load_profile}")
        else:
            print(f"❌ Failed to load profile: {args.load_profile}")

    if args.list_models:
        models = config_manager.list_available_models()
        print("\n🤖 Available Models:")
        for model in models:
            print(f"  {model['name']}")
            print(f"    Cost: ${model['cost_per_1k_total']:.4f}/1K tokens")
            print(f"    Context: {model['context_window']:,} tokens")
            print(f"    Recommended for: {', '.join(model['recommended_for'])}")
            print()

    if args.validate_key:
        is_valid = config_manager.validate_api_key()
        if is_valid:
            print("✅ OpenAI API key is valid")
        else:
            print("❌ OpenAI API key is invalid or not set")

    if args.show:
        summary = config_manager.get_config_summary()
        print("\n⚙️  Current Configuration:")
        print(json.dumps(summary, indent=2, default=str))

    return 0


def handle_enhance_command(args):
    """Handle content enhancement."""
    from content_enhancer import AIContentEnhancer, EnhancementType
    from openai_integration import OpenAIConfig

    # Create enhancer
    openai_config = OpenAIConfig(
        api_key=os.getenv("OPENAI_API_KEY"), model=args.model or "gpt-4o"
    )
    enhancer = AIContentEnhancer(openai_config)

    # Get input text
    if args.input == "-":
        text = sys.stdin.read()
    else:
        with open(args.input, "r", encoding="utf-8") as f:
            text = f.read()

    # Enhance content
    if args.type == "auto":
        result = enhancer.auto_enhance(text)
    else:
        enhancement_type = EnhancementType(args.type)
        result = enhancer.enhance_content(text, enhancement_type, args.preserve_meaning)

    # Output result
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result.enhanced_text)
        print(f"✅ Enhanced content saved: {args.output}")
    else:
        print(result.enhanced_text)

    # Show enhancement details
    print(f"\n📊 Enhancement Details:")
    print(f"  Type: {result.enhancement_type.value}")
    print(f"  Quality improvement: {result.quality_improvement:.2f}")
    print(f"  Cost: ${result.cost:.4f}")
    print(f"  Improvements: {', '.join(result.improvements_made)}")

    return 0


def handle_stats_command(args):
    """Handle statistics display."""
    from cost_optimizer import CostOptimizer

    optimizer = CostOptimizer()
    report = optimizer.get_optimization_report()

    print("📊 AI Processing Statistics")
    print("=" * 40)

    cost_summary = report["cost_summary"]
    print(f"Cost Summary (Last 7 days):")
    print(f"  Total cost: ${cost_summary['total_cost']:.2f}")
    print(f"  Total requests: {cost_summary['total_requests']}")
    print(f"  Total tokens: {cost_summary['total_tokens']:,}")
    print(
        f"  Average cost/request: ${cost_summary['total_cost'] / max(1, cost_summary['total_requests']):.4f}"
    )

    if args.detailed:
        print(f"\nModel Breakdown:")
        for model, data in cost_summary.get("model_breakdown", {}).items():
            print(f"  {model}:")
            print(f"    Cost: ${data['cost']:.2f}")
            print(f"    Requests: {data['requests']}")
            print(f"    Tokens: {data['tokens']:,}")

        cache_perf = report["cache_performance"]
        print(f"\nCache Performance:")
        print(f"  Hit rate: {cache_perf['current_session']['hit_rate']:.1%}")
        print(f"  Total entries: {cache_perf['overall'].get('total_entries', 0)}")
        print(f"  Cost saved: ${cache_perf['overall'].get('total_cost_cached', 0):.2f}")

    return 0


if __name__ == "__main__":
    exit(main())
