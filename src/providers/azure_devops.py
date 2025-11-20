"""
Azure DevOps provider implementation
"""

import os
from typing import Dict, List, Any, Optional
from azure.devops.connection import Connection
from azure.devops.v7_1.git import GitClient
from msrest.authentication import BasicAuthentication

from .base_provider import BaseProvider
from ..utils.logger import get_logger

logger = get_logger()


class AzureDevOpsProvider(BaseProvider):
    """Azure DevOps repository provider."""
    
    def __init__(
        self,
        organization_url: str,
        project: str,
        repository: str,
        pat: str
    ):
        """
        Initialize Azure DevOps provider.
        
        Args:
            organization_url: Azure DevOps organization URL
            project: Project name
            repository: Repository name
            pat: Personal Access Token
        """
        self.organization_url = organization_url.rstrip('/')
        self.project = project
        self.repository = repository
        
        # Create connection
        credentials = BasicAuthentication('', pat)
        self.connection = Connection(base_url=self.organization_url, creds=credentials)
        self.git_client: GitClient = self.connection.clients.get_git_client()
        
        logger.info(f"Initialized Azure DevOps provider for {organization_url}/{project}/{repository}")
    
    def get_pull_request(self, pr_id: str) -> Dict[str, Any]:
        """Get pull request details."""
        try:
            pr = self.git_client.get_pull_request(
                self.repository,
                int(pr_id),
                project=self.project
            )
            
            return {
                'id': pr.pull_request_id,
                'title': pr.title,
                'description': pr.description,
                'author': pr.created_by.display_name if pr.created_by else 'Unknown',
                'source_branch': pr.source_ref_name,
                'target_branch': pr.target_ref_name,
                'status': pr.status,
                'created_date': pr.creation_date,
                'url': f"{self.organization_url}/{self.project}/_git/{self.repository}/pullrequest/{pr_id}"
            }
        except Exception as e:
            logger.error(f"Error fetching PR details: {e}")
            raise
    
    def get_changed_files(self, pr_id: str) -> List[Dict[str, Any]]:
        """Get list of changed files in the PR."""
        try:
            # Get PR details first
            pr = self.git_client.get_pull_request(
                self.repository,
                int(pr_id),
                project=self.project
            )
            
            # Get commits in the PR
            commits = self.git_client.get_pull_request_commits(
                self.repository,
                int(pr_id),
                project=self.project
            )
            
            if not commits:
                return []
            
            # Get changes for the last commit
            last_commit_id = commits[-1].commit_id
            
            # Get commit changes
            changes = self.git_client.get_changes(
                last_commit_id,
                self.repository,
                project=self.project
            )
            
            files = []
            for change in changes.changes:
                if change.item and change.item.path:
                    files.append({
                        'path': change.item.path.lstrip('/'),
                        'change_type': str(change.change_type),
                        'size': change.item.size if hasattr(change.item, 'size') else 0,
                        'object_id': change.item.object_id
                    })
            
            return files
            
        except Exception as e:
            logger.error(f"Error fetching changed files: {e}")
            raise
    
    def get_file_content(self, file_path: str, commit_id: Optional[str] = None) -> str:
        """Get content of a file."""
        try:
            item = self.git_client.get_item(
                self.repository,
                file_path,
                project=self.project,
                version_descriptor={'version': commit_id} if commit_id else None,
                include_content=True
            )
            
            return item.content if item.content else ""
            
        except Exception as e:
            logger.warning(f"Error fetching file content for {file_path}: {e}")
            return ""
    
    def post_comment(self, pr_id: str, comment: str) -> bool:
        """Post a comment on the pull request."""
        try:
            from azure.devops.v7_1.git.models import Comment, CommentThread
            
            thread = CommentThread()
            thread.comments = [Comment(content=comment)]
            thread.status = 1  # Active
            
            self.git_client.create_thread(
                thread,
                self.repository,
                int(pr_id),
                project=self.project
            )
            
            logger.info(f"Posted summary comment to PR {pr_id}")
            return True
            
        except Exception as e:
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
        """Post an inline comment on a specific line."""
        try:
            from azure.devops.v7_1.git.models import Comment, CommentThread, CommentThreadContext
            
            # Create thread context
            context = CommentThreadContext()
            context.file_path = f"/{file_path}"
            context.right_file_start = {'line': line_number, 'offset': 1}
            context.right_file_end = {'line': line_number, 'offset': 1}
            
            # Create thread
            thread = CommentThread()
            thread.comments = [Comment(content=comment)]
            thread.status = 1  # Active
            thread.thread_context = context
            
            self.git_client.create_thread(
                thread,
                self.repository,
                int(pr_id),
                project=self.project
            )
            
            logger.debug(f"Posted inline comment to {file_path}:{line_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error posting inline comment: {e}")
            return False
    
    def get_file_diff(self, pr_id: str, file_path: str) -> str:
        """Get the diff for a specific file."""
        try:
            pr = self.git_client.get_pull_request(
                self.repository,
                int(pr_id),
                project=self.project
            )
            
            # Get diff between source and target
            diff = self.git_client.get_items_batch(
                {
                    'itemDescriptors': [{
                        'path': file_path,
                        'versionType': 'branch',
                        'version': pr.source_ref_name
                    }]
                },
                self.repository,
                project=self.project
            )
            
            # This is a simplified version - actual diff would require more complex logic
            return str(diff)
            
        except Exception as e:
            logger.warning(f"Error fetching file diff for {file_path}: {e}")
            return ""
