# Workflows

## Active Workflows

### `pr-checks.yaml`
Runs on pull requests to `main` and `dev` branches. Performs:
- **Pre-commit checks** - Code linting and formatting validation
- **Terraform lint** - Infrastructure code validation
- **PR status comment** - Posts a comment on the PR with check results

This workflow ensures code quality and consistency before merging.

---

## Troubleshooting

**Workflow doesn't run?**
- Check that GitHub Actions is enabled in repository settings
- Verify the PR is targeting `main` or `dev` branch

**Checks failing?**
- Review the workflow logs in the Actions tab
- Ensure your code follows the project's style guidelines
- Run pre-commit hooks locally before pushing
