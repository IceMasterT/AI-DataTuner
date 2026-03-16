#!/usr/bin/env python3
"""
Test script to verify personality saving functionality.
"""

def test_personality_save():
    """Test saving a custom personality."""
    print("🧪 Testing Custom Personality Save Functionality")
    
    try:
        from custom_personality_manager import CustomPersonalityManager, CustomPersonality
        
        # Initialize manager
        manager = CustomPersonalityManager()
        print("✅ Custom personality manager initialized")
        
        # Create a test personality
        test_personality = CustomPersonality(
            name="test_personality",
            description="This is a test personality for validation purposes. It should be friendly and helpful while maintaining professionalism.",
            strength=0.8,
            preserve_meaning=True,
            tags=["test", "validation", "friendly"]
        )
        
        print(f"📝 Created test personality: {test_personality.name}")
        print(f"   Description: {test_personality.description[:50]}...")
        print(f"   Strength: {test_personality.strength}")
        print(f"   Tags: {test_personality.tags}")
        
        # Test save_personality method
        print("\n🔄 Testing save_personality method...")
        result = manager.save_personality(test_personality)
        
        if result:
            print("✅ save_personality method works correctly")
        else:
            print("❌ save_personality method failed")
            return False
        
        # Verify the personality was saved
        print("\n🔍 Verifying personality was saved...")
        saved_personalities = manager.list_personalities()
        
        if "test_personality" in saved_personalities:
            print("✅ Personality found in saved personalities list")
        else:
            print("❌ Personality not found in saved personalities list")
            return False
        
        # Test retrieval
        print("\n📖 Testing personality retrieval...")
        retrieved_personality = manager.get_personality("test_personality")
        
        if retrieved_personality:
            print("✅ Personality retrieved successfully")
            print(f"   Name: {retrieved_personality.name}")
            print(f"   Description: {retrieved_personality.description[:50]}...")
            print(f"   Strength: {retrieved_personality.strength}")
            print(f"   Tags: {retrieved_personality.tags}")
        else:
            print("❌ Failed to retrieve saved personality")
            return False
        
        # Test updating the personality
        print("\n🔄 Testing personality update...")
        updated_personality = CustomPersonality(
            name="test_personality",
            description="Updated test personality with new description for validation.",
            strength=0.9,
            preserve_meaning=True,
            tags=["test", "validation", "updated"]
        )
        
        update_result = manager.save_personality(updated_personality)
        
        if update_result:
            print("✅ Personality update successful")
            
            # Verify update
            updated_retrieved = manager.get_personality("test_personality")
            if updated_retrieved and updated_retrieved.strength == 0.9:
                print("✅ Update verified - strength changed to 0.9")
            else:
                print("❌ Update verification failed")
                return False
        else:
            print("❌ Personality update failed")
            return False
        
        # Clean up - delete test personality
        print("\n🧹 Cleaning up test personality...")
        delete_result = manager.delete_personality("test_personality")
        
        if delete_result:
            print("✅ Test personality deleted successfully")
        else:
            print("⚠️ Could not delete test personality (may be env personality)")
        
        print("\n🎉 All personality save tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_gui_integration():
    """Test the specific scenario from the GUI."""
    print("\n🖥️ Testing GUI Integration Scenario")
    
    try:
        from custom_personality_manager import CustomPersonalityManager, CustomPersonality
        
        # Initialize manager (as GUI would)
        manager = CustomPersonalityManager()
        print("✅ Manager initialized for GUI test")
        
        # Simulate GUI creating a personality
        gui_personality = CustomPersonality(
            name="gui_test_personality",
            description="This personality was created through the GUI interface for testing purposes.",
            tags=["gui", "test", "user-created"]
        )
        
        print(f"📝 GUI created personality: {gui_personality.name}")
        
        # This is the exact call that was failing in the GUI
        try:
            manager.save_personality(gui_personality)
            print("✅ GUI save_personality call successful")
        except AttributeError as e:
            print(f"❌ GUI save_personality call failed: {e}")
            return False
        
        # Verify it was saved
        if "gui_test_personality" in manager.list_personalities():
            print("✅ GUI personality saved and listed correctly")
        else:
            print("❌ GUI personality not found in list")
            return False
        
        # Clean up
        manager.delete_personality("gui_test_personality")
        print("✅ GUI test personality cleaned up")
        
        return True
        
    except Exception as e:
        print(f"❌ GUI integration test failed: {e}")
        return False

def main():
    """Run personality save tests."""
    print("🧪 CUSTOM PERSONALITY SAVE - FUNCTIONALITY TEST")
    print("Testing the save_personality method that was missing")
    
    tests = [
        ("Basic Personality Save", test_personality_save),
        ("GUI Integration", test_gui_integration)
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        results[test_name] = test_func()
    
    print(f"\n{'='*60}")
    print(" TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ save_personality method is now working correctly")
        print("✅ GUI personality saving functionality restored")
        return 0
    else:
        print(f"\n❌ {total-passed} TESTS FAILED!")
        return 1

if __name__ == "__main__":
    exit(main())
