# Workflows

## Active Workflows

### `fork-governance.yaml`
Triggers on fork - automatically sets up governance on forked repos.

### `apply-rulesets.yaml`
Triggers on push to `main` with `/rulesets/**` changes - auto-applies ruleset updates.

---

## Setup Required: GH_PAT Secret

Create Personal Access Token with scopes:
- `repo` - Full repository access
- `administration:write` - Manage rulesets

**Steps:**
1. GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token (classic)
3. Select scopes: `repo`, `admin:repo_hook`
4. Copy token
5. Add to template repo: Settings → Secrets → Actions → New secret
6. Name: `GH_PAT`, Value: your token

---

## What Fork Governance Does

When someone forks:
1. Validates repo name (`aws-*` lowercase kebab-case)
2. Applies all 5 rulesets
3. Creates `dev` branch, sets as default
4. Creates environments: `dev`, `staging`, `prod`
5. Enables Dependabot, vulnerability alerts, auto-delete branches
6. Checks README/CONTRIBUTING updated
7. Creates setup issue with instructions

---

## Required Status Check Workflows

Create these (referenced by rulesets):
- `pr-checks.yaml` - Linting, testing
- `static-code-scan.yaml` - Security scanning
- `terraform-plan.yaml` - Infrastructure validation

---

## Troubleshooting

**Workflow doesn't run?** Check GitHub Actions enabled

**"Resource not accessible"?** PAT missing or wrong scopes

**Rulesets not applying?** Check PAT has `administration:write`, verify JSON valid
