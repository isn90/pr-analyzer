"""
GitLab provider implementation
"""

import os
from typing import Dict, List, Any, Optional
import gitlab
from gitlab.exceptions import GitlabError

from .base_provider import BaseProvider
from ..utils.logger import get_logger

logger = get_logger()


class GitLabProvider(BaseProvider):
    """GitLab repository provider."""
    
    def __init__(
        self,
        gitlab_url: str,
        project_id: str,
        token: str
    ):
        """
        Initialize GitLab provider.
        
        Args:
            gitlab_url: GitLab instance URL (e.g., 'https://gitlab.com' or 'https://autocode.git.epam.com')
            project_id: Project ID or path (e.g., 'shivshankar_natarajan/pr-analyzer')
            token: GitLab Personal Access Token or Job Token
        """
        self.gitlab_url = gitlab_url.rstrip('/')
        self.project_id = project_id
        
        # Create GitLab connection
        self.gl = gitlab.Gitlab(self.gitlab_url, private_token=token)
        self.gl.auth()
        
        # Get project
        self.project = self.gl.projects.get(project_id)
        
        logger.info(f"Initialized GitLab provider for {gitlab_url}/{project_id}")
    
    def get_pull_request(self, pr_id: str) -> Dict[str, Any]:
        """Get merge request details."""
        try:
            mr = self.project.mergerequests.get(int(pr_id))
            
            return {
                'id': mr.iid,
                'title': mr.title,
                'description': mr.description,
                'author': mr.author.get('name', 'Unknown') if mr.author else 'Unknown',
                'source_branch': mr.source_branch,
                'target_branch': mr.target_branch,
                'status': mr.state,
                'created_date': mr.created_at,
                'url': mr.web_url
            }
        except GitlabError as e:
            logger.error(f"Error fetching MR details: {e}")
            raise
    
    def get_changed_files(self, pr_id: str) -> List[Dict[str, Any]]:
        """Get list of changed files in the MR."""
        try:
            mr = self.project.mergerequests.get(int(pr_id))
            changes = mr.changes()
            
            files = []
            for change in changes.get('changes', []):
                files.append({
                    'path': change.get('new_path', change.get('old_path', '')),
                    'old_path': change.get('old_path', ''),
                    'new_path': change.get('new_path', ''),
                    'change_type': self._determine_change_type(change),
                    'new_file': change.get('new_file', False),
                    'deleted_file': change.get('deleted_file', False),
                    'renamed_file': change.get('renamed_file', False),
                    'diff': change.get('diff', '')
                })
            
            return files
            
        except GitlabError as e:
            logger.error(f"Error fetching changed files: {e}")
            raise
    
    def _determine_change_type(self, change: Dict[str, Any]) -> str:
        """Determine the type of change from GitLab change object."""
        if change.get('new_file'):
            return 'added'
        elif change.get('deleted_file'):
            return 'deleted'
        elif change.get('renamed_file'):
            return 'renamed'
        else:
            return 'modified'
    
    def get_file_content(self, file_path: str, commit_id: Optional[str] = None) -> str:
        """Get content of a file."""
        try:
            ref = commit_id if commit_id else self.project.default_branch
            file = self.project.files.get(file_path=file_path, ref=ref)
            
            # Decode content (it's base64 encoded)
            import base64
            content = base64.b64decode(file.content).decode('utf-8')
            return content
            
        except GitlabError as e:
            logger.warning(f"Error fetching file content for {file_path}: {e}")
            return ""
    
    def post_comment(self, pr_id: str, comment: str) -> bool:
        """Post a comment on the merge request."""
        try:
            mr = self.project.mergerequests.get(int(pr_id))
            mr.notes.create({'body': comment})
            
            logger.info(f"Posted summary comment to MR {pr_id}")
            return True
            
        except GitlabError as e:
            logger.error(f"Error posting comment: {e}")
            return False
    
    def post_inline_comment(
        self,
        pr_id: str,
        file_path: str,
        line_number: int,
        comment: str
    ) -> bool:
        """Post an inline comment on a specific line."""
        try:
            mr = self.project.mergerequests.get(int(pr_id))
            
            # Get MR changes to find the diff position
            changes = mr.changes()
            
            # Find the file in changes
            target_change = None
            for change in changes.get('changes', []):
                if change.get('new_path') == file_path or change.get('old_path') == file_path:
                    target_change = change
                    break
            
            if not target_change:
                logger.warning(f"File {file_path} not found in MR changes")
                return False
            
            # Create discussion on the diff
            # GitLab uses position-based comments
            position = {
                'base_sha': changes.get('diff_refs', {}).get('base_sha'),
                'start_sha': changes.get('diff_refs', {}).get('start_sha'),
                'head_sha': changes.get('diff_refs', {}).get('head_sha'),
                'position_type': 'text',
                'new_path': target_change.get('new_path'),
                'old_path': target_change.get('old_path'),
                'new_line': line_number if not target_change.get('deleted_file') else None,
                'old_line': line_number if target_change.get('deleted_file') else None,
            }
            
            discussion_data = {
                'body': comment,
                'position': position
            }
            
            mr.discussions.create(discussion_data)
            
            logger.debug(f"Posted inline comment to {file_path}:{line_number}")
            return True
            
        except GitlabError as e:
            logger.error(f"Error posting inline comment: {e}")
            logger.debug(f"Error details: {str(e)}")
            return False
    
    def get_file_diff(self, pr_id: str, file_path: str) -> str:
        """Get the diff for a specific file."""
        try:
            mr = self.project.mergerequests.get(int(pr_id))
            changes = mr.changes()
            
            for change in changes.get('changes', []):
                if change.get('new_path') == file_path or change.get('old_path') == file_path:
                    return change.get('diff', '')
            
            return ""
            
        except GitlabError as e:
            logger.warning(f"Error fetching file diff for {file_path}: {e}")
            return ""
