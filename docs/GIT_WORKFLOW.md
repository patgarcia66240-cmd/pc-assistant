# Git Workflow

## Branch Strategy

- `main` - Production ready code
- `develop` - Development branch
- `feature/*` - Feature branches
- `bugfix/*` - Bug fix branches

## Committing

Use conventional commits:

```
feat: Add new feature
fix: Fix a bug
docs: Update documentation
refactor: Refactor code
test: Add tests
chore: Update dependencies
```

Example:
```bash
git commit -m "feat: Add voice input support to chat"
```

## Pull Requests

1. Create feature branch: `git checkout -b feature/feature-name`
2. Make changes and commit
3. Push: `git push origin feature/feature-name`
4. Create PR with description
5. Wait for review
6. Merge to develop
7. Later, merge develop to main for release

## Releases

Version format: `v0.1.0`

Create tag:
```bash
git tag -a v0.1.0 -m "Release version 0.1.0"
git push origin v0.1.0
```
