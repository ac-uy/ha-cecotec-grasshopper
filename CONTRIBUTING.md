# Contributing to Cecotec GrassHopper Integration

Thank you for your interest in contributing! Here's how you can help.

## Reporting Issues

Found a bug? Please open an issue on [GitHub Issues](https://github.com/ac-uy/ha-cecotec-grasshopper/issues) with:

- **Description**: What's the problem?
- **Steps to reproduce**: How can we replicate it?
- **Expected behavior**: What should happen?
- **Actual behavior**: What actually happens?
- **Logs**: Include relevant Home Assistant logs (Settings → System → Logs)
- **Environment**: HA version, device model, etc.

## Feature Requests

Have an idea? Open an issue with the `enhancement` label and describe:

- **Use case**: Why is this needed?
- **Proposed solution**: How should it work?
- **Alternatives**: Any other approaches?

## Development

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/ac-uy/ha-cecotec-grasshopper.git
   cd ha-cecotec-grasshopper
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Testing

Test the API directly:
```bash
.\.venv\Scripts\python.exe test_api.py
```

Update `test_api.py` with your credentials first.

### Code Style

- Follow PEP 8
- Use type hints where possible
- Add docstrings to functions
- Keep functions focused and testable

## Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/) for clear, structured commit history.

### Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types

- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, missing semicolons, etc.)
- **refactor**: Code refactoring without feature changes
- **perf**: Performance improvements
- **test**: Adding or updating tests
- **chore**: Build, dependencies, or tooling changes
- **ci**: CI/CD configuration changes

### Examples

```
feat: add GPS location tracking for mower

fix: initialize device state in constructor

docs: update README with troubleshooting section

refactor: simplify update_device method

perf: reduce API polling interval from 60s to 30s
```

### Breaking Changes

For breaking changes, add `!` after the type:

```
feat!: change API authentication method

BREAKING CHANGE: OAuth2 now required instead of basic auth
```

## Versioning

This project uses [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Breaking changes
- **MINOR** (0.X.0): New features (backward compatible)
- **PATCH** (0.0.X): Bug fixes (backward compatible)

Update `manifest.json` version when releasing.

## Submitting Changes

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Test thoroughly
5. Commit with conventional commit messages
6. Push to your fork
7. Open a Pull Request with a clear description

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow

## Questions?

Open an issue or reach out on the [Home Assistant Community Forum](https://community.home-assistant.io/).

Thank you for contributing! 🚀
