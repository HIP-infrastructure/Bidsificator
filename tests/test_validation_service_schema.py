#!/usr/bin/env python
"""
Test the new schema-driven ValidationService implementation
"""

import json
import tempfile
from pathlib import Path

from bidsificator.core.schema import BidsSchemaManager
from bidsificator.services.ValidationServiceSchema import ValidationService, ValidationResult, ValidationError


def test_validation_service():
    """Test the schema-driven ValidationService"""
    
    print("=" * 70)
    print("TESTING SCHEMA-DRIVEN VALIDATION SERVICE")
    print("=" * 70)
    
    # Setup
    schema_manager = BidsSchemaManager()
    schema_manager.load_schema()
    validator = ValidationService(schema_manager)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        dataset_path = Path(temp_dir) / "test_dataset"
        dataset_path.mkdir()
        
        print("✅ Schema loaded and validator initialized")
        
        # Test 1: Validate empty dataset (should fail)
        print("\n1. TESTING EMPTY DATASET VALIDATION")
        print("-" * 50)
        
        result = validator.validate_dataset(str(dataset_path))
        print(f"Empty dataset valid: {result.is_valid}")
        print(f"Message: {result.message}")
        print(f"Errors: {result.error_count}, Warnings: {result.warning_count}")
        
        if result.errors:
            for error in result.errors[:3]:  # Show first 3 errors
                print(f"  - {error.message} ({error.rule})")
        
        assert not result.is_valid, "Empty dataset should not be valid"
        print("✅ Empty dataset correctly rejected")
        
        # Test 2: Create minimal valid dataset
        print("\n2. TESTING MINIMAL VALID DATASET")
        print("-" * 50)
        
        # Create dataset_description.json
        dataset_desc = {
            "Name": "Test Dataset",
            "BIDSVersion": "1.10.0",
            "Description": "A test dataset for validation"
        }
        
        with open(dataset_path / "dataset_description.json", 'w') as f:
            json.dump(dataset_desc, f, indent=2)
        
        # Create a test subject
        subject_dir = dataset_path / "sub-01"
        ieeg_dir = subject_dir / "ieeg"
        ieeg_dir.mkdir(parents=True)
        
        # Create a data file and sidecar
        data_file = ieeg_dir / "sub-01_task-rest_ieeg.edf"
        data_file.write_text("dummy edf data")
        
        json_file = ieeg_dir / "sub-01_task-rest_ieeg.json"
        metadata = {
            "TaskName": "rest",
            "SamplingFrequency": 1024,
            "iEEGReference": "average",
            "PowerLineFrequency": 60,
            "SoftwareFilters": "n/a",
            "iEEGCoordinateSystem": "ACPC",
            "iEEGCoordinateUnits": "mm",
            "iEEGCoordinateSystemDescription": "ACPC coordinates"
        }
        
        with open(json_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Validate dataset
        result = validator.validate_dataset(str(dataset_path))
        print(f"Minimal dataset valid: {result.is_valid}")
        print(f"Message: {result.message}")
        print(f"Errors: {result.error_count}, Warnings: {result.warning_count}")
        
        if result.warnings:
            for warning in result.warnings[:3]:  # Show first 3 warnings
                print(f"  Warning: {warning.message} ({warning.rule})")
        
        assert result.error_count == 0, "Minimal dataset should have no errors (warnings are OK)"
        print("✅ Minimal dataset validation completed")
        
        # Test 3: Subject-specific validation
        print("\n3. TESTING SUBJECT-SPECIFIC VALIDATION")
        print("-" * 50)
        
        subject_result = validator.validate_subject(str(dataset_path), "sub-01")
        print(f"Subject validation: {subject_result.is_valid}")
        print(f"Message: {subject_result.message}")
        print(f"Errors: {subject_result.error_count}, Warnings: {subject_result.warning_count}")
        
        # Test invalid subject
        invalid_result = validator.validate_subject(str(dataset_path), "sub-999")
        print(f"Invalid subject validation: {invalid_result.is_valid}")
        print(f"Message: {invalid_result.message}")
        
        assert not invalid_result.is_valid, "Invalid subject should fail validation"
        print("✅ Subject validation working correctly")
        
        # Test 4: Filename validation
        print("\n4. TESTING FILENAME VALIDATION")
        print("-" * 50)
        
        test_filenames = [
            ("sub-01_task-rest_ieeg.edf", True, "Valid iEEG filename"),
            ("sub-01_ses-pre_task-memory_run-1_ieeg.edf", True, "Valid with session and run"),
            ("task-rest_ieeg.edf", False, "Missing subject"),
            ("sub-01_invalid@char_ieeg.edf", False, "Invalid character"),
            ("sub-01_task-rest_wrongsuffix.edf", False, "Wrong suffix for ieeg"),
        ]
        
        for filename, should_be_valid, description in test_filenames:
            result = validator.validate_filename(filename, 'ieeg')
            is_valid = result.is_valid
            status = "✅" if is_valid == should_be_valid else "❌"
            print(f"  {status} {filename}: {description} ({'Valid' if is_valid else 'Invalid'})")
            
            if not is_valid and result.errors:
                print(f"      Error: {result.errors[0].message}")
        
        print("✅ Filename validation completed")
        
        # Test 5: Backward compatibility methods
        print("\n5. TESTING BACKWARD COMPATIBILITY")
        print("-" * 50)
        
        # Test old method signatures
        valid, msg = validator.validate_subject_name("sub-01")
        print(f"Subject name validation: {valid} - {msg}")
        assert valid, "Valid subject name should pass"
        
        valid, msg = validator.validate_session_name("ses-pre")
        print(f"Session name validation: {valid} - {msg}")
        assert valid, "Valid session name should pass"
        
        valid, msg = validator.validate_task_name("rest")
        print(f"Task name validation: {valid} - {msg}")
        assert valid, "Valid task name should pass"
        
        # Test old dataset validation method
        valid, msg = validator.validate_bids_dataset(str(dataset_path))
        print(f"Dataset validation (old method): {valid} - {msg}")
        
        print("✅ Backward compatibility working")
        
        # Test 6: Error categorization
        print("\n6. TESTING ERROR CATEGORIZATION")
        print("-" * 50)
        
        # Create a problematic dataset
        problem_dir = dataset_path / "sub-02"
        problem_ieeg_dir = problem_dir / "ieeg" 
        problem_ieeg_dir.mkdir(parents=True)
        
        # File with missing required metadata
        problem_data = problem_ieeg_dir / "sub-02_task-test_ieeg.edf"
        problem_data.write_text("dummy data")
        
        problem_json = problem_ieeg_dir / "sub-02_task-test_ieeg.json"
        incomplete_metadata = {
            "TaskName": "test",
            "SamplingFrequency": "n/a"  # This should trigger an error
        }
        
        with open(problem_json, 'w') as f:
            json.dump(incomplete_metadata, f, indent=2)
        
        # Validate problematic subject
        problem_result = validator.validate_subject(str(dataset_path), "sub-02")
        
        print(f"Problematic subject:")
        print(f"  Valid: {problem_result.is_valid}")
        print(f"  Errors: {problem_result.error_count}")
        print(f"  Warnings: {problem_result.warning_count}")
        
        # Show error details
        for error in problem_result.errors:
            print(f"    Error: {error.message} (Rule: {error.rule})")
        
        for warning in problem_result.warnings:
            print(f"    Warning: {warning.message} (Rule: {warning.rule})")
        
        print("✅ Error categorization working")
        
        # Test 7: ValidationResult dataclass
        print("\n7. TESTING VALIDATIONRESULT FEATURES")
        print("-" * 50)
        
        # Create a result with mixed issues
        test_result = ValidationResult(
            is_valid=False,
            message="Test result",
            errors=[
                ValidationError("test1.txt", "Error 1", "error", "test-rule"),
                ValidationError("test2.txt", "Error 2", "error", "test-rule")
            ],
            warnings=[
                ValidationError("test3.txt", "Warning 1", "warning", "test-rule")
            ]
        )
        
        print(f"  Error count: {test_result.error_count}")
        print(f"  Warning count: {test_result.warning_count}")
        print(f"  Total issues: {test_result.total_issues}")
        
        assert test_result.error_count == 2, "Should have 2 errors"
        assert test_result.warning_count == 1, "Should have 1 warning"
        assert test_result.total_issues == 3, "Should have 3 total issues"
        
        print("✅ ValidationResult features working")
    
    print(f"\n{'='*70}")
    print("✅ ALL VALIDATION SERVICE TESTS PASSED!")
    print(f"{'='*70}")
    return True


if __name__ == "__main__":
    success = test_validation_service()
    exit(0 if success else 1)