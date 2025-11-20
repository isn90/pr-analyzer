# Reusable Workflow Setup Guide

This PR Analyzer can now be used as a reusable workflow in other repositories without duplicating the code.

## How to Use in Other Repositories

### Step 1: Add Secrets to Your Repository

In the repository you want to analyze, add these GitHub secrets:
- Go to **Settings** → **Secrets and variables** → **Actions**
- Add the following secrets:
  - `AZURE_OPENAI_ENDPOINT` - Your Azure OpenAI endpoint URL
  - `AZURE_OPENAI_API_KEY` - Your Azure OpenAI API key
  - `AZURE_OPENAI_DEPLOYMENT` - Your deployment name (e.g., "gpt-4")

### Step 2: Create Workflow File

In your target repository, create `.github/workflows/pr-analyzer.yml`:

```yaml
name: PR Analyzer

on:
  pull_request:
    branches:
      - develop
      - master
      - main
    types:
      - opened
      - synchronize
      - reopened

jobs:
  analyze:
    uses: YOUR-USERNAME/pr-analyzer/.github/workflows/pr-analyzer.yml@main
    secrets:
      AZURE_OPENAI_ENDPOINT: ${{ secrets.AZURE_OPENAI_ENDPOINT }}
      AZURE_OPENAI_API_KEY: ${{ secrets.AZURE_OPENAI_API_KEY }}
      AZURE_OPENAI_DEPLOYMENT: ${{ secrets.AZURE_OPENAI_DEPLOYMENT }}
    permissions:
      contents: read
      pull-requests: write
      issues: write
```

**Important:** Replace `YOUR-USERNAME` with your GitHub username or organization name where the `pr-analyzer` repository is hosted.

### Step 3: Commit and Push

```bash
git add .github/workflows/pr-analyzer.yml
git commit -m "Add PR analyzer workflow"
git push
```

### Step 4: Test

Create a pull request in your repository targeting `develop`, `master`, or `main` branch. The analyzer will automatically run and post comments.

## Benefits

✅ **No code duplication** - All Python code stays in the `pr-analyzer` repository  
✅ **Easy updates** - Fix bugs once, all repos benefit immediately  
✅ **Minimal setup** - Other repos need only ~20 lines of YAML  
✅ **Centralized maintenance** - Manage dependencies in one place  

## Requirements

- The `pr-analyzer` repository must be:
  - **Public**, OR
  - In the **same organization** as the calling repository with appropriate access
- Calling repository needs `pull-requests: write` permission

## Organization-Level Secrets (Optional)

For multiple repositories, you can set secrets at the organization level:
- Go to **Organization Settings** → **Secrets and variables** → **Actions**
- Add the same secrets there
- All repositories will inherit these secrets

## Troubleshooting

**Error: "Workflow not found"**
- Make sure you replaced `YOUR-USERNAME` with the correct GitHub username/org
- Verify the `pr-analyzer` repository is accessible

**Error: "Secret not found"**
- Check that secrets are added to the calling repository (or organization)
- Secret names must match exactly (case-sensitive)

**Permissions error**
- Ensure the workflow has `pull-requests: write` permission
- Check repository settings allow Actions to create pull request comments
