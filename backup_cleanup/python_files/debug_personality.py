#!/usr/bin/env python3
"""Debug script for personality saving."""

from custom_personality_manager import get_custom_personality_manager, CustomPersonality

def debug_personality_saving():
    """Debug personality saving issues."""
    print("🔍 Debugging personality saving...")
    
    manager = get_custom_personality_manager()
    print(f"Current personalities: {list(manager.custom_personalities.keys())}")
    
    # Create test personality
    personality = CustomPersonality(
        name='debug_test',
        description='Debug test personality',
        tags=['custom', 'debug']
    )
    
    print(f"Creating personality: {personality.name}")
    print(f"Tags: {personality.tags}")
    
    # Add personality
    result = manager.add_personality(personality)
    print(f"Add result: {result}")
    
    print(f"Personalities after add: {list(manager.custom_personalities.keys())}")
    
    # Check file content
    import json
    from pathlib import Path
    
    file_path = Path("custom_personalities.json")
    if file_path.exists():
        with open(file_path, 'r') as f:
            content = f.read()
        print(f"File content: {content}")
        
        try:
            data = json.loads(content)
            print(f"Parsed JSON: {data}")
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
    else:
        print("File does not exist")

if __name__ == "__main__":
    debug_personality_saving()
