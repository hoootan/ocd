# Contributing to OCD 🤝

Thank you for your interest in contributing to OCD (Organized Content Directory)! We welcome contributions from the community and are excited to see what you'll build.

## 🎯 Ways to Contribute

### 🐛 Bug Reports
- Use GitHub Issues to report bugs
- Include detailed steps to reproduce
- Provide system information (OS, Python version)
- Include relevant log output

### ✨ Feature Requests
- Check existing issues first
- Describe the use case clearly
- Explain why the feature would be valuable
- Consider implementation complexity

### 💻 Code Contributions
- Fork the repository
- Create a feature branch
- Write tests for new functionality
- Follow our coding standards
- Submit a pull request

### 📚 Documentation
- Improve existing documentation
- Add examples and tutorials
- Fix typos and clarifications
- Update outdated information

## 🚀 Getting Started

### Development Setup

1. **Fork and Clone**:
   ```bash
   git clone https://github.com/your-username/ocd.git
   cd ocd
   ```

2. **Install Development Environment**:
   ```bash
   python install.py --dev
   source .venv/bin/activate  # macOS/Linux
   ```

3. **Verify Setup**:
   ```bash
   ocd --help
   pytest  # Run tests
   ```

### Development Workflow

1. **Create Feature Branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**:
   - Write code following our standards
   - Add tests for new functionality
   - Update documentation as needed

3. **Test Your Changes**:
   ```bash
   # Run all tests
   pytest

   # Run with coverage
   pytest --cov=src/ocd --cov-report=html

   # Test specific functionality
   ocd organize test_folder --dry-run
   ```

4. **Code Quality Checks**:
   ```bash
   # Format code
   black src/ tests/ examples/

   # Sort imports
   isort src/ tests/ examples/

   # Lint code
   flake8 src/ tests/

   # Type check
   mypy src/
   ```

## 📋 Coding Standards

### Python Style
- Follow PEP 8
- Use Black for formatting (line length: 88)
- Use type hints for all functions
- Write comprehensive docstrings

### Code Organization
```python
# Good: Clear, descriptive function with type hints
async def organize_files_by_type(
    directory: Path, 
    dry_run: bool = True
) -> List[OperationResult]:
    """
    Organize files in directory by their type.
    
    Args:
        directory: Path to directory to organize
        dry_run: If True, only preview changes
        
    Returns:
        List of operation results
    """
    # Implementation here
```

### Documentation
- Use Google-style docstrings
- Include examples in docstrings
- Update README.md for user-facing changes
- Add inline comments for complex logic

### Testing
- Write unit tests for all new functions
- Include integration tests for features
- Test both success and error cases
- Use meaningful test names

```python
def test_file_classifier_handles_unknown_extensions():
    """FileClassifierSLM should gracefully handle unknown file types."""
    # Test implementation
```

## 🏗️ Architecture Guidelines

### Adding New SLM Models
1. Inherit from `BaseSLM`
2. Implement required abstract methods
3. Add resource management
4. Include comprehensive tests
5. Update model manager

### Adding New Providers
1. Inherit from `BaseProvider`
2. Implement provider interface
3. Add configuration support
4. Include error handling
5. Add to provider registry

### Adding New Tools
1. Follow LangChain tool interface
2. Include comprehensive validation
3. Add safety checks
4. Implement dry-run mode
5. Add operation logging

## 🧪 Testing

### Running Tests
```bash
# All tests
pytest

# Specific test file
pytest tests/test_models.py

# Integration tests
pytest tests/integration/

# With coverage
pytest --cov=src/ocd --cov-report=term-missing
```

### Test Categories
- **Unit Tests**: Individual function testing
- **Integration Tests**: Component interaction testing  
- **End-to-End Tests**: Full workflow testing
- **Performance Tests**: Speed and resource usage

### Writing Tests
```python
import pytest
from pathlib import Path
from ocd.models import FileClassifierSLM

@pytest.fixture
def temp_directory(tmp_path):
    """Create temporary test directory."""
    return tmp_path

def test_classifier_categorizes_code_files(temp_directory):
    """FileClassifierSLM should correctly identify code files."""
    # Create test files
    python_file = temp_directory / "script.py"
    python_file.write_text("print('hello')")
    
    # Test classification
    classifier = FileClassifierSLM()
    result = classifier.predict(str(python_file))
    
    assert result["category"] == "code"
    assert result["subcategory"] == "python"
```

## 🔍 Code Review Process

### Before Submitting PR
- [ ] All tests pass
- [ ] Code is formatted (black, isort)
- [ ] No linting errors (flake8)
- [ ] Type checking passes (mypy)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated

### PR Requirements
- Clear description of changes
- Reference related issues
- Include test results
- Screenshots for UI changes
- Breaking changes documented

### Review Criteria
- Code quality and clarity
- Test coverage
- Documentation completeness
- Performance impact
- Security considerations

## 🎨 Feature Development

### New SLM Models
When adding specialized models:
- Research existing solutions
- Design for efficiency and accuracy
- Include quantization support
- Add comprehensive benchmarks
- Document model capabilities

### New Organization Strategies
When adding organization methods:
- Consider user workflows
- Support multiple file types
- Include safety validation
- Add dry-run support
- Provide clear examples

### New AI Providers
When adding provider support:
- Follow provider interface
- Include error handling
- Add configuration options
- Support rate limiting
- Document setup process

## 📊 Performance Guidelines

### Efficiency Requirements
- SLM models should load in <5 seconds
- File analysis should handle 1000+ files
- Memory usage should be reasonable
- Provide progress indicators
- Support cancellation

### Benchmarking
```bash
# Performance testing
python -m pytest tests/performance/ -v

# Memory profiling
python -m memory_profiler examples/large_directory_test.py

# CPU profiling
python -m cProfile -o profile.stats ocd organize large_folder --dry-run
```

## 🐛 Debugging

### Common Issues
- Model loading failures: Check dependencies
- File permission errors: Validate paths
- Memory issues: Monitor model usage
- Performance problems: Profile bottlenecks

### Debug Tools
```bash
# Verbose logging
export OCD_LOG_LEVEL=DEBUG
ocd organize folder --dry-run

# Python debugging
python -m pdb -c continue ocd organize folder

# Memory debugging
python -m tracemalloc -- ocd organize folder
```

## 📝 Issue Templates

### Bug Report Template
```markdown
**Bug Description**
Clear description of the bug

**Steps to Reproduce**
1. Step one
2. Step two
3. Step three

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happens

**System Information**
- OS: [Windows/macOS/Linux]
- Python version: [3.9/3.10/3.11/3.12]
- OCD version: [0.1.0]

**Additional Context**
Any other relevant information
```

### Feature Request Template
```markdown
**Feature Description**
Clear description of the proposed feature

**Use Case**
Why this feature would be valuable

**Proposed Solution**
How the feature might work

**Alternatives Considered**
Other approaches you've considered

**Additional Context**
Any other relevant information
```

## 🏆 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Credited in relevant documentation
- Given appropriate GitHub badges

## 📞 Getting Help

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Code Review**: PRs and code feedback
- **Documentation**: README and wiki updates

## 📜 Code of Conduct

We are committed to providing a welcoming and inclusive experience for everyone. Please be:

- **Respectful**: Treat everyone with respect
- **Inclusive**: Welcome diverse perspectives
- **Collaborative**: Work together constructively
- **Professional**: Maintain professional standards

Thank you for contributing to OCD! 🎉