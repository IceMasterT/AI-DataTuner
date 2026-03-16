#!/usr/bin/env python3
"""
Simple verification of the phase-controlled pipeline folder structure.
"""

def verify_pipeline_configuration():
    """Verify that the pipeline is configured with correct folder structure."""
    print("🔍 Verifying Pipeline Folder Configuration")
    print("=" * 50)
    
    try:
        from phase_controlled_pipeline import get_pipeline
        
        pipeline = get_pipeline()
        
        print("📋 Phase Configuration:")
        print()
        
        expected_flow = [
            ("phase1_sanitization", "Input Parsing & Sanitization", "input", "Phase 1"),
            ("phase2_chunking", "Chunking & Fact Extraction", "Phase 1", "Phase 2"),
            ("phase3_personality", "Personality Prompting & Formatting", "Phase 2", "Phase 3"),
            ("phase4_quality", "Quality Scoring & Assessment", "Phase 3", "Phase 4")
        ]
        
        all_correct = True
        
        for phase_id, phase_name, expected_input, expected_output in expected_flow:
            if phase_id in pipeline.phases:
                config = pipeline.phases[phase_id]
                actual_input = config.input_folder
                actual_output = config.output_folder
                
                input_correct = actual_input == expected_input
                output_correct = actual_output == expected_output
                
                print(f"🎛️ {phase_name}")
                print(f"   Input:  {actual_input} {'✅' if input_correct else '❌'}")
                print(f"   Output: {actual_output} {'✅' if output_correct else '❌'}")
                
                if not input_correct:
                    print(f"   Expected input: {expected_input}")
                    all_correct = False
                
                if not output_correct:
                    print(f"   Expected output: {expected_output}")
                    all_correct = False
                
                print()
            else:
                print(f"❌ Phase not found: {phase_id}")
                all_correct = False
        
        if all_correct:
            print("✅ All folder configurations are CORRECT!")
            print()
            print("📁 Data Flow:")
            print("   input → Phase 1 → Phase 2 → Phase 3 → Phase 4")
            print()
            print("🎯 Pipeline Ready:")
            print("   • Input Parsing & Sanitization → Phase 1 folder")
            print("   • Chunking & Fact Extraction → Phase 2 folder")
            print("   • Personality Prompting & Formatting → Phase 3 folder")
            print("   • Quality Scoring & Assessment → Phase 4 folder")
        else:
            print("❌ Some folder configurations are INCORRECT!")
        
        return all_correct
        
    except Exception as e:
        print(f"❌ Error verifying configuration: {e}")
        return False

def show_pipeline_summary():
    """Show a summary of the pipeline system."""
    print("\n🎛️ PHASE-CONTROLLED PIPELINE SUMMARY")
    print("=" * 50)
    
    print("📊 System Features:")
    print("   ✅ Red/Green light phase control")
    print("   ✅ Selective phase execution")
    print("   ✅ Proper folder data transfer")
    print("   ✅ Real-time monitoring")
    print("   ✅ Quality assessment")
    
    print("\n📁 Folder Structure:")
    print("   input/     - Raw input files (PDF, CSV, JSON, JSONL, TXT)")
    print("   Phase 1/   - Sanitized and parsed text files")
    print("   Phase 2/   - Chunked text with fact extraction")
    print("   Phase 3/   - Personality-formatted training data")
    print("   Phase 4/   - Quality reports and final assessment")
    
    print("\n🔄 Data Transfer Flow:")
    print("   1. Input files → Phase 1 (sanitization)")
    print("   2. Phase 1 → Phase 2 (chunking)")
    print("   3. Phase 2 → Phase 3 (personality formatting)")
    print("   4. Phase 3 → Phase 4 (quality assessment)")
    
    print("\n🚀 Usage:")
    print("   python phase_control_gui.py  # Launch dashboard")
    print("   python test_folder_flow.py   # Test complete flow")

def main():
    """Main verification function."""
    print("🧪 PIPELINE FOLDER STRUCTURE VERIFICATION")
    print(f"Verifying correct folder configuration for data transfer")
    print()
    
    success = verify_pipeline_configuration()
    
    show_pipeline_summary()
    
    if success:
        print("\n🎉 VERIFICATION SUCCESSFUL!")
        print("The pipeline is correctly configured for proper data transfer.")
        return 0
    else:
        print("\n❌ VERIFICATION FAILED!")
        print("Please check the pipeline configuration.")
        return 1

if __name__ == "__main__":
    exit(main())
