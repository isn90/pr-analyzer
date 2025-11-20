"""
GitHub provider implementation
"""

from typing import Dict, List, Any, Optional
from github import Github, GithubException

from .base_provider import BaseProvider
from ..utils.logger import get_logger

logger = get_logger()


class GitHubProvider(BaseProvider):
    """GitHub repository provider."""
    
    def __init__(self, repository: str, token: str):
        """
        Initialize GitHub provider.
        
        Args:
            repository: Repository name in format 'owner/repo'
            token: GitHub Personal Access Token
        """
        self.repository_name = repository
        self.github = Github(token)
        self.repo = self.github.get_repo(repository)
        
        logger.info(f"Initialized GitHub provider for {repository}")
    
    def get_pull_request(self, pr_id: str) -> Dict[str, Any]:
        """Get pull request details."""
        try:
            pr = self.repo.get_pull(int(pr_id))
            
            return {
                'id': pr.number,
                'title': pr.title,
                'description': pr.body,
                'author': pr.user.login,
                'source_branch': pr.head.ref,
                'target_branch': pr.base.ref,
                'status': pr.state,
                'created_date': pr.created_at,
                'url': pr.html_url
            }
        except GithubException as e:
            logger.error(f"Error fetching PR details: {e}")
            raise
    
    def get_changed_files(self, pr_id: str) -> List[Dict[str, Any]]:
        """Get list of changed files in the PR."""
        try:
            pr = self.repo.get_pull(int(pr_id))
            files = []
            
            for file in pr.get_files():
                files.append({
                    'path': file.filename,
                    'change_type': file.status,
                    'size': file.changes,
                    'additions': file.additions,
                    'deletions': file.deletions,
                    'patch': file.patch if hasattr(file, 'patch') else None
                })
            
            return files
            
        except GithubException as e:
            logger.error(f"Error fetching changed files: {e}")
            raise
    
    def get_file_content(self, file_path: str, commit_id: Optional[str] = None) -> str:
        """Get content of a file."""
        try:
            if commit_id:
                content = self.repo.get_contents(file_path, ref=commit_id)
            else:
                content = self.repo.get_contents(file_path)
            
            if isinstance(content, list):
                return ""
            
            return content.decoded_content.decode('utf-8')
            
        except GithubException as e:
            logger.warning(f"Error fetching file content for {file_path}: {e}")
            return ""
    
    def post_comment(self, pr_id: str, comment: str) -> bool:
        """Post a comment on the pull request."""
        try:
            pr = self.repo.get_pull(int(pr_id))
            pr.create_issue_comment(comment)
            
            logger.info(f"Posted summary comment to PR {pr_id}")
            return True
            
        except GithubException as e:
            logger.error(f"Error posting comment: {e}")
            return False
    
    def post_inline_comment(
        self,
        pr_id: str,
        file_path: str,
        line_number: int,
        comment: str,
        position: int = None
    ) -> bool:
        """Post an inline comment on a specific line or diff position."""
        try:
            pr = self.repo.get_pull(int(pr_id))
            
            # Get the latest commit
            commits = list(pr.get_commits())
            if not commits:
                logger.warning("No commits found in PR")
                return False
            
            latest_commit = commits[-1]
            
            # If position is provided, use it for diff-based comment
            # Otherwise use line number for file-based comment
            if position is not None:
                # Position-based comment (diff line position)
                pr.create_review_comment(
                    body=comment,
                    commit=latest_commit,
                    path=file_path,
                    position=position  # Position in the diff
                )
                logger.debug(f"Posted inline comment to {file_path} at diff position {position}")
            else:
                # Line-based comment (file line number)
                pr.create_review_comment(
                    body=comment,
                    commit=latest_commit,
                    path=file_path,
                    line=line_number
                )
                logger.debug(f"Posted inline comment to {file_path}:{line_number}")
            
            return True
            
        except GithubException as e:
            logger.error(f"Error posting inline comment to {file_path}: {e.status} - {e.data}")
            return False
    
    def get_file_diff(self, pr_id: str, file_path: str) -> str:
        """Get the diff for a specific file."""
        try:
            pr = self.repo.get_pull(int(pr_id))
            
            for file in pr.get_files():
                if file.filename == file_path:
                    return file.patch if hasattr(file, 'patch') else ""
            
            return ""
            
        except GithubException as e:
            logger.warning(f"Error fetching file diff for {file_path}: {e}")
            return ""
