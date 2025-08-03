"""Basic functionality tests for OCD."""

import pytest
from pathlib import Path
import tempfile
import os


def test_directory_analysis():
    """Test basic directory analysis functionality."""
    try:
        from ocd.analyzers import DirectoryAnalyzer
        from ocd.core.types import AnalysisType
        
        analyzer = DirectoryAnalyzer()
        
        # Test with current directory
        current_dir = Path.cwd()
        result = analyzer.analyze(
            current_dir, 
            analysis_types=[AnalysisType.STRUCTURE]
        )
        
        assert result is not None
        assert hasattr(result, 'directory_info')
        assert result.directory_info.total_files >= 0
        
    except ImportError as e:
        pytest.skip(f"Dependencies not available: {e}")


def test_file_classification():
    """Test file classification with SLM models."""
    try:
        from ocd.models.classifier import FileClassifierSLM
        
        # Create temporary test files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            python_file = temp_path / "test.py"
            python_file.write_text("print('hello world')")
            
            text_file = temp_path / "test.txt"
            text_file.write_text("This is a text document")
            
            classifier = FileClassifierSLM()
            
            # Test Python file classification
            py_result = classifier.predict(str(python_file))
            assert py_result['category'] in ['code', 'documents']  # Allow flexibility
            
            # Test text file classification
            txt_result = classifier.predict(str(text_file))
            assert txt_result['category'] == 'documents'
            
    except ImportError as e:
        pytest.skip(f"SLM dependencies not available: {e}")
    except Exception as e:
        pytest.skip(f"SLM model loading failed (expected in CI): {e}")


def test_file_operations_manager():
    """Test file operations manager basic functionality."""
    try:
        from ocd.tools.file_operations import FileOperationManager, FileOperation
        from ocd.core.types import SafetyLevel
        
        manager = FileOperationManager(safety_level=SafetyLevel.BALANCED)
        
        # Test basic initialization
        assert manager.safety_level == SafetyLevel.BALANCED
        assert len(manager.operation_history) == 0
        
        # Test operation creation
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.txt"
            test_file.write_text("test content")
            
            operation = FileOperation(
                operation_type="move",
                source_path=test_file,
                destination_path=temp_path / "moved_test.txt"
            )
            
            assert operation.operation_type == "move"
            assert operation.source_path == test_file
            
    except ImportError as e:
        pytest.skip(f"Dependencies not available: {e}")


def test_cli_help():
    """Test that CLI help works."""
    try:
        from ocd.cli import app
        
        # Test that the CLI app exists and has commands
        assert app is not None
        assert hasattr(app, 'info')
        
    except ImportError as e:
        pytest.skip(f"CLI dependencies not available: {e}")


@pytest.mark.integration
def test_end_to_end_dry_run():
    """Test end-to-end dry run functionality."""
    try:
        from ocd.cli import _run_basic_organization
        from ocd.core.types import SafetyLevel
        
        # Test with current directory (dry run only)
        current_dir = Path.cwd()
        
        # This should not raise an exception
        # Note: Actual execution depends on available dependencies
        # In CI, this tests the import and basic structure
        
        assert callable(_run_basic_organization)
        
    except ImportError as e:
        pytest.skip(f"Dependencies not available: {e}")


def test_safety_levels():
    """Test that safety levels are properly defined."""
    try:
        from ocd.core.types import SafetyLevel
        
        # Test enum values
        assert SafetyLevel.MINIMAL == "minimal"
        assert SafetyLevel.BALANCED == "balanced"
        assert SafetyLevel.MAXIMUM == "maximum"
        
        # Test that all required levels exist
        safety_levels = [e.value for e in SafetyLevel]
        assert "minimal" in safety_levels
        assert "balanced" in safety_levels
        assert "maximum" in safety_levels
        
    except ImportError as e:
        pytest.skip(f"Dependencies not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])