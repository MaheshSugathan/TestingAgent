# Contributing to RAG Evaluation Pipeline

Thank you for your interest in contributing to the RAG Evaluation Pipeline! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Guidelines](#contributing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Release Process](#release-process)

## Code of Conduct

This project and everyone participating in it is governed by our commitment to providing a welcoming and inspiring community for all. Please be respectful and considerate of others.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/your-username/rag-evaluation-pipeline.git
   cd rag-evaluation-pipeline
   ```
3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/original-org/rag-evaluation-pipeline.git
   ```

## Development Setup

### Prerequisites

- Python 3.8 or higher
- AWS CLI configured (for AWS-related features)
- Git

### Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install development dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -e .[dev]
   ```

3. Set up pre-commit hooks (optional but recommended):
   ```bash
   pre-commit install
   ```

### Configuration

1. Copy the example environment file:
   ```bash
   cp env.example .env
   ```

2. Update `.env` with your configuration values

3. Ensure your AWS credentials are configured for testing

## Contributing Guidelines

### Types of Contributions

We welcome several types of contributions:

- **Bug fixes**: Fix issues in existing code
- **New features**: Add new functionality
- **Documentation**: Improve or add documentation
- **Tests**: Add or improve test coverage
- **Performance improvements**: Optimize existing code
- **Agent integrations**: Add support for new external agents

### Branch Naming

Use descriptive branch names:
- `feature/add-new-evaluator`
- `bugfix/fix-s3-retrieval-error`
- `docs/update-readme`
- `test/add-agentcore-tests`

### Commit Messages

Follow conventional commit format:
```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(agents): add support for OpenAI GPT models
fix(pipeline): resolve timeout issues in dev agent
docs(readme): update installation instructions
test(evaluator): add tests for new metrics
```

## Pull Request Process

1. **Create a feature branch** from `main`:
   ```bash
   git checkout main
   git pull upstream main
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the coding standards

3. **Add tests** for new functionality

4. **Update documentation** if needed

5. **Run tests** to ensure everything passes:
   ```bash
   pytest tests/
   ```

6. **Run linting** and formatting:
   ```bash
   black .
   flake8 .
   mypy .
   ```

7. **Commit your changes** with descriptive commit messages

8. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

9. **Create a Pull Request** with:
   - Clear title and description
   - Reference any related issues
   - Screenshots if UI changes
   - Testing instructions

### PR Review Process

- All PRs require at least one review
- CI/CD checks must pass
- Code coverage should not decrease
- Documentation must be updated for new features

## Issue Reporting

### Before Creating an Issue

1. Check existing issues to avoid duplicates
2. Ensure you're using the latest version
3. Try to reproduce the issue

### Issue Template

Use the following template when creating issues:

```markdown
**Describe the issue**
A clear description of what the issue is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. See error

**Expected behavior**
What you expected to happen.

**Environment:**
- OS: [e.g., Ubuntu 20.04]
- Python version: [e.g., 3.9.7]
- Package version: [e.g., 1.0.0]

**Additional context**
Add any other context about the problem here.
```

## Coding Standards

### Python Code Style

- Follow PEP 8
- Use Black for code formatting
- Use Flake8 for linting
- Use MyPy for type checking
- Maximum line length: 88 characters (Black default)

### Code Organization

- Keep functions focused and small
- Use descriptive variable and function names
- Add docstrings for all public functions and classes
- Follow the existing project structure

### Example Code Style

```python
def process_documents(documents: List[Document], 
                     config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Process documents for evaluation.
    
    Args:
        documents: List of LangChain documents to process
        config: Configuration dictionary
        
    Returns:
        List of processed document dictionaries
        
    Raises:
        ValueError: If documents list is empty
    """
    if not documents:
        raise ValueError("Documents list cannot be empty")
    
    # Implementation here
    return processed_docs
```

### Import Organization

```python
# Standard library imports
import os
import time
from typing import List, Dict, Any

# Third-party imports
import boto3
from langchain.schema import Document

# Local imports
from .base import BaseAgent
from ..config import ConfigManager
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_agents.py

# Run with coverage
pytest --cov=. --cov-report=html

# Run with verbose output
pytest -v

# Run specific test
pytest tests/test_agents.py::TestS3RetrievalAgent::test_parse_json_content
```

### Writing Tests

- Write tests for all new functionality
- Aim for high test coverage (>80%)
- Use descriptive test names
- Mock external dependencies
- Test both success and failure cases

### Test Structure

```python
class TestYourClass:
    """Test cases for YourClass."""
    
    @pytest.fixture
    def sample_data(self):
        """Provide sample data for tests."""
        return {"key": "value"}
    
    def test_success_case(self, sample_data):
        """Test successful execution."""
        # Arrange
        instance = YourClass()
        
        # Act
        result = instance.method(sample_data)
        
        # Assert
        assert result is not None
        assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_async_method(self):
        """Test async method."""
        # Test implementation
        pass
```

## Documentation

### Code Documentation

- Add docstrings to all public functions and classes
- Use Google-style docstrings
- Include type hints
- Document parameters, return values, and exceptions

### README Updates

- Update README.md for new features
- Include usage examples
- Update installation instructions if needed
- Add configuration examples

### API Documentation

- Document new CLI commands
- Update configuration options
- Add architecture diagrams if needed

## Release Process

### Version Numbering

We follow Semantic Versioning (SemVer):
- MAJOR: Incompatible API changes
- MINOR: New functionality (backward compatible)
- PATCH: Bug fixes (backward compatible)

### Release Checklist

1. Update version in `setup.py`
2. Update `CHANGELOG.md`
3. Run full test suite
4. Update documentation
5. Create release tag
6. Publish to PyPI (if applicable)

## Development Tools

### Recommended IDE Setup

- VS Code with Python extension
- Configure Black formatter
- Enable Flake8 linting
- Set up MyPy type checking

### Useful Commands

```bash
# Format code
black .

# Lint code
flake8 .

# Type check
mypy .

# Run tests
pytest

# Install in development mode
pip install -e .

# Build package
python setup.py sdist bdist_wheel
```

## Getting Help

- Check existing issues and discussions
- Join our community chat (if available)
- Create an issue for questions or bugs
- Review the documentation

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

Thank you for contributing to the RAG Evaluation Pipeline! 🚀
