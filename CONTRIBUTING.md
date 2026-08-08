# Contributing Guidelines

This repo uses **trunk-based development**: short-lived branches off `main`, merge via PR, release with tags.

## Branch Naming: `type/issue-123`

**Requirements:** Lowercase, kebab-case, type prefix

**Valid:** `feature/issue-123`, `bugfix/issue-456`, `hotfix/issue-789`
**Invalid:** `Feature/Issue-123`, `feature/issue_123`, `issue-123`

**Protected branch:** `main` — no force push; PRs required

Do not create long-lived branches (`dev`, `develop`, `release/*`). Ship from `main` and cut releases with tags.

---

## Commit Messages: `issue-123: description`

**Requirements:** Lowercase ticket ref, colon + space

**Valid:** `issue-123: add feature`, `issue-456: fix bug`, `deps-auto: update package`
**Invalid:** `Issue-123: Add feature`, `issue-123 add feature`, `Add feature`

---

## Version Tags: `v*`

**Pattern:** `v<major>.<minor>.<patch>[-<prerelease>]`

**Valid:** `v1.0.0`, `v2.1.3-alpha`, `v1.0.0-beta.1`
**Invalid:** `1.0.0`, `V1.0.0`, `v1.0`

**Protection:** No force updates or deletions

Tag releases from `main` after merge (e.g. `git tag -a v1.0.0 -m "MVP1"` then `git push origin v1.0.0`).

---

## Pull Request Process

1. **Branch from `main`:**
   ```bash
   git checkout main && git pull
   git checkout -b feature/issue-123
   ```

2. **Commit with proper format:**
   ```bash
   git commit -m "issue-123: implement feature"
   ```

3. **Push and create PR into `main`:**
   ```bash
   git push origin feature/issue-123
   gh pr create --base main
   ```

4. **PR Requirements:**
   - Fill out template (auto-populates)
   - Link the GitHub issue
   - 1 approval required (when configured)
   - All status checks pass
   - All conversations resolved

5. **After merge:** Branch auto-deletes; deploy/release from `main` via tags

---

## Pre-commit Hooks (Optional)

Install to validate locally:
```bash
pip install pre-commit
pre-commit install
pre-commit install --hook-type commit-msg
```

---

## Questions?

- Check GitHub Actions logs for specific errors
- See [.github/workflows/README.md](./.github/workflows/README.md)
