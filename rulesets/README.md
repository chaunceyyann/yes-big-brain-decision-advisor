# Repository Rulesets

## Quick Apply

```bash
cd rulesets
gh api repos/:owner/:repo/rulesets --method POST --input main.json
gh api repos/:owner/:repo/rulesets --method POST --input dev.json
gh api repos/:owner/:repo/rulesets --method POST --input tag-protection.json
gh api repos/:owner/:repo/rulesets --method POST --input branch-naming.json
gh api repos/:owner/:repo/rulesets --method POST --input commit-message.json
```

Or push to `main` - `.github/workflows/apply-rulesets.yaml` auto-applies.

**Fork?** Rulesets auto-apply via `.github/workflows/fork-governance.yaml` (requires `GH_PAT` secret).

## What Each Does

| Ruleset | Enforces | Pattern/Rule |
|---------|----------|--------------|
| `main.json` | Branch protection | 1 PR approval + 3 status checks, no force push/delete |
| `dev.json` | Branch protection | 1 PR approval + 3 status checks, no force push/delete |
| `tag-protection.json` | Tag protection | Protects `v*` tags, no force push/delete |
| `branch-naming.json` | Branch names | `type/jira-123` (lowercase, kebab-case) |
| `commit-message.json` | Commit messages | `jira-123: description` (lowercase) |

## Required Status Checks

Before merging to `main` or `dev`, these must pass:
- `pr-checks` - linting, testing
- `static-code-scan` - security scanning
- `terraform-plan` - infrastructure validation

**Create these workflows** in `.github/workflows/` with matching names.

## Rules Quick Reference

**Branch naming:**
- ✓ `feature/jira-123`, `bugfix/proj-456`
- ✗ `Feature/JIRA-123`, `feature/jira_123`

**Commit messages:**
- ✓ `jira-123: add feature`, `proj-456: fix bug`, `deps-auto: update package`
- ✗ `Add feature`, `JIRA-123: Add feature`

**Version tags:**
- ✓ `v1.0.0`, `v2.1.3-alpha`
- ✗ `1.0.0`, `V1.0.0`

**Protected branches:**
- `main`, `dev` - no direct push, no force push, no delete

## Testing

```bash
# Branch naming
git checkout -b feature/jira-123  # ✓
git checkout -b Feature/JIRA-123  # ✗

# Commit message
git commit -m "jira-123: add feature"  # ✓
git commit -m "Add feature"            # ✗

# Tag protection
git tag v1.0.0 && git push origin v1.0.0  # ✓
git push --force origin v1.0.0             # ✗

# Force push (blocked)
git push --force origin main  # ✗
```

## Troubleshooting

**Rulesets not applying?** Check admin permissions and JSON validity.

**Status checks not passing?** Create the required workflow files.

**Branch/commit rejected?** Use lowercase, kebab-case, and correct pattern.
