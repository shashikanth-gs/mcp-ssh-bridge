# Contributing to SSH MCP Bridge

Thank you for your interest in contributing to SSH MCP Bridge! This document provides guidelines and instructions for contributing.

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of experience level, gender identity, sexual orientation, disability, personal appearance, race, ethnicity, age, religion, or nationality.

### Expected Behavior

- Be respectful and considerate
- Use welcoming and inclusive language
- Accept constructive criticism gracefully
- Focus on what is best for the community
- Show empathy towards other community members

### Unacceptable Behavior

- Harassment, discrimination, or offensive comments
- Trolling or personal attacks
- Publishing others' private information
- Other conduct that could reasonably be considered inappropriate

## How to Contribute

### Reporting Bugs

Before creating a bug report:
1. Check the [existing issues](https://github.com/shashikanth-gs/mcp-ssh-bridge/issues)
2. Verify the bug exists in the latest version
3. Collect relevant information (logs, configuration, steps to reproduce)

When creating a bug report, include:
- Clear and descriptive title
- Detailed steps to reproduce
- Expected vs. actual behavior
- Environment details (OS, Python version, Docker version)
- Configuration file (remove sensitive data)
- Relevant log output
- Screenshots if applicable

### Suggesting Enhancements

Enhancement suggestions are welcome! Include:
- Clear use case and motivation
- Detailed description of the proposed feature
- Examples of how it would work
- Potential implementation approach (optional)

### Pull Requests

1. **Fork the repository**
   ```bash
   git clone https://github.com/shashikanth-gs/mcp-ssh-bridge.git
   cd ssh-mcp-bridge
   git remote add upstream https://github.com/shashikanth-gs/mcp-ssh-bridge.git
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Follow coding standards (see below)
   - Add tests for new functionality
   - Update documentation as needed
   - Keep commits atomic and well-described

4. **Test your changes**
   ```bash
   # Run tests
   pytest
   
   # Check code style
   black src/ tests/
   flake8 src/ tests/
   mypy src/
   ```

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```
   
   Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation changes
   - `test:` - Test additions or changes
   - `refactor:` - Code refactoring
   - `chore:` - Maintenance tasks

6. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create Pull Request**
   - Go to GitHub and create a PR from your fork
   - Fill in the PR template
   - Link related issues
   - Wait for review

## Development Setup

### Prerequisites

- Python 3.9 or higher
- Git
- Docker (optional, for testing)

### Setup Instructions

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/ssh-mcp-bridge.git
cd ssh-mcp-bridge

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks (optional)
pre-commit install
```

### Development Dependencies

The development installation includes:
- **pytest** - Testing framework
- **pytest-cov** - Code coverage
- **pytest-asyncio** - Async testing
- **black** - Code formatter
- **flake8** - Linter
- **mypy** - Type checker
- **pre-commit** - Git hooks

## Coding Standards

### Python Style

Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide:

```bash
# Format code
black src/ tests/

# Check style
flake8 src/ tests/

# Type checking
mypy src/
```

### Code Organization

- One class per file (generally)
- Group related functions together
- Keep files under 500 lines when possible
- Use meaningful names for variables and functions

### Type Hints

Use type hints for all function signatures:

```python
def execute_command(self, host: str, command: str) -> dict[str, Any]:
    """Execute command on specified host.
    
    Args:
        host: Name of the SSH host
        command: Command to execute
        
    Returns:
        Dictionary with execution results
        
    Raises:
        ValueError: If host not found
        SSHException: If SSH connection fails
    """
    pass
```

### Docstrings

Use Google-style docstrings:

```python
def function_name(arg1: str, arg2: int) -> bool:
    """Brief description of function.
    
    Longer description if needed. Explain what the function does,
    any important notes, and usage examples.
    
    Args:
        arg1: Description of arg1
        arg2: Description of arg2
        
    Returns:
        Description of return value
        
    Raises:
        ExceptionType: When this exception occurs
        
    Examples:
        >>> function_name("test", 42)
        True
    """
    pass
```

### Error Handling

- Use specific exceptions
- Provide helpful error messages
- Log errors appropriately
- Don't catch exceptions you can't handle

```python
try:
    session = self._create_session(host)
except paramiko.SSHException as e:
    logger.error(f"SSH connection failed for {host}: {e}")
    raise ConnectionError(f"Could not connect to {host}") from e
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ssh_mcp_bridge --cov-report=html

# Run specific test file
pytest tests/test_config.py

# Run specific test
pytest tests/test_config.py::test_config_loading
```

### Writing Tests

```python
import pytest
from ssh_mcp_bridge.models.config import ServerConfig

def test_server_config_defaults():
    """Test ServerConfig with default values."""
    config = ServerConfig(enable_stdio=True)
    assert config.enable_stdio is True
    assert config.enable_http is False
    assert config.log_level == "INFO"

def test_server_config_validation():
    """Test ServerConfig validation."""
    with pytest.raises(ValueError):
        ServerConfig(enable_stdio=False, enable_http=False)
```

### Test Coverage

- Aim for >80% code coverage
- Test happy paths and error cases
- Test edge cases and boundary conditions
- Mock external dependencies (SSH, HTTP requests)

## Documentation

### Code Documentation

- Add docstrings to all public functions and classes
- Update existing docstrings when modifying code
- Include usage examples in docstrings

### User Documentation

When adding features, update:
- README.md - If it affects quick start or overview
- docs/ - Add detailed documentation
- examples/ - Add configuration examples if needed

### Documentation Style

- Use clear, concise language
- Include code examples
- Add diagrams when helpful
- Keep formatting consistent

## Commit Messages

Follow Conventional Commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Examples

```
feat(http): add OAuth 2.0 authentication support

Implement OAuth 2.0/OIDC authentication for HTTP mode:
- Add JWT token validation
- Fetch and cache JWKS from provider
- Extract user claims from tokens
- Add OAuth discovery endpoint

Closes #123
```

```
fix(session): prevent race condition in session cleanup

The cleanup thread was occasionally closing active sessions.
Added lock to prevent concurrent access to sessions dict.

Fixes #456
```

### Type Guidelines

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation only
- **style**: Formatting, missing semicolons, etc.
- **refactor**: Code change that neither fixes a bug nor adds a feature
- **perf**: Performance improvement
- **test**: Adding or correcting tests
- **chore**: Updating build tasks, package manager configs, etc.

## Review Process

### What to Expect

1. **Automated checks** run on your PR:
   - Tests must pass
   - Code style checks
   - Type checking
   - Coverage analysis

2. **Code review** by maintainers:
   - Usually within 1-3 days
   - May request changes
   - Discussion and iteration

3. **Approval and merge**:
   - At least one approval required
   - Squash and merge or rebase
   - Automatic deployment (if configured)

### Review Checklist

Before requesting review, ensure:
- [ ] Tests pass locally
- [ ] Code follows style guide
- [ ] Documentation updated
- [ ] Commit messages follow convention
- [ ] No merge conflicts
- [ ] PR description is clear
- [ ] Related issues are linked

## Project Structure

```
ssh-mcp-bridge/
├── src/
│   └── ssh_mcp_bridge/
│       ├── __init__.py
│       ├── __main__.py
│       ├── app.py
│       ├── api/              # API layer
│       │   ├── http_server.py
│       │   └── mcp_server.py
│       ├── core/             # Core logic
│       │   ├── session_manager.py
│       │   └── ssh_session.py
│       ├── models/           # Data models
│       │   └── config.py
│       ├── services/         # Business logic
│       │   └── mcp_service.py
│       └── utils/            # Utilities
│           ├── jwt_verifier.py
│           └── logging.py
├── tests/                    # Test files
├── docs/                     # Documentation
├── examples/                 # Example configs
├── requirements.txt          # Dependencies
├── pyproject.toml           # Project metadata
├── pytest.ini               # Test configuration
└── README.md                # Main documentation
```

## Release Process

Maintainers follow these steps for releases:

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create release tag
4. Build and publish to PyPI (if applicable)
5. Build and push Docker images
6. Create GitHub release

## Questions or Help

- **Documentation**: Check the [docs/](docs/) directory
- **Issues**: Search [existing issues](https://github.com/shashikanth-gs/mcp-ssh-bridge/issues)
- **Discussions**: Use [GitHub Discussions](https://github.com/shashikanth-gs/mcp-ssh-bridge/discussions)
- **Contact**: Create an issue or reach out to maintainers

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- GitHub contributors page

Thank you for contributing to SSH MCP Bridge!
