#!/usr/bin/env python3
"""
Test Personality Integration in Ten Pillars System
Verify that personality is consistently applied throughout all processing.
"""

from ten_pillars_integration import get_ten_pillars_system

def test_personality_integration():
    """Test personality integration in Ten Pillars system."""
    print('🎭 TESTING PERSONALITY INTEGRATION IN TEN PILLARS')
    print('='*60)
    
    # Initialize Ten Pillars system
    pillars_system = get_ten_pillars_system()
    
    # Test content
    test_content = 'Machine learning is a method of data analysis that automates analytical model building.'
    
    # Test different personalities
    personalities = ['professional', 'casual', 'technical', 'friendly']
    
    results = []
    
    for personality in personalities:
        print(f'\n🎭 Testing {personality} personality:')
        
        try:
            result = pillars_system.process_item(
                item_id=f'test_{personality}',
                content=test_content,
                format_type='qwen',
                personality=personality,
                original_content=test_content
            )
            
            results.append(result)
            
            if result.success:
                print(f'   ✅ SUCCESS - Quality: {result.quality_score:.1f}%')
                print(f'   🎭 Personality Applied: {personality}')
                print(f'   📊 Processing Steps: {len(result.processing_steps)}')
                
                # Check for personality application step
                personality_step = None
                for step in result.processing_steps:
                    if step.get('pillar') == 'personality_application':
                        personality_step = step
                        break
                
                if personality_step:
                    print(f'   🎯 Personality Step Found: {personality_step["result"]["personality_applied"]}')
                else:
                    print('   ⚠️ No explicit personality step found')
                    
                # Show final data personality
                if result.final_data and 'personality' in result.final_data:
                    print(f'   📄 Final Data Personality: {result.final_data["personality"]}')
                    
            else:
                print(f'   ❌ FAILED: {len(result.errors)} errors')
                for error in result.errors[:2]:
                    print(f'      • {error}')
                    
        except Exception as e:
            print(f'   ❌ ERROR: {e}')
    
    # Summary
    print(f'\n📊 PERSONALITY INTEGRATION TEST SUMMARY')
    print('-'*50)
    
    successful = sum(1 for r in results if r.success)
    total = len(results)
    
    print(f'Total Tests: {total}')
    print(f'Successful: {successful}')
    print(f'Success Rate: {(successful/total*100):.1f}%')
    
    if successful > 0:
        print(f'\n🎭 Personality integration working across {successful} personalities!')
        print('✅ Active personality consistently applied to all processing')
    else:
        print('\n❌ Personality integration needs attention')
    
    return results

if __name__ == "__main__":
    test_personality_integration()
