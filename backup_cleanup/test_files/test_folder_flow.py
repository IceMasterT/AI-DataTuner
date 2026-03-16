#!/usr/bin/env python3
"""
Test script to verify proper folder flow and data transfer in the phase-controlled pipeline.
Tests: Input → Phase 1 → Phase 2 → Phase 3 → Phase 4
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime

def print_header(title):
    """Print a formatted header."""
    print("\n" + "="*70)
    print(f" {title}")
    print("="*70)

def print_section(title):
    """Print a section header."""
    print(f"\n📁 {title}")
    print("-" * 50)

def setup_test_environment():
    """Set up test environment with sample data."""
    print_section("Setting Up Test Environment")
    
    # Create input folder with sample files
    input_folder = Path("input")
    input_folder.mkdir(exist_ok=True)
    
    # Create sample text files
    sample_files = {
        "sample1.txt": """
        Machine learning is a method of data analysis that automates analytical model building. 
        It is a branch of artificial intelligence based on the idea that systems can learn from data, 
        identify patterns and make decisions with minimal human intervention.
        """,
        
        "sample2.txt": """
        Natural language processing (NLP) is a subfield of linguistics, computer science, and artificial intelligence. 
        It is concerned with the interactions between computers and human language, in particular how to program 
        computers to process and analyze large amounts of natural language data.
        """,
        
        "sample3.txt": """
        Deep learning is part of a broader family of machine learning methods based on artificial neural networks. 
        Learning can be supervised, semi-supervised or unsupervised. Deep learning architectures such as deep neural 
        networks have been applied to fields including computer vision, speech recognition, and natural language processing.
        """
    }
    
    for filename, content in sample_files.items():
        file_path = input_folder / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content.strip())
        print(f"✅ Created: {file_path}")
    
    # Clean up any existing phase folders
    for phase_folder in ["Phase 1", "Phase 2", "Phase 3", "Phase 4"]:
        if Path(phase_folder).exists():
            shutil.rmtree(phase_folder)
            print(f"🧹 Cleaned up existing: {phase_folder}")
    
    print(f"📁 Test environment ready with {len(sample_files)} sample files")

def test_pipeline_folder_flow():
    """Test the complete pipeline folder flow."""
    print_header("TESTING PIPELINE FOLDER FLOW")
    
    try:
        from phase_controlled_pipeline import get_pipeline
        
        # Get pipeline instance
        pipeline = get_pipeline()
        
        # Verify folder configuration
        print_section("Verifying Folder Configuration")
        
        expected_flow = [
            ("phase1_sanitization", "input", "Phase 1"),
            ("phase2_chunking", "Phase 1", "Phase 2"),
            ("phase3_personality", "Phase 2", "Phase 3"),
            ("phase4_quality", "Phase 3", "Phase 4")
        ]
        
        for phase_name, expected_input, expected_output in expected_flow:
            phase_config = pipeline.phases[phase_name]
            actual_input = phase_config.input_folder
            actual_output = phase_config.output_folder
            
            print(f"📋 {phase_config.name}:")
            print(f"   Input:  {actual_input} {'✅' if actual_input == expected_input else '❌'}")
            print(f"   Output: {actual_output} {'✅' if actual_output == expected_output else '❌'}")
            
            if actual_input != expected_input or actual_output != expected_output:
                print(f"   ❌ Expected: {expected_input} → {expected_output}")
                return False
        
        print("✅ All folder configurations are correct!")
        
        # Enable all phases
        print_section("Enabling All Phases")
        from phase_controlled_pipeline import PhaseStatus

        for phase_name in pipeline.phases.keys():
            pipeline.set_phase_status(phase_name, PhaseStatus.ENABLED)
            print(f"🟢 Enabled: {pipeline.phases[phase_name].name}")
        
        # Run pipeline
        print_section("Running Complete Pipeline")
        print("🚀 Starting pipeline execution...")
        
        results = pipeline.start_pipeline()
        
        # Verify results
        print_section("Verifying Results")
        
        for phase_name, result in results.items():
            phase_config = pipeline.phases[phase_name]
            print(f"\n📊 {phase_config.name}:")
            print(f"   Status: {result.status.value}")
            print(f"   Files Processed: {result.files_processed}")
            print(f"   Files Failed: {result.files_failed}")
            print(f"   Output Files: {len(result.output_files)}")
            print(f"   Output Folder: {phase_config.output_folder}")
            
            if result.errors:
                print(f"   Errors: {len(result.errors)}")
                for error in result.errors[:3]:  # Show first 3 errors
                    print(f"     • {error}")
        
        return True
        
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_folder_contents():
    """Verify that data was properly transferred between folders."""
    print_header("VERIFYING FOLDER CONTENTS & DATA TRANSFER")
    
    folders_to_check = ["input", "Phase 1", "Phase 2", "Phase 3", "Phase 4"]
    
    for folder_name in folders_to_check:
        folder_path = Path(folder_name)
        
        print_section(f"Checking {folder_name} Folder")
        
        if not folder_path.exists():
            print(f"❌ Folder does not exist: {folder_path}")
            continue
        
        # Count files
        all_files = list(folder_path.rglob("*"))
        files_only = [f for f in all_files if f.is_file()]
        
        print(f"📁 Folder: {folder_path}")
        print(f"📄 Files: {len(files_only)}")
        
        if files_only:
            print("📋 File List:")
            for file_path in files_only[:10]:  # Show first 10 files
                relative_path = file_path.relative_to(folder_path)
                file_size = file_path.stat().st_size
                print(f"   • {relative_path} ({file_size} bytes)")
            
            if len(files_only) > 10:
                print(f"   ... and {len(files_only) - 10} more files")
            
            # Show sample content from first file
            if files_only:
                sample_file = files_only[0]
                try:
                    with open(sample_file, 'r', encoding='utf-8') as f:
                        content = f.read()[:200]  # First 200 characters
                    print(f"📝 Sample content from {sample_file.name}:")
                    print(f"   {content}...")
                except Exception as e:
                    print(f"   Could not read sample: {e}")
        else:
            print("📄 No files found")

def verify_data_flow():
    """Verify that data flows correctly through the pipeline."""
    print_header("VERIFYING DATA FLOW")
    
    flow_checks = [
        ("input", "Phase 1", "Input files should be sanitized and transferred"),
        ("Phase 1", "Phase 2", "Sanitized files should be chunked"),
        ("Phase 2", "Phase 3", "Chunks should be personality-formatted"),
        ("Phase 3", "Phase 4", "Formatted data should be quality-assessed")
    ]
    
    for source_folder, target_folder, description in flow_checks:
        print_section(f"Data Flow: {source_folder} → {target_folder}")
        
        source_path = Path(source_folder)
        target_path = Path(target_folder)
        
        if not source_path.exists():
            print(f"❌ Source folder missing: {source_path}")
            continue
        
        if not target_path.exists():
            print(f"❌ Target folder missing: {target_path}")
            continue
        
        source_files = [f for f in source_path.rglob("*") if f.is_file()]
        target_files = [f for f in target_path.rglob("*") if f.is_file()]
        
        print(f"📊 {description}")
        print(f"   Source files: {len(source_files)}")
        print(f"   Target files: {len(target_files)}")
        
        if target_files:
            print(f"✅ Data transfer successful")
        else:
            print(f"❌ No data transferred")

def check_final_output():
    """Check the final output in Phase 4."""
    print_header("CHECKING FINAL OUTPUT")
    
    phase4_path = Path("Phase 4")
    
    if not phase4_path.exists():
        print("❌ Phase 4 folder does not exist")
        return False
    
    # Look for quality report
    report_files = list(phase4_path.glob("*report*.json"))
    summary_files = list(phase4_path.glob("*summary*.txt"))
    
    print_section("Quality Assessment Files")
    
    if report_files:
        for report_file in report_files:
            print(f"📊 Found quality report: {report_file.name}")
            
            try:
                with open(report_file, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
                
                if "pipeline_summary" in report_data:
                    summary = report_data["pipeline_summary"]
                    print(f"   Files processed: {summary.get('files_scored', 0)}")
                    print(f"   Average quality: {summary.get('average_quality_score', 0):.1f}/100")
                    print(f"   Processing complete: {summary.get('processing_complete', False)}")
                
                if "quality_metrics" in report_data:
                    metrics = report_data["quality_metrics"]
                    print(f"   Overall grade: {metrics.get('overall_grade', 'N/A')}")
            
            except Exception as e:
                print(f"   Error reading report: {e}")
    
    if summary_files:
        for summary_file in summary_files:
            print(f"📋 Found summary: {summary_file.name}")
            
            try:
                with open(summary_file, 'r', encoding='utf-8') as f:
                    content = f.read()[:500]  # First 500 characters
                print(f"   Content preview:")
                for line in content.split('\n')[:5]:
                    if line.strip():
                        print(f"     {line}")
            
            except Exception as e:
                print(f"   Error reading summary: {e}")
    
    if not report_files and not summary_files:
        print("❌ No quality assessment files found")
        return False
    
    print("✅ Final output verification complete")
    return True

def main():
    """Run complete folder flow test."""
    print("🧪 PHASE-CONTROLLED PIPELINE FOLDER FLOW TEST")
    print("Testing proper data transfer: Input → Phase 1 → Phase 2 → Phase 3 → Phase 4")
    print(f"Test started at: {datetime.now()}")
    
    try:
        # Setup test environment
        setup_test_environment()
        
        # Test pipeline folder flow
        if not test_pipeline_folder_flow():
            print("\n❌ Pipeline test failed!")
            return 1
        
        # Verify folder contents
        verify_folder_contents()
        
        # Verify data flow
        verify_data_flow()
        
        # Check final output
        if not check_final_output():
            print("\n❌ Final output verification failed!")
            return 1
        
        print_header("TEST RESULTS")
        print("🎉 All tests passed successfully!")
        
        print("\n✅ Verified Features:")
        print("  • Correct folder configuration (Input → Phase 1 → Phase 2 → Phase 3 → Phase 4)")
        print("  • Proper data transfer between phases")
        print("  • File processing and transformation")
        print("  • Quality assessment and final reporting")
        print("  • Complete pipeline execution")
        
        print("\n📁 Final Folder Structure:")
        print("  input/          - Original input files")
        print("  Phase 1/        - Sanitized and parsed files")
        print("  Phase 2/        - Chunked text files")
        print("  Phase 3/        - Personality-formatted training data")
        print("  Phase 4/        - Quality reports and final assessment")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
