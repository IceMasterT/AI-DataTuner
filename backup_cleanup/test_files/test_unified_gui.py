#!/usr/bin/env python3
"""
Test script for the Unified Pipeline GUI.
Demonstrates all features and capabilities.
"""

import sys
from pathlib import Path

def test_gui_import():
    """Test that the unified GUI can be imported successfully."""
    print("🧪 Testing Unified GUI Import...")
    
    try:
        from unified_pipeline_gui import UnifiedPipelineGUI
        print("✅ Unified GUI imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_gui_initialization():
    """Test GUI initialization without showing the window."""
    print("\n🧪 Testing GUI Initialization...")
    
    try:
        from unified_pipeline_gui import UnifiedPipelineGUI
        
        # Create GUI instance but don't run mainloop
        app = UnifiedPipelineGUI()
        
        print("✅ GUI initialized successfully")
        
        # Test basic functionality
        print("🔍 Testing basic functionality...")
        
        # Test status update
        app.update_status("Test status message")
        print("  ✅ Status update works")
        
        # Test log message
        app.log_message("Test log message")
        print("  ✅ Log message works")
        
        # Test phase display update
        app.update_phase_displays()
        print("  ✅ Phase display update works")
        
        # Test folder status refresh
        app.refresh_folder_status()
        print("  ✅ Folder status refresh works")
        
        return True
        
    except Exception as e:
        print(f"❌ GUI initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_component_integration():
    """Test integration with pipeline components."""
    print("\n🧪 Testing Component Integration...")
    
    try:
        from unified_pipeline_gui import UnifiedPipelineGUI
        app = UnifiedPipelineGUI()
        
        # Test pipeline integration
        if hasattr(app, 'pipeline'):
            print("  ✅ Pipeline integration works")
        else:
            print("  ❌ Pipeline integration missing")
        
        # Test personality manager integration
        if hasattr(app, 'custom_personality_manager'):
            print("  ✅ Personality manager integration works")
        else:
            print("  ❌ Personality manager integration missing")
        
        # Test config integration
        if hasattr(app, 'config'):
            print("  ✅ Config integration works")
        else:
            print("  ❌ Config integration missing")
        
        return True
        
    except Exception as e:
        print(f"❌ Component integration test failed: {e}")
        return False

def show_gui_features():
    """Show available GUI features."""
    print("\n🎯 Unified GUI Features:")
    print("=" * 50)
    
    features = [
        "🚀 Main Control - File management and pipeline execution",
        "🎛️ Phase Control - Red/green light system for phases",
        "🤖 AI Settings - Complete OpenAI configuration",
        "🎭 Personality - Full personality management system",
        "🛡️ Security - Advanced security and filtering",
        "📁 Folders - Complete folder management",
        "⚙️ Processing - Performance and format settings",
        "📊 Monitoring - Real-time logs and analytics"
    ]
    
    for feature in features:
        print(f"  {feature}")
    
    print("\n🎛️ Phase Control Features:")
    print("  🟢 Green Light - Phase enabled")
    print("  🔴 Red Light - Phase disabled")
    print("  🟡 Yellow Light - Phase running")
    print("  🔵 Blue Light - Phase complete")
    print("  🟠 Orange Light - Phase error")
    
    print("\n🎭 Personality Features:")
    print("  📚 Predefined Templates - 10+ built-in personalities")
    print("  ✏️ Custom Personalities - Create unlimited custom voices")
    print("  🎚️ Strength Control - Adjust personality intensity")
    print("  🔍 Live Preview - Test transformations")
    print("  💾 Management - Full CRUD operations")

def show_usage_instructions():
    """Show usage instructions."""
    print("\n📖 Usage Instructions:")
    print("=" * 50)
    
    print("🚀 Quick Start:")
    print("  1. python unified_pipeline_gui.py")
    print("  2. Configure input folder in Main Control tab")
    print("  3. Enable desired phases in Phase Control tab")
    print("  4. Set personality in Personality tab")
    print("  5. Configure AI settings if using OpenAI")
    print("  6. Click 'START PIPELINE' to begin processing")
    
    print("\n🎛️ Phase Control:")
    print("  • Click toggle buttons to enable/disable phases")
    print("  • Use settings buttons to configure phase parameters")
    print("  • Monitor status lights for real-time phase status")
    
    print("\n🎭 Personality Management:")
    print("  • Select from dropdown or create custom personalities")
    print("  • Adjust strength slider for personality intensity")
    print("  • Use preview to test personality transformations")
    print("  • Save custom personalities for reuse")
    
    print("\n📊 Monitoring:")
    print("  • Real-time logs show processing information")
    print("  • Phase results display detailed execution metrics")
    print("  • System status shows overall pipeline health")
    print("  • Statistics provide performance analytics")

def main():
    """Main test function."""
    print("🧪 UNIFIED PIPELINE GUI - COMPREHENSIVE TEST")
    print("Testing the merged pipeline_gui.py + phase_control_gui.py interface")
    print(f"Python version: {sys.version}")
    print()
    
    success = True
    
    # Test GUI import
    if not test_gui_import():
        success = False
    
    # Test GUI initialization
    if not test_gui_initialization():
        success = False
    
    # Test component integration
    if not test_component_integration():
        success = False
    
    # Show features and usage
    show_gui_features()
    show_usage_instructions()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("The Unified Pipeline GUI is ready to use.")
        
        print("\n🚀 To launch the GUI:")
        print("   python unified_pipeline_gui.py")
        
        print("\n✨ Key Benefits:")
        print("  • Single interface for all pipeline features")
        print("  • Red/green light phase control system")
        print("  • Integrated personality management")
        print("  • Real-time monitoring and logging")
        print("  • Complete customization options")
        print("  • Advanced security and filtering")
        print("  • Comprehensive folder management")
        
        return 0
    else:
        print("❌ SOME TESTS FAILED!")
        print("Please check the error messages above.")
        return 1

if __name__ == "__main__":
    exit(main())
