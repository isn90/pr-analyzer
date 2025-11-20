"""
PR Analyzer - Main Entry Point
Analyzes pull requests using Azure OpenAI and posts comprehensive reports.
"""

import os
import sys
from typing import Optional
from dotenv import load_dotenv

from src.utils.logger import setup_logger
from src.utils.config import Config
from src.providers.azure_devops import AzureDevOpsProvider
from src.providers.github import GitHubProvider
from src.providers.gitlab import GitLabProvider
from src.analyzers.code_analyzer import CodeAnalyzer
from src.reporters.pr_reporter import PRReporter

# Load .env file for local development (ignored in CI/CD)
load_dotenv()


def get_provider():
    """Determine and return the appropriate provider based on environment."""
    provider_type = os.getenv('BUILD_REPOSITORY_PROVIDER', 'TfsGit')
    
    if provider_type == 'TfsGit':
        logger.info("Using Azure DevOps provider")
        return AzureDevOpsProvider(
            organization_url=os.getenv('SYSTEM_TEAMFOUNDATIONCOLLECTIONURI'),
            project=os.getenv('SYSTEM_TEAMPROJECT'),
            repository=os.getenv('BUILD_REPOSITORY_NAME'),
            pat=os.getenv('AZURE_DEVOPS_PAT')
        )
    elif provider_type == 'GitHub':
        logger.info("Using GitHub provider")
        repo_name = os.getenv('BUILD_REPOSITORY_NAME')
        return GitHubProvider(
            repository=repo_name,
            token=os.getenv('GITHUB_TOKEN')
        )
    elif provider_type == 'GitLab':
        logger.info("Using GitLab provider")
        gitlab_url = os.getenv('CI_SERVER_URL', os.getenv('GITLAB_URL'))
        project_id = os.getenv('CI_PROJECT_PATH', os.getenv('GITLAB_PROJECT'))
        token = os.getenv('GITLAB_TOKEN', os.getenv('CI_JOB_TOKEN'))
        
        return GitLabProvider(
            gitlab_url=gitlab_url,
            project_id=project_id,
            token=token
        )
    else:
        raise ValueError(f"Unsupported repository provider: {provider_type}")


def main():
    """Main execution flow."""
    global logger
    
    # Setup
    config = Config()
    logger = setup_logger(config)
    
    logger.info("=" * 80)
    logger.info("PR Analyzer Starting")
    logger.info("=" * 80)
    
    try:
        # Get PR ID
        pr_id = os.getenv('SYSTEM_PULLREQUEST_PULLREQUESTID')
        if not pr_id:
            logger.error("No pull request ID found. This script should run in a PR context.")
            sys.exit(1)
        
        logger.info(f"Analyzing Pull Request: {pr_id}")
        
        # Initialize provider
        provider = get_provider()
        
        # Get PR details
        logger.info("Fetching PR details...")
        pr_details = provider.get_pull_request(pr_id)
        logger.info(f"PR Title: {pr_details.get('title', 'N/A')}")
        logger.info(f"PR Author: {pr_details.get('author', 'N/A')}")
        
        # Get changed files
        logger.info("Fetching changed files...")
        changed_files = provider.get_changed_files(pr_id)
        logger.info(f"Found {len(changed_files)} changed files")
        
        if not changed_files:
            logger.warning("No files to analyze. Exiting.")
            return
        
        # Filter files based on config
        filtered_files = filter_files(changed_files, config)
        logger.info(f"Analyzing {len(filtered_files)} files after filtering")
        
        if not filtered_files:
            logger.warning("No files to analyze after filtering. Exiting.")
            return
        
        # Initialize analyzer
        analyzer = CodeAnalyzer(config)
        
        # Analyze files
        logger.info("Starting AI analysis...")
        analysis_results = analyzer.analyze_pr(filtered_files, pr_details)
        
        # Generate and post report
        logger.info("Generating report...")
        reporter = PRReporter(provider, config)
        reporter.post_report(pr_id, analysis_results)
        
        logger.info("=" * 80)
        logger.info("PR Analyzer Completed Successfully")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Error during PR analysis: {str(e)}", exc_info=True)
        sys.exit(1)


def filter_files(files: list, config: Config) -> list:
    """Filter files based on configuration settings."""
    filtered = []
    
    for file_info in files:
        path = file_info.get('path', '')
        
        # Check if file is in excluded directory
        excluded = False
        for exclude_dir in config.get('analysis.exclude_directories', []):
            if exclude_dir in path:
                excluded = True
                break
        
        if excluded:
            logger.debug(f"Excluding {path} (in excluded directory)")
            continue
        
        # Check file extension
        include_extensions = config.get('analysis.include_extensions', [])
        if include_extensions:
            if not any(path.endswith(ext) for ext in include_extensions):
                logger.debug(f"Excluding {path} (extension not in include list)")
                continue
        
        # Check file size
        max_size = config.get('analysis.max_file_size', 100000)
        file_size = file_info.get('size', 0)
        if file_size > max_size:
            logger.debug(f"Excluding {path} (file too large: {file_size} bytes)")
            continue
        
        filtered.append(file_info)
        
        # Check max files limit
        if len(filtered) >= config.get('analysis.max_files', 50):
            logger.warning(f"Reached maximum file limit ({config.get('analysis.max_files')})")
            break
    
    return filtered


if __name__ == "__main__":
    main()
