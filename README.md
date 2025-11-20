# PR Analyzer

An automated tool that analyzes pull requests using Azure OpenAI to ensure code quality and best practices. Supports Azure DevOps, GitHub, and GitLab repositories.

## Features

- 🤖 **AI-Powered Analysis**: Uses Azure OpenAI to analyze code changes
- 🔍 **Comprehensive Checks**: 
  - Code quality and best practices
  - Security vulnerabilities
  - Performance issues
  - Code style and formatting
  - Potential bugs
  - Documentation completeness
- 💬 **Dual Reporting**: Posts both summary comments and inline code comments
- 🔄 **Multi-Platform**: Supports Azure DevOps, GitHub, and GitLab repositories
- ⚡ **Automated**: Runs automatically on PRs/MRs to develop/master branches

## Prerequisites

- Python 3.12+
- Azure OpenAI service endpoint and API key
- Repository access token:
  - Azure DevOps: Personal Access Token (PAT)
  - GitHub: Personal Access Token
  - GitLab: Personal Access Token or Job Token

## Setup

### For GitLab

#### 1. Add CI/CD Variables

Go to **Settings > CI/CD > Variables** and add:

- `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI endpoint URL
- `AZURE_OPENAI_API_KEY`: Your Azure OpenAI API key (mark as **Masked**)
- `AZURE_OPENAI_DEPLOYMENT`: Your deployment name (e.g., "gpt-4")
- `GITLAB_TOKEN`: Personal Access Token with `api` scope (mark as **Masked**)

**Note**: `CI_JOB_TOKEN` is automatically available but has limited permissions. For posting comments, use a Personal Access Token.

#### 2. The `.gitlab-ci.yml` File

The `.gitlab-ci.yml` file is already included in this repository. It will:
- Run automatically on merge requests
- Install dependencies
- Execute the PR analyzer
- Post comments to your MR

#### 3. Create Personal Access Token

1. Go to **User Settings > Access Tokens**
2. Create a new token with `api` scope
3. Add it as `GITLAB_TOKEN` in CI/CD Variables

### For Azure DevOps

#### 1. Configure Azure DevOps Pipeline

Add the following variables to your Azure DevOps pipeline or variable group:

- `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI endpoint URL
- `AZURE_OPENAI_API_KEY`: Your Azure OpenAI API key
- `AZURE_OPENAI_DEPLOYMENT`: Your Azure OpenAI deployment name (e.g., "gpt-4")
- `AZURE_DEVOPS_PAT`: Azure DevOps Personal Access Token

#### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 3. Add to Azure Pipeline

Create or update `azure-pipelines.yml` in your repository:

```yaml
trigger: none

pr:
  branches:
    include:
      - develop
      - master
      - main

pool:
  vmImage: 'ubuntu-latest'

steps:
  - task: UsePythonVersion@0
    inputs:
      versionSpec: '3.12'
    displayName: 'Use Python 3.12'

  - script: |
      pip install -r requirements.txt
    displayName: 'Install dependencies'

  - script: |
      python main.py
    displayName: 'Analyze Pull Request'
    env:
      AZURE_OPENAI_ENDPOINT: $(AZURE_OPENAI_ENDPOINT)
      AZURE_OPENAI_API_KEY: $(AZURE_OPENAI_API_KEY)
      AZURE_OPENAI_DEPLOYMENT: $(AZURE_OPENAI_DEPLOYMENT)
      AZURE_DEVOPS_PAT: $(AZURE_DEVOPS_PAT)
      SYSTEM_PULLREQUEST_PULLREQUESTID: $(System.PullRequest.PullRequestId)
      BUILD_REPOSITORY_PROVIDER: $(Build.Repository.Provider)
      BUILD_REPOSITORY_NAME: $(Build.Repository.Name)
      SYSTEM_TEAMFOUNDATIONCOLLECTIONURI: $(System.TeamFoundationCollectionUri)
      SYSTEM_TEAMPROJECT: $(System.TeamProject)
```

### For GitHub

See `.github/workflows/pr-analyzer.yml` for GitHub Actions setup.

## Configuration

Edit `config.yaml` to customize analysis behavior:

```yaml
analysis:
  max_file_size: 100000  # Skip files larger than this (bytes)
  max_files: 50          # Maximum files to analyze per PR
  
openai:
  model: "gpt-4"
  temperature: 0.3
  max_tokens: 2000
  
reporting:
  summary_enabled: true
  inline_comments_enabled: true
  severity_levels:
    - critical
    - high
    - medium
    - low
```

## Usage

### Manual Run (Development/Testing)

```bash
# Set environment variables
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_API_KEY="your-api-key"
export AZURE_OPENAI_DEPLOYMENT="gpt-4"

# For Azure DevOps PR
export AZURE_DEVOPS_PAT="your-pat"
export SYSTEM_PULLREQUEST_PULLREQUESTID="123"
export BUILD_REPOSITORY_PROVIDER="TfsGit"
export SYSTEM_TEAMFOUNDATIONCOLLECTIONURI="https://dev.azure.com/your-org/"
export SYSTEM_TEAMPROJECT="YourProject"
export BUILD_REPOSITORY_NAME="YourRepo"

# For GitHub PR
export GITHUB_TOKEN="your-github-token"
export BUILD_REPOSITORY_PROVIDER="GitHub"
export BUILD_REPOSITORY_NAME="owner/repo"
export SYSTEM_PULLREQUEST_PULLREQUESTID="123"

# For GitLab MR
export GITLAB_TOKEN="your-gitlab-token"
export BUILD_REPOSITORY_PROVIDER="GitLab"
export CI_SERVER_URL="https://gitlab.com"  # or your GitLab instance URL
export CI_PROJECT_PATH="namespace/project"
export SYSTEM_PULLREQUEST_PULLREQUESTID="123"  # MR IID

# Run the analyzer
python main.py
```

### Automatic Run

The tool runs automatically when configured in your CI/CD pipeline:
- **Azure DevOps**: Add to `azure-pipelines.yml`
- **GitHub**: Use GitHub Actions workflow
- **GitLab**: Add `.gitlab-ci.yml` (see below)

## Project Structure

```
pr-analyzer/
├── main.py                 # Entry point
├── src/
│   ├── __init__.py
│   ├── analyzers/
│   │   ├── __init__.py
│   │   ├── ai_analyzer.py      # Azure OpenAI integration
│   │   └── code_analyzer.py    # Code analysis logic
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base_provider.py    # Base provider interface
│   │   ├── azure_devops.py     # Azure DevOps API client
│   │   ├── github.py           # GitHub API client
│   │   └── gitlab.py           # GitLab API client
│   ├── reporters/
│   │   ├── __init__.py
│   │   └── pr_reporter.py      # PR commenting logic
│   └── utils/
│       ├── __init__.py
│       ├── config.py           # Configuration management
│       └── logger.py           # Logging utilities
├── config.yaml             # Configuration file
├── requirements.txt        # Python dependencies
├── .gitlab-ci.yml         # GitLab CI/CD pipeline
├── .env.example           # Environment variables template
├── .gitignore
└── README.md
```

## How It Works

1. **PR/MR Detection**: Detects when a PR/MR is created or updated
2. **Fetch Changes**: Retrieves all changed files and their diffs
3. **AI Analysis**: Sends code changes to Azure OpenAI for analysis
4. **Generate Report**: Creates comprehensive analysis report
5. **Post Comments**: 
   - Posts summary comment on PR/MR
   - Posts inline comments on specific code issues
6. **Complete**: Pipeline completes, developers can review feedback

## Example Output

### Summary Comment
```markdown
## 🤖 AI Code Review Summary

**Overall Assessment**: 3 files analyzed, 5 issues found

### Critical Issues (1)
- Potential SQL injection vulnerability in `api/database.py`

### High Priority (2)
- Missing error handling in `services/user_service.py`
- Unvalidated user input in `controllers/auth_controller.py`

### Medium Priority (2)
- Inconsistent naming conventions in `utils/helpers.py`
- Missing docstrings in public methods

**Recommendation**: Please address critical and high priority issues before merging.
```

### Inline Comment Example
```
⚠️ **Security Issue - High Priority**

Potential SQL injection vulnerability detected. User input is directly concatenated into SQL query.

**Recommendation**: Use parameterized queries or an ORM to prevent SQL injection.

**Example Fix**:
```python
# Instead of:
query = f"SELECT * FROM users WHERE id = {user_id}"

# Use:
query = "SELECT * FROM users WHERE id = ?"
cursor.execute(query, (user_id,))
```
```

## Troubleshooting

### Common Issues

**Issue**: Pipeline fails with authentication error
- **Solution**: Verify your PAT tokens have correct permissions (Code: Read & Write)

**Issue**: No comments posted on PR
- **Solution**: Check pipeline logs for errors, verify tokens are set correctly

**Issue**: Rate limiting errors
- **Solution**: Reduce `max_files` in config.yaml or add retry logic

## License

MIT License

## Contributing

Contributions welcome! Please open an issue or submit a PR.
