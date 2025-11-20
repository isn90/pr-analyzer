"""
Base provider interface for repository management
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class BaseProvider(ABC):
    """Abstract base class for repository providers."""
    
    @abstractmethod
    def get_pull_request(self, pr_id: str) -> Dict[str, Any]:
        """
        Get pull request details.
        
        Args:
            pr_id: Pull request ID
            
        Returns:
            Dictionary containing PR details
        """
        pass
    
    @abstractmethod
    def get_changed_files(self, pr_id: str) -> List[Dict[str, Any]]:
        """
        Get list of changed files in the PR.
        
        Args:
            pr_id: Pull request ID
            
        Returns:
            List of dictionaries containing file information
        """
        pass
    
    @abstractmethod
    def get_file_content(self, file_path: str, commit_id: Optional[str] = None) -> str:
        """
        Get content of a file.
        
        Args:
            file_path: Path to the file
            commit_id: Specific commit ID (optional)
            
        Returns:
            File content as string
        """
        pass
    
    @abstractmethod
    def post_comment(self, pr_id: str, comment: str) -> bool:
        """
        Post a comment on the pull request.
        
        Args:
            pr_id: Pull request ID
            comment: Comment text
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def post_inline_comment(
        self,
        pr_id: str,
        file_path: str,
        line_number: int,
        comment: str,
        position: int = None
    ) -> bool:
        """
        Post an inline comment on a specific line.
        
        Args:
            pr_id: Pull request ID
            file_path: Path to the file
            line_number: Line number in the new file for the comment
            comment: Comment text
            position: Position in the diff (optional, for diff-based comments)
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_file_diff(self, pr_id: str, file_path: str) -> str:
        """
        Get the diff for a specific file.
        
        Args:
            pr_id: Pull request ID
            file_path: Path to the file
            
        Returns:
            Diff content as string
        """
        pass
