"""
Code analyzer orchestrator
"""

from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from .ai_analyzer import AIAnalyzer
from ..utils.logger import get_logger
from ..utils.config import Config
from ..utils.diff_parser import DiffParser

logger = get_logger()


class CodeAnalyzer:
    """Main code analyzer that orchestrates the analysis process."""
    
    def __init__(self, config: Config):
        """
        Initialize code analyzer.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.ai_analyzer = AIAnalyzer(config)
    
    def analyze_pr(
        self,
        changed_files: List[Dict[str, Any]],
        pr_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze all files in a pull request.
        
        Args:
            changed_files: List of changed file information
            pr_details: Pull request details
            
        Returns:
            Complete analysis results
        """
        logger.info(f"Starting analysis of {len(changed_files)} files")
        
        file_analyses = []
        
        # Analyze files sequentially for now (can be parallelized later)
        for file_info in changed_files:
            try:
                analysis = self._analyze_file(file_info)
                if analysis:
                    file_analyses.append(analysis)
            except Exception as e:
                logger.error(f"Error analyzing file {file_info.get('path', 'unknown')}: {e}")
        
        # Generate overall summary
        logger.info("Generating overall PR summary...")
        overall_summary = self.ai_analyzer.generate_summary(file_analyses)
        
        # Compile results
        results = {
            'pr_id': pr_details.get('id'),
            'pr_title': pr_details.get('title'),
            'pr_author': pr_details.get('author'),
            'total_files': len(changed_files),
            'analyzed_files': len(file_analyses),
            'file_analyses': file_analyses,
            'overall_summary': overall_summary,
            'statistics': self._calculate_statistics(file_analyses)
        }
        
        logger.info(f"Analysis complete. Found {results['statistics']['total_issues']} total issues")
        
        return results
    
    def _analyze_file(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single file.
        
        Args:
            file_info: File information including path and changes
            
        Returns:
            Analysis result for the file
        """
        file_path = file_info.get('path', '')
        change_type = file_info.get('change_type', 'modified')
        logger.info(f"Analyzing file: {file_path} (change type: {change_type})")
        
        # Get diff/patch if available
        patch = file_info.get('patch', '')
        
        if not patch:
            logger.warning(f"No patch available for {file_path}, skipping analysis")
            return None
        
        # Check if diff-only analysis is enabled (default: true)
        use_diff_only = self.config.get('analysis.diff_only', True)
        
        if use_diff_only:
            # Extract and format changes from diff
            changes = DiffParser.extract_changes(patch, include_context=True, context_lines=3)
            
            if changes['total_additions'] == 0 and changes['total_deletions'] == 0:
                logger.info(f"No additions or deletions in {file_path}, skipping")
                return None
            
            # Format diff for analysis
            formatted_diff = DiffParser.format_for_analysis(patch, file_path)
            
            logger.info(f"Analyzing {changes['total_additions']} additions and {changes['total_deletions']} deletions")
            
            # Analyze only the diff
            analysis = self.ai_analyzer.analyze_code_changes(
                file_path=file_path,
                code_diff=formatted_diff,
                changes_metadata=changes,
                change_type=change_type
            )
        else:
            # Fallback: analyze full file (old behavior)
            logger.info("Using full file analysis mode")
            analysis = self.ai_analyzer.analyze_code_changes(
                file_path=file_path,
                code_diff=patch,
                changes_metadata=None,
                change_type=change_type
            )
        
        # Add diff metadata to analysis
        if analysis:
            analysis['patch'] = patch
            analysis['change_type'] = change_type
        
        return analysis
    
    def _calculate_statistics(self, file_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate statistics from analysis results.
        
        Args:
            file_analyses: List of file analysis results
            
        Returns:
            Statistics dictionary
        """
        all_issues = []
        for analysis in file_analyses:
            all_issues.extend(analysis.get('issues', []))
        
        # Count by severity
        severity_counts = {
            'critical': sum(1 for i in all_issues if i.get('severity') == 'critical'),
            'high': sum(1 for i in all_issues if i.get('severity') == 'high'),
            'medium': sum(1 for i in all_issues if i.get('severity') == 'medium'),
            'low': sum(1 for i in all_issues if i.get('severity') == 'low')
        }
        
        # Count by category
        category_counts = {}
        for issue in all_issues:
            cat = issue.get('category', 'other')
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Calculate average score
        scores = [a.get('overall_score', 0) for a in file_analyses if 'overall_score' in a]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        return {
            'total_issues': len(all_issues),
            'by_severity': severity_counts,
            'by_category': category_counts,
            'average_score': round(avg_score, 2),
            'files_with_issues': sum(1 for a in file_analyses if a.get('issues'))
        }
