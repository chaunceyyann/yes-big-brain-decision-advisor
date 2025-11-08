# Contributing Guidelines

## Branch Naming: `type/jira-123`

**Requirements:** Lowercase, kebab-case, type prefix

**Valid:** `feature/jira-123`, `bugfix/proj-456`, `hotfix/issue-789`
**Invalid:** `Feature/JIRA-123`, `feature/jira_123`, `jira-123`

**Protected branches:** `main`, `dev` - no force push, PR required

---

## Commit Messages: `jira-123: description`

**Requirements:** Lowercase, kebab-case ticket, colon + space

**Valid:** `jira-123: add feature`, `proj-456: fix bug`, `deps-auto: update package`
**Invalid:** `JIRA-123: Add feature`, `jira-123 add feature`, `Add feature`

---

## Version Tags: `v*`

**Pattern:** `v<major>.<minor>.<patch>[-<prerelease>]`

**Valid:** `v1.0.0`, `v2.1.3-alpha`, `v1.0.0-beta.1`
**Invalid:** `1.0.0`, `V1.0.0`, `v1.0`

**Protection:** No force updates or deletions

---

## Pull Request Process

1. **Branch from `dev`:**
   ```bash
   git checkout dev && git pull
   git checkout -b feature/jira-123
   ```

2. **Commit with proper format:**
   ```bash
   git commit -m "jira-123: implement feature"
   ```

3. **Push and create PR:**
   ```bash
   git push origin feature/jira-123
   ```

4. **PR Requirements:**
   - Fill out template (auto-populates)
   - Link JIRA ticket
   - 1 approval required
   - All status checks pass: `pr-checks`, `static-code-scan`, `terraform-plan`
   - All conversations resolved

5. **After merge:** Branch auto-deletes

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
- Review [rulesets/README.md](./rulesets/README.md)
- See [.github/workflows/README.md](./.github/workflows/README.md)
