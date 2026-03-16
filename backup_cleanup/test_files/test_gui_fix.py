#!/usr/bin/env python3
"""
Test script to verify the GUI status_bar fix.
"""

import sys
import traceback

def test_gui_initialization():
    """Test that the GUI initializes without status_bar errors."""
    try:
        print("🧪 Testing GUI initialization...")
        
        from pipeline_gui import PipelineGUI
        
        print("✅ GUI class imported successfully")
        
        # Create GUI instance (but don't run mainloop)
        app = PipelineGUI()
        
        print("✅ GUI instance created successfully")
        
        # Test status update
        app.update_status("Test status message")
        
        print("✅ Status update works correctly")
        
        # Check that status_bar exists
        if hasattr(app, 'status_bar'):
            print("✅ Status bar created successfully")
            print(f"   Status bar text: {app.status_bar.cget('text')}")
        else:
            print("⚠️  Status bar not yet created (this is expected during initialization)")
        
        # Test personality options loading
        if hasattr(app, 'personality_options'):
            print(f"✅ Personality options loaded: {len(app.personality_options)} options")
            print(f"   Available options: {app.personality_options[:5]}...")
        
        print("\n🎉 All tests passed! GUI should work correctly now.")
        return True
        
    except Exception as e:
        print(f"❌ Error during GUI test: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False

def test_custom_personality_integration():
    """Test custom personality integration."""
    try:
        print("\n🧪 Testing custom personality integration...")
        
        from custom_personality_manager import get_custom_personality_manager
        
        manager = get_custom_personality_manager()
        print("✅ Custom personality manager loaded")
        
        personalities = manager.list_personalities()
        print(f"✅ Found {len(personalities)} custom personalities")
        
        if personalities:
            print(f"   Custom personalities: {personalities}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during custom personality test: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🔧 GUI Fix Verification Tests")
    print("=" * 50)
    
    success = True
    
    # Test GUI initialization
    if not test_gui_initialization():
        success = False
    
    # Test custom personality integration
    if not test_custom_personality_integration():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed! The GUI is ready to use.")
        print("\n🚀 To start the GUI:")
        print("   python pipeline_gui.py")
        print("\n🎭 To manage personalities via CLI:")
        print("   python personality_cli.py list")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
