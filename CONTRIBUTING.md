# Contributing to Kalshi Market Insights

Thank you for your interest in contributing to this project! This is a **portfolio demonstration project** showcasing data science and full-stack engineering skills. While it's primarily maintained by the author, contributions that align with the project's goals are welcome.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Submitting Contributions](#submitting-contributions)
- [Reporting Issues](#reporting-issues)

## 🤝 Code of Conduct

This project adheres to a simple principle: **be respectful and professional**. We're all here to learn and build cool things together.

- Be kind and constructive in feedback
- Focus on the code, not the person
- Assume good intentions
- Help others learn and grow

## 🚀 Getting Started

### Prerequisites

- Python ≥ 3.11
- Node.js ≥ 22
- pnpm (for frontend)
- Docker + Docker Compose (recommended)
- Git

### Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/kalshi-analysis.git
cd kalshi-analysis

# Add upstream remote
git remote add upstream https://github.com/seanbearden/kalshi-analysis.git
```

### Local Development Setup

```bash
# Quick start with Docker
make demo

# Or manual setup:
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# Frontend
cd frontend
pnpm install
```

## 🔧 Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

### 2. Make Your Changes

Follow the [Coding Standards](#coding-standards) below.

### 3. Test Your Changes

```bash
# Backend tests
cd backend
pytest tests/ -v
mypy .
ruff check .

# Frontend tests (when implemented)
cd frontend
pnpm test
pnpm type-check
pnpm lint
```

### 4. Commit Your Work

We use conventional commit messages:

```bash
git commit -m "feat: add real-time WebSocket connection"
git commit -m "fix: resolve order book race condition"
git commit -m "docs: update README with deployment instructions"
git commit -m "test: add backtesting strategy unit tests"
```

**Commit types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `chore`: Build/tooling changes

### 5. Keep Your Branch Updated

```bash
git fetch upstream
git rebase upstream/main
```

### 6. Push and Create PR

```bash
git push origin feature/your-feature-name
# Then create a Pull Request on GitHub
```

## 📐 Coding Standards

### Python (Backend)

**Style and Formatting:**
- Use **Ruff** for linting
- Use **Black** for formatting
- Use **mypy** for type checking
- Follow PEP 8 conventions

**Code Quality:**
- Type hints required for all functions
- Pydantic models for data validation
- Async/await for I/O operations
- Docstrings for public APIs (Google style)

**Example:**
```python
from pydantic import BaseModel
from typing import Optional

async def fetch_market_data(
    ticker: str,
    start_date: Optional[datetime] = None,
) -> MarketSnapshot:
    """Fetch market snapshot from Kalshi API.

    Args:
        ticker: Market ticker symbol
        start_date: Optional start date for historical data

    Returns:
        Market snapshot with current prices and volume

    Raises:
        KalshiAPIError: If API request fails
    """
    ...
```

### TypeScript (Frontend)

**Style and Formatting:**
- Use **ESLint** for linting
- Use **Prettier** for formatting
- Strict TypeScript mode enabled

**Code Quality:**
- Functional components with hooks
- Type-safe props and state
- Consistent naming (PascalCase for components, camelCase for functions)

**Example:**
```typescript
interface MarketCardProps {
  ticker: string;
  title: string;
  yesPrice: number;
  noPrice: number;
}

export function MarketCard({ ticker, title, yesPrice, noPrice }: MarketCardProps) {
  const { data, isLoading } = useMarketQuery(ticker);

  if (isLoading) return <Skeleton />;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      {/* ... */}
    </Card>
  );
}
```

### Pre-commit Hooks

Install pre-commit hooks to automatically check code quality:

```bash
# Backend
cd backend
pip install pre-commit
pre-commit install

# Frontend
cd frontend
pnpm install  # Husky hooks configured in package.json
```

## 🎯 Contribution Areas

### Phase 1 Priorities (Current)

**Backend:**
- [ ] Kalshi API client improvements
- [ ] Database query optimization
- [ ] Backtesting engine enhancements
- [ ] API endpoint additions

**Frontend:**
- [ ] shadcn/ui component integration
- [ ] Recharts visualizations
- [ ] Data table enhancements
- [ ] Responsive design improvements

**Data Science:**
- [ ] New trading strategies
- [ ] Calibration analysis tools
- [ ] Performance metrics
- [ ] Jupyter notebook examples

**Testing:**
- [ ] Backend unit tests (pytest)
- [ ] Frontend component tests (Vitest)
- [ ] Integration tests
- [ ] Property-based tests (Hypothesis)

### Future Phases

Contributions for Phase 2+ features are welcome but may be deferred:
- WebSocket real-time connections
- GraphQL API layer
- Authentication and multi-user support
- Cloud deployment configurations

## 📝 Submitting Contributions

### Pull Request Checklist

Before submitting a PR, ensure:

- [ ] Code follows project style guidelines
- [ ] All tests pass (`pytest`, `pnpm test`)
- [ ] Type checking passes (`mypy`, `pnpm type-check`)
- [ ] Linting passes (`ruff`, `pnpm lint`)
- [ ] Pre-commit hooks are satisfied
- [ ] Documentation updated (if applicable)
- [ ] Commit messages follow conventional format
- [ ] PR description explains the change clearly

### PR Description Template

```markdown
## Description
[Brief description of what this PR does]

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
[Describe how you tested your changes]

## Screenshots (if applicable)
[Add screenshots for UI changes]

## Related Issues
Closes #[issue-number]
```

## 🐛 Reporting Issues

### Bug Reports

When reporting a bug, include:

1. **Description**: Clear description of the issue
2. **Steps to Reproduce**: Detailed steps to reproduce the behavior
3. **Expected Behavior**: What you expected to happen
4. **Actual Behavior**: What actually happened
5. **Environment**:
   - OS: [e.g., macOS 13.0, Ubuntu 22.04]
   - Python version: [e.g., 3.11.5]
   - Node.js version: [e.g., 22.0.0]
   - Docker version: [if applicable]
6. **Logs/Screenshots**: Any relevant error messages or screenshots

### Feature Requests

When requesting a feature:

1. **Use Case**: Describe the problem you're trying to solve
2. **Proposed Solution**: Your idea for how to implement it
3. **Alternatives**: Other approaches you've considered
4. **Phase Alignment**: Which phase this feature fits into (1-4)

## 📚 Additional Resources

- [Project README](README.md) - Architecture and setup
- [CLAUDE.md](CLAUDE.md) - AI assistant context
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

## 🙏 Recognition

Contributors will be recognized in:
- GitHub contributors list
- Release notes (for significant contributions)
- README acknowledgments (for major features)

## ❓ Questions?

- Open a [GitHub Discussion](https://github.com/seanbearden/kalshi-analysis/discussions)
- Create an issue with the `question` label
- Check existing issues and discussions first

---

**Thank you for contributing to Kalshi Market Insights!** 🎉

Your contributions help make this project a better demonstration of modern data science and full-stack engineering practices.
