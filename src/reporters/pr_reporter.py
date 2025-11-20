"""
PR reporter for posting analysis results
"""

from typing import Dict, Any, List

from ..providers.base_provider import BaseProvider
from ..utils.logger import get_logger
from ..utils.config import Config

logger = get_logger()


class PRReporter:
    """Handles posting analysis results to pull requests."""
    
    def __init__(self, provider: BaseProvider, config: Config):
        """
        Initialize PR reporter.
        
        Args:
            provider: Repository provider instance
            config: Configuration object
        """
        self.provider = provider
        self.config = config
    
    def post_report(self, pr_id: str, analysis_results: Dict[str, Any]) -> bool:
        """
        Post analysis report to pull request.
        
        Args:
            pr_id: Pull request ID
            analysis_results: Complete analysis results
            
        Returns:
            True if successful, False otherwise
        """
        success = True
        
        # Post summary comment if enabled
        if self.config.get('reporting.summary_enabled', True):
            summary_comment = self._generate_summary_comment(analysis_results)
            if not self.provider.post_comment(pr_id, summary_comment):
                success = False
        
        # Post inline comments if enabled
        if self.config.get('reporting.inline_comments_enabled', True):
            if not self._post_inline_comments(pr_id, analysis_results):
                success = False
        
        return success
    
    def _generate_summary_comment(self, results: Dict[str, Any]) -> str:
        """
        Generate formatted summary comment.
        
        Args:
            results: Analysis results
            
        Returns:
            Formatted comment text
        """
        header = self.config.get('reporting.comment_header', '🤖 AI Code Review')
        footer = self.config.get('reporting.comment_footer', 'Powered by Azure OpenAI')
        
        stats = results.get('statistics', {})
        severity = stats.get('by_severity', {})
        
        # Build comment
        comment = f"## {header}\n\n"
        
        # Overview
        comment += f"**Pull Request**: {results.get('pr_title', 'N/A')}\n"
        comment += f"**Author**: {results.get('pr_author', 'N/A')}\n"
        comment += f"**Files Analyzed**: {results.get('analyzed_files', 0)} / {results.get('total_files', 0)}\n"
        comment += f"**Total Issues Found**: {stats.get('total_issues', 0)}\n"
        comment += f"**Code Quality Score**: {stats.get('average_score', 0)}/10\n\n"
        
        # Issues by severity
        if stats.get('total_issues', 0) > 0:
            comment += "### 📊 Issues by Severity\n\n"
            
            if severity.get('critical', 0) > 0:
                comment += f"- 🔴 **Critical**: {severity['critical']}\n"
            if severity.get('high', 0) > 0:
                comment += f"- 🟠 **High**: {severity['high']}\n"
            if severity.get('medium', 0) > 0:
                comment += f"- 🟡 **Medium**: {severity['medium']}\n"
            if severity.get('low', 0) > 0:
                comment += f"- 🔵 **Low**: {severity['low']}\n"
            
            comment += "\n"
            
            # Top issues
            comment += "### 🎯 Key Issues\n\n"
            top_issues = self._get_top_issues(results, limit=5)
            
            for i, issue in enumerate(top_issues, 1):
                severity_icon = self._get_severity_icon(issue.get('severity', 'low'))
                comment += f"{i}. {severity_icon} **{issue.get('category', 'General').replace('_', ' ').title()}** "
                comment += f"in `{issue.get('file', 'unknown')}`"
                if issue.get('line'):
                    comment += f" (Line {issue['line']})"
                comment += f"\n   - {issue.get('description', 'No description')}\n"
            
            comment += "\n"
        
        # Overall summary
        comment += "### 📝 Summary\n\n"
        comment += results.get('overall_summary', 'Analysis completed successfully.')
        comment += "\n\n"
        
        # Recommendation
        comment += "### ✅ Recommendation\n\n"
        comment += self._get_recommendation(stats)
        comment += "\n\n"
        
        # Footer
        comment += f"---\n*{footer}*\n"
        
        return comment
    
    def _post_inline_comments(self, pr_id: str, results: Dict[str, Any]) -> bool:
        """
        Post inline comments on specific lines.
        
        Args:
            pr_id: Pull request ID
            results: Analysis results
            
        Returns:
            True if successful, False otherwise
        """
        max_per_file = self.config.get('reporting.max_inline_comments_per_file', 10)
        severity_levels = self.config.get('reporting.severity_levels', ['critical', 'high', 'medium', 'low'])
        
        success = True
        
        # Group issues by file
        files_issues = {}
        for analysis in results.get('file_analyses', []):
            file_path = analysis.get('file', '')
            issues = analysis.get('issues', [])
            
            # Filter by severity
            filtered_issues = [
                i for i in issues 
                if i.get('severity', 'low') in severity_levels and i.get('line')
            ]
            
            if filtered_issues:
                files_issues[file_path] = filtered_issues
        
        # Post comments
        for file_path, issues in files_issues.items():
            # Sort by severity and limit
            sorted_issues = sorted(
                issues,
                key=lambda x: ['critical', 'high', 'medium', 'low'].index(x.get('severity', 'low'))
            )[:max_per_file]
            
            for issue in sorted_issues:
                try:
                    comment = self._format_inline_comment(issue)
                    self.provider.post_inline_comment(
                        pr_id=pr_id,
                        file_path=file_path,
                        line_number=issue.get('line', 1),
                        comment=comment
                    )
                except Exception as e:
                    logger.error(f"Error posting inline comment: {e}")
                    success = False
        
        return success
    
    def _format_inline_comment(self, issue: Dict[str, Any]) -> str:
        """
        Format an inline comment.
        
        Args:
            issue: Issue information
            
        Returns:
            Formatted comment text
        """
        severity_icon = self._get_severity_icon(issue.get('severity', 'low'))
        severity = issue.get('severity', 'low').upper()
        category = issue.get('category', 'General').replace('_', ' ').title()
        
        comment = f"{severity_icon} **{category} Issue - {severity} Priority**\n\n"
        comment += f"{issue.get('description', 'No description provided')}\n\n"
        
        if issue.get('recommendation'):
            comment += f"**💡 Recommendation**: {issue['recommendation']}\n"
        
        return comment
    
    def _get_top_issues(self, results: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get top issues sorted by severity.
        
        Args:
            results: Analysis results
            limit: Maximum number of issues to return
            
        Returns:
            List of top issues
        """
        all_issues = []
        for analysis in results.get('file_analyses', []):
            all_issues.extend(analysis.get('issues', []))
        
        # Sort by severity
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        sorted_issues = sorted(
            all_issues,
            key=lambda x: severity_order.get(x.get('severity', 'low'), 999)
        )
        
        return sorted_issues[:limit]
    
    def _get_severity_icon(self, severity: str) -> str:
        """Get icon for severity level."""
        icons = {
            'critical': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🔵',
            'info': 'ℹ️'
        }
        return icons.get(severity.lower(), '⚪')
    
    def _get_recommendation(self, stats: Dict[str, Any]) -> str:
        """
        Get recommendation based on statistics.
        
        Args:
            stats: Statistics dictionary
            
        Returns:
            Recommendation text
        """
        severity = stats.get('by_severity', {})
        score = stats.get('average_score', 0)
        
        if severity.get('critical', 0) > 0:
            return "❌ **Not Ready for Merge** - Critical issues must be addressed before merging."
        elif severity.get('high', 0) > 0:
            return "⚠️ **Needs Changes** - High priority issues should be resolved before merging."
        elif score >= 8:
            return "✅ **Approved** - Code looks good! Minor issues can be addressed in future PRs."
        elif score >= 6:
            return "👍 **Approved with Minor Changes** - Consider addressing medium priority issues."
        else:
            return "⚠️ **Needs Improvement** - Please review and address the identified issues."
