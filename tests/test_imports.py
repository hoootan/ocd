"""Test that core modules can be imported without errors."""

import pytest


def test_cli_import():
    """Test that CLI module can be imported."""
    try:
        import ocd.cli
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import ocd.cli: {e}")


def test_models_import():
    """Test that models module can be imported."""
    try:
        from ocd.models import SLMModelManager
        assert SLMModelManager is not None
    except ImportError as e:
        pytest.fail(f"Failed to import ocd.models: {e}")


def test_providers_import():
    """Test that providers module can be imported."""
    try:
        from ocd.providers import LocalSLMProvider
        assert LocalSLMProvider is not None
    except ImportError as e:
        pytest.fail(f"Failed to import ocd.providers: {e}")


def test_analyzers_import():
    """Test that analyzers module can be imported."""
    try:
        from ocd.analyzers import DirectoryAnalyzer
        assert DirectoryAnalyzer is not None
    except ImportError as e:
        pytest.fail(f"Failed to import ocd.analyzers: {e}")


def test_core_types_import():
    """Test that core types can be imported."""
    try:
        from ocd.core.types import SafetyLevel, AnalysisType
        assert SafetyLevel is not None
        assert AnalysisType is not None
    except ImportError as e:
        pytest.fail(f"Failed to import ocd.core.types: {e}")


def test_tools_import():
    """Test that tools module can be imported."""
    try:
        from ocd.tools.file_operations import FileOperationManager
        assert FileOperationManager is not None
    except ImportError as e:
        pytest.fail(f"Failed to import ocd.tools: {e}")


def test_optional_agent_import():
    """Test that agent modules can be imported if LangChain is available."""
    try:
        from ocd.agents import OrganizationAgent
        assert OrganizationAgent is not None
        print("✅ LangChain agents available")
    except ImportError:
        print("⚠️ LangChain agents not available (expected in some environments)")
        # This is expected and acceptable
        pass