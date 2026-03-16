#!/usr/bin/env python3
"""
CLI tool for managing custom personalities.
Allows creating, editing, testing, and managing custom personality configurations.
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

from custom_personality_manager import get_custom_personality_manager, CustomPersonality
from personality_modifier import PersonalityModifier


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Custom Personality Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all personalities
  python personality_cli.py list

  # Create a new personality
  python personality_cli.py create "my_brand" "Professional but friendly, uses clear language"

  # Test a personality
  python personality_cli.py test "my_brand" "This is a sample text to transform"

  # Show personality details
  python personality_cli.py show "my_brand"

  # Delete a personality
  python personality_cli.py delete "my_brand"

  # Export personalities
  python personality_cli.py export personalities_backup.json

  # Import personalities
  python personality_cli.py import personalities_backup.json
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all custom personalities')
    list_parser.add_argument('--tag', help='Filter by tag')
    list_parser.add_argument('--detailed', action='store_true', help='Show detailed information')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new custom personality')
    create_parser.add_argument('name', help='Personality name')
    create_parser.add_argument('description', help='Personality description')
    create_parser.add_argument('--strength', type=float, default=0.7, help='Default strength (0.1-1.0)')
    create_parser.add_argument('--tags', nargs='+', default=['custom'], help='Tags for the personality')
    
    # Show command
    show_parser = subparsers.add_parser('show', help='Show personality details')
    show_parser.add_argument('name', help='Personality name')
    
    # Edit command
    edit_parser = subparsers.add_parser('edit', help='Edit an existing personality')
    edit_parser.add_argument('name', help='Personality name')
    edit_parser.add_argument('--description', help='New description')
    edit_parser.add_argument('--strength', type=float, help='New default strength')
    edit_parser.add_argument('--add-tags', nargs='+', help='Tags to add')
    edit_parser.add_argument('--remove-tags', nargs='+', help='Tags to remove')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a custom personality')
    delete_parser.add_argument('name', help='Personality name')
    delete_parser.add_argument('--force', action='store_true', help='Force deletion without confirmation')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test a personality with sample text')
    test_parser.add_argument('personality', help='Personality name or description')
    test_parser.add_argument('text', help='Sample text to transform')
    test_parser.add_argument('--strength', type=float, default=0.7, help='Personality strength (0.1-1.0)')
    test_parser.add_argument('--show-cost', action='store_true', help='Show cost information')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search personalities')
    search_parser.add_argument('query', help='Search query')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export personalities to file')
    export_parser.add_argument('file', help='Output file path')
    export_parser.add_argument('--include-env', action='store_true', help='Include env personalities')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import personalities from file')
    import_parser.add_argument('file', help='Input file path')
    import_parser.add_argument('--overwrite', action='store_true', help='Overwrite existing personalities')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show usage statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        if args.command == 'list':
            return handle_list_command(args)
        elif args.command == 'create':
            return handle_create_command(args)
        elif args.command == 'show':
            return handle_show_command(args)
        elif args.command == 'edit':
            return handle_edit_command(args)
        elif args.command == 'delete':
            return handle_delete_command(args)
        elif args.command == 'test':
            return handle_test_command(args)
        elif args.command == 'search':
            return handle_search_command(args)
        elif args.command == 'export':
            return handle_export_command(args)
        elif args.command == 'import':
            return handle_import_command(args)
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


def handle_list_command(args):
    """Handle the list command."""
    manager = get_custom_personality_manager()
    personalities = manager.custom_personalities
    
    if args.tag:
        personalities = {
            name: p for name, p in personalities.items()
            if args.tag in p.tags
        }
    
    if not personalities:
        print("No custom personalities found.")
        return 0
    
    print(f"📚 Custom Personalities ({len(personalities)} found):")
    print("=" * 50)
    
    for name, personality in personalities.items():
        print(f"\n🎭 {name}")
        
        if args.detailed:
            print(f"   Description: {personality.description}")
            print(f"   Strength: {personality.strength}")
            print(f"   Tags: {', '.join(personality.tags)}")
            print(f"   Usage: {personality.usage_count} times")
            if personality.last_used:
                print(f"   Last used: {personality.last_used}")
        else:
            # Truncate long descriptions
            desc = personality.description
            if len(desc) > 60:
                desc = desc[:57] + "..."
            print(f"   {desc}")
            print(f"   Tags: {', '.join(personality.tags[:3])}")
    
    return 0


def handle_create_command(args):
    """Handle the create command."""
    manager = get_custom_personality_manager()
    
    # Check if personality already exists
    if manager.get_personality(args.name):
        print(f"❌ Personality '{args.name}' already exists. Use 'edit' to modify it.")
        return 1
    
    # Create new personality
    personality = CustomPersonality(
        name=args.name,
        description=args.description,
        strength=args.strength,
        tags=args.tags
    )
    
    if manager.add_personality(personality):
        print(f"✅ Created personality '{args.name}'")
        print(f"   Description: {args.description}")
        print(f"   Strength: {args.strength}")
        print(f"   Tags: {', '.join(args.tags)}")
        return 0
    else:
        print(f"❌ Failed to create personality '{args.name}'")
        return 1


def handle_show_command(args):
    """Handle the show command."""
    manager = get_custom_personality_manager()
    personality = manager.get_personality(args.name)
    
    if not personality:
        print(f"❌ Personality '{args.name}' not found.")
        return 1
    
    print(f"🎭 Personality: {personality.name}")
    print("=" * 50)
    print(f"Description: {personality.description}")
    print(f"Default Strength: {personality.strength}")
    print(f"Preserve Meaning: {personality.preserve_meaning}")
    print(f"Tags: {', '.join(personality.tags)}")
    print(f"Created: {personality.created_date}")
    print(f"Usage Count: {personality.usage_count}")
    
    if personality.last_used:
        print(f"Last Used: {personality.last_used}")
    
    return 0


def handle_edit_command(args):
    """Handle the edit command."""
    manager = get_custom_personality_manager()
    
    if not manager.get_personality(args.name):
        print(f"❌ Personality '{args.name}' not found.")
        return 1
    
    updates = {}
    
    if args.description:
        updates['description'] = args.description
    
    if args.strength is not None:
        updates['strength'] = args.strength
    
    if args.add_tags:
        personality = manager.get_personality(args.name)
        new_tags = list(set(personality.tags + args.add_tags))
        updates['tags'] = new_tags
    
    if args.remove_tags:
        personality = manager.get_personality(args.name)
        new_tags = [tag for tag in personality.tags if tag not in args.remove_tags]
        updates['tags'] = new_tags
    
    if not updates:
        print("❌ No updates specified.")
        return 1
    
    if manager.update_personality(args.name, **updates):
        print(f"✅ Updated personality '{args.name}'")
        for key, value in updates.items():
            print(f"   {key}: {value}")
        return 0
    else:
        print(f"❌ Failed to update personality '{args.name}'")
        return 1


def handle_delete_command(args):
    """Handle the delete command."""
    manager = get_custom_personality_manager()
    
    if not manager.get_personality(args.name):
        print(f"❌ Personality '{args.name}' not found.")
        return 1
    
    if not args.force:
        response = input(f"Are you sure you want to delete '{args.name}'? (y/N): ")
        if response.lower() != 'y':
            print("❌ Deletion cancelled.")
            return 1
    
    if manager.delete_personality(args.name):
        print(f"✅ Deleted personality '{args.name}'")
        return 0
    else:
        print(f"❌ Failed to delete personality '{args.name}'")
        return 1


def handle_test_command(args):
    """Handle the test command."""
    print(f"🧪 Testing personality: {args.personality}")
    print(f"📝 Sample text: {args.text}")
    print(f"🎚️ Strength: {args.strength}")
    print("-" * 50)
    
    try:
        modifier = PersonalityModifier()
        result = modifier.apply_personality(args.text, args.personality, args.strength)
        
        print(f"✅ Transformation successful!")
        print(f"📄 Original: {result.original_text}")
        print(f"🎭 Modified: {result.modified_text}")
        print(f"📊 Confidence: {result.confidence:.2f}")
        
        if args.show_cost:
            print(f"💰 Cost: ${result.cost:.6f}")
            print(f"🔢 Tokens: {result.tokens_used}")
        
        if result.improvements:
            print(f"🔧 Improvements: {', '.join(result.improvements)}")
        
        return 0
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 1


def handle_search_command(args):
    """Handle the search command."""
    manager = get_custom_personality_manager()
    suggestions = manager.get_personality_suggestions(args.query)
    
    if not suggestions:
        print(f"No personalities found matching '{args.query}'")
        return 0
    
    print(f"🔍 Search results for '{args.query}':")
    print("=" * 50)
    
    for name in suggestions:
        personality = manager.get_personality(name)
        print(f"\n🎭 {name}")
        print(f"   {personality.description}")
        print(f"   Tags: {', '.join(personality.tags)}")
    
    return 0


def handle_export_command(args):
    """Handle the export command."""
    manager = get_custom_personality_manager()
    
    if manager.export_personalities(args.file):
        count = len(manager.custom_personalities)
        print(f"✅ Exported {count} personalities to {args.file}")
        return 0
    else:
        print(f"❌ Failed to export personalities to {args.file}")
        return 1


def handle_import_command(args):
    """Handle the import command."""
    if not Path(args.file).exists():
        print(f"❌ File not found: {args.file}")
        return 1
    
    manager = get_custom_personality_manager()
    imported_count = manager.import_personalities(args.file, args.overwrite)
    
    if imported_count > 0:
        print(f"✅ Imported {imported_count} personalities from {args.file}")
        return 0
    else:
        print(f"❌ No personalities imported from {args.file}")
        return 1


def handle_stats_command(args):
    """Handle the stats command."""
    manager = get_custom_personality_manager()
    stats = manager.get_usage_statistics()
    
    print("📊 Personality Usage Statistics")
    print("=" * 50)
    print(f"Total Personalities: {stats['total_personalities']}")
    print(f"Environment Personalities: {stats['env_personalities']}")
    print(f"File Personalities: {stats['file_personalities']}")
    
    if stats['most_used']:
        print(f"Most Used: {stats['most_used']} ({stats['most_used_count']} times)")
    
    print("\n📈 Individual Usage:")
    for name, data in stats['personalities'].items():
        print(f"  {name}: {data['usage_count']} times")
        if data['last_used']:
            print(f"    Last used: {data['last_used']}")
    
    return 0


if __name__ == "__main__":
    exit(main())
