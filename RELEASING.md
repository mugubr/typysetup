# Releasing TyPySetup

This project publishes to PyPI automatically via GitHub Actions using **OIDC
Trusted Publishing** (no long-lived API tokens).

## One-time setup (Trusted Publishing)

Configure a Trusted Publisher on both registries so GitHub Actions can publish
without secrets. Do this once per registry.

On **https://pypi.org** → *Your project → Settings → Publishing* (or *Account →
Publishing* for the first release), add a GitHub publisher:

| Field             | Value                    |
| ----------------- | ------------------------ |
| Owner             | `mugubr`                 |
| Repository name   | `typysetup`              |
| Workflow name     | `publish-to-pypi.yml`    |
| Environment name  | `pypi`                   |

Repeat on **https://test.pypi.org** with environment name `testpypi`.

The workflow already declares the matching `environment:` blocks and
`permissions: id-token: write`, so no tokens or secrets are required.

## Cutting a release

1. Make sure `master` is green (the **CI** workflow runs ruff, black, mypy, and
   pytest on Python 3.10–3.13).
2. Bump the version in **both** places (they must stay in sync):
   - `src/typysetup/__init__.py` → `__version__`
   - `pyproject.toml` → `version`
3. Update `CHANGELOG.md` with a new `## [X.Y.Z] - YYYY-MM-DD` section.
4. Refresh the lockfile if dependencies changed: `uv lock`.
5. Verify locally:

   ```bash
   uv sync --extra dev
   uv run ruff check src tests
   uv run black --check src tests
   uv run pytest
   uv run --extra release python -m build
   uv run --extra release twine check dist/*
   ```

6. Commit, then tag and push the tag:

   ```bash
   git commit -am "chore: release X.Y.Z"
   git tag vX.Y.Z
   git push origin master --tags
   ```

Pushing a `vX.Y.Z` tag triggers `publish-to-pypi.yml`, which:

1. runs the test gate (Python 3.10 and 3.13),
2. builds the sdist + wheel and runs `twine check`,
3. publishes to **TestPyPI**, then **PyPI** (both via OIDC),
4. creates a **GitHub Release** with auto-generated notes and the built
   artifacts attached.

## Versioning

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** — backwards-incompatible changes (e.g. dropping Python versions).
- **MINOR** — backwards-compatible features.
- **PATCH** — backwards-compatible bug fixes.
