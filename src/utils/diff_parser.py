"""
Diff parser utility for extracting changes from unified diff format
"""

import re
from typing import List, Dict, Any, Optional
from ..utils.logger import get_logger

logger = get_logger()


class DiffHunk:
    """Represents a single hunk in a diff."""
    
    def __init__(self, old_start: int, old_count: int, new_start: int, new_count: int):
        self.old_start = old_start
        self.old_count = old_count
        self.new_start = new_start
        self.new_count = new_count
        self.lines: List[Dict[str, Any]] = []
    
    def add_line(self, line_type: str, content: str, old_line_num: Optional[int], new_line_num: Optional[int]):
        """Add a line to the hunk."""
        self.lines.append({
            'type': line_type,  # 'add', 'delete', 'context'
            'content': content,
            'old_line': old_line_num,
            'new_line': new_line_num
        })
    
    def get_added_lines(self) -> List[Dict[str, Any]]:
        """Get only the added lines."""
        return [line for line in self.lines if line['type'] == 'add']
    
    def get_modified_lines(self) -> List[Dict[str, Any]]:
        """Get added and deleted lines (modifications)."""
        return [line for line in self.lines if line['type'] in ('add', 'delete')]
    
    def get_context_for_line(self, new_line_num: int, context_lines: int = 3) -> List[Dict[str, Any]]:
        """Get surrounding context for a specific line number."""
        result = []
        target_idx = None
        
        for idx, line in enumerate(self.lines):
            if line['new_line'] == new_line_num:
                target_idx = idx
                break
        
        if target_idx is None:
            return result
        
        start_idx = max(0, target_idx - context_lines)
        end_idx = min(len(self.lines), target_idx + context_lines + 1)
        
        return self.lines[start_idx:end_idx]


class DiffParser:
    """Parser for unified diff format."""
    
    # Regex for hunk header: @@ -old_start,old_count +new_start,new_count @@
    HUNK_HEADER_PATTERN = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')
    
    @staticmethod
    def parse_patch(patch: str) -> List[DiffHunk]:
        """
        Parse a unified diff patch into hunks.
        
        Args:
            patch: Unified diff string
            
        Returns:
            List of DiffHunk objects
        """
        if not patch:
            return []
        
        hunks = []
        current_hunk = None
        old_line_num = 0
        new_line_num = 0
        
        for line in patch.split('\n'):
            # Check for hunk header
            match = DiffParser.HUNK_HEADER_PATTERN.match(line)
            if match:
                # Save previous hunk if exists
                if current_hunk:
                    hunks.append(current_hunk)
                
                # Parse hunk header
                old_start = int(match.group(1))
                old_count = int(match.group(2)) if match.group(2) else 1
                new_start = int(match.group(3))
                new_count = int(match.group(4)) if match.group(4) else 1
                
                current_hunk = DiffHunk(old_start, old_count, new_start, new_count)
                old_line_num = old_start
                new_line_num = new_start
                continue
            
            if not current_hunk:
                continue
            
            # Parse diff lines
            if line.startswith('+') and not line.startswith('+++'):
                # Added line
                content = line[1:]  # Remove '+' prefix
                current_hunk.add_line('add', content, None, new_line_num)
                new_line_num += 1
            elif line.startswith('-') and not line.startswith('---'):
                # Deleted line
                content = line[1:]  # Remove '-' prefix
                current_hunk.add_line('delete', content, old_line_num, None)
                old_line_num += 1
            elif line.startswith(' '):
                # Context line
                content = line[1:]  # Remove ' ' prefix
                current_hunk.add_line('context', content, old_line_num, new_line_num)
                old_line_num += 1
                new_line_num += 1
            elif line.startswith('\\'):
                # No newline at end of file - skip
                continue
        
        # Add last hunk
        if current_hunk:
            hunks.append(current_hunk)
        
        return hunks
    
    @staticmethod
    def extract_changes(patch: str, include_context: bool = True, context_lines: int = 3) -> Dict[str, Any]:
        """
        Extract changes from a patch with optional context.
        
        Args:
            patch: Unified diff string
            include_context: Whether to include surrounding context lines
            context_lines: Number of context lines to include before/after changes
            
        Returns:
            Dictionary with extracted changes and metadata
        """
        hunks = DiffParser.parse_patch(patch)
        
        added_lines = []
        deleted_lines = []
        modified_sections = []
        
        for hunk in hunks:
            hunk_added = hunk.get_added_lines()
            hunk_deleted = [line for line in hunk.lines if line['type'] == 'delete']
            
            added_lines.extend(hunk_added)
            deleted_lines.extend(hunk_deleted)
            
            # Create modified sections with context
            if hunk_added or hunk_deleted:
                section = {
                    'start_line': hunk.new_start,
                    'lines': hunk.lines if include_context else hunk.get_modified_lines()
                }
                modified_sections.append(section)
        
        return {
            'hunks': hunks,
            'added_lines': added_lines,
            'deleted_lines': deleted_lines,
            'modified_sections': modified_sections,
            'total_additions': len(added_lines),
            'total_deletions': len(deleted_lines)
        }
    
    @staticmethod
    def format_for_analysis(patch: str, file_path: str) -> str:
        """
        Format patch for AI analysis with clear structure.
        
        Args:
            patch: Unified diff string
            file_path: Path to the file
            
        Returns:
            Formatted string for AI analysis
        """
        changes = DiffParser.extract_changes(patch)
        
        if not changes['modified_sections']:
            return ""
        
        output = [f"File: {file_path}"]
        output.append(f"Changes: +{changes['total_additions']} -{changes['total_deletions']}")
        output.append("")
        
        for section in changes['modified_sections']:
            output.append(f"--- Changed Section (starting at line {section['start_line']}) ---")
            
            for line in section['lines']:
                if line['type'] == 'add':
                    prefix = "+ "
                    line_num = line['new_line']
                elif line['type'] == 'delete':
                    prefix = "- "
                    line_num = line['old_line']
                else:
                    prefix = "  "
                    line_num = line['new_line']
                
                output.append(f"{prefix}{line_num:4d} | {line['content']}")
            
            output.append("")
        
        return '\n'.join(output)
    
    @staticmethod
    def get_diff_line_position(patch: str, new_line_num: int) -> Optional[int]:
        """
        Get the position of a line in the diff (for inline comments).
        
        Args:
            patch: Unified diff string
            new_line_num: The line number in the new file
            
        Returns:
            Position in the diff (0-indexed) or None if not found
        """
        position = 0
        
        for line in patch.split('\n'):
            # Skip file headers
            if line.startswith('+++') or line.startswith('---'):
                continue
            
            # Skip hunk headers
            if line.startswith('@@'):
                position += 1
                continue
            
            # Check if this is the target line
            hunks = DiffParser.parse_patch(patch)
            current_new_line = 0
            
            for hunk in hunks:
                for hunk_line in hunk.lines:
                    if hunk_line['type'] in ('add', 'context') and hunk_line['new_line'] == new_line_num:
                        # Calculate position by counting lines in patch
                        return DiffParser._calculate_position(patch, new_line_num)
        
        return None
    
    @staticmethod
    def _calculate_position(patch: str, target_new_line: int) -> Optional[int]:
        """Calculate the exact position in the diff for a given line number."""
        lines = patch.split('\n')
        position = 0
        current_new_line = 0
        in_hunk = False
        
        for line in lines:
            # Check for hunk header
            match = DiffParser.HUNK_HEADER_PATTERN.match(line)
            if match:
                in_hunk = True
                new_start = int(match.group(3))
                current_new_line = new_start
                position += 1
                continue
            
            if not in_hunk:
                continue
            
            if line.startswith('+++') or line.startswith('---'):
                continue
            
            if line.startswith('+') and not line.startswith('+++'):
                if current_new_line == target_new_line:
                    return position
                current_new_line += 1
                position += 1
            elif line.startswith(' '):
                if current_new_line == target_new_line:
                    return position
                current_new_line += 1
                position += 1
            elif line.startswith('-') and not line.startswith('---'):
                position += 1
        
        return None
