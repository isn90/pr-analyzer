"""
Azure OpenAI integration for code analysis
"""

import os
from typing import Dict, List, Any
from openai import AzureOpenAI

from ..utils.logger import get_logger
from ..utils.config import Config

logger = get_logger()


class AIAnalyzer:
    """AI-powered code analyzer using Azure OpenAI."""
    
    def __init__(self, config: Config):
        """
        Initialize AI analyzer.
        
        Args:
            config: Configuration object
        """
        self.config = config
        openai_config = config.get_azure_openai_config()
        
        # Validate configuration
        if not openai_config['endpoint']:
            raise ValueError("AZURE_OPENAI_ENDPOINT environment variable not set")
        if not openai_config['api_key']:
            raise ValueError("AZURE_OPENAI_API_KEY environment variable not set")
        if not openai_config['deployment']:
            raise ValueError("AZURE_OPENAI_DEPLOYMENT environment variable not set")
        
        # Initialize Azure OpenAI client
        self.client = AzureOpenAI(
            azure_endpoint=openai_config['endpoint'],
            api_key=openai_config['api_key'],
            api_version="2024-02-15-preview"
        )
        
        self.deployment = openai_config['deployment']
        self.temperature = openai_config['temperature']
        self.max_tokens = openai_config['max_tokens']
        
        logger.info(f"Initialized AI Analyzer with deployment: {self.deployment}")
    
    def analyze_code_changes(
        self,
        file_path: str,
        code_diff: str,
        changes_metadata: Dict[str, Any] = None,
        change_type: str = "modified"
    ) -> Dict[str, Any]:
        """
        Analyze code changes using Azure OpenAI.
        
        Args:
            file_path: Path to the file being analyzed
            code_diff: Formatted diff of the changes
            changes_metadata: Metadata about changes (line counts, hunks, etc.)
            change_type: Type of change (added, modified, deleted)
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            prompt = self._build_analysis_prompt(
                file_path, 
                code_diff, 
                changes_metadata,
                change_type
            )
            
            logger.debug(f"Analyzing {file_path} with AI...")
            
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt(change_type)
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            analysis_text = response.choices[0].message.content
            
            # Parse the response into structured format
            result = self._parse_analysis_result(analysis_text, file_path)
            
            # Add metadata
            if changes_metadata:
                result['changes_summary'] = {
                    'additions': changes_metadata.get('total_additions', 0),
                    'deletions': changes_metadata.get('total_deletions', 0)
                }
            
            logger.info(f"Completed AI analysis for {file_path}")
            return result
            
        except Exception as e:
            logger.error(f"Error during AI analysis of {file_path}: {e}")
            return {
                'file': file_path,
                'issues': [],
                'summary': f"Analysis failed: {str(e)}",
                'overall_score': 0
            }
    
    def _get_system_prompt(self, change_type: str = "modified") -> str:
        """Get the system prompt for AI analysis."""
        enabled_categories = self.config.get_enabled_categories()
        
        change_context = {
            "modified": "analyzing modifications to existing code",
            "added": "reviewing newly added code",
            "deleted": "reviewing code deletions for potential impacts"
        }.get(change_type, "analyzing code changes")
        
        return f"""You are an expert code reviewer {change_context} in a pull request. 
Your task is to review ONLY the code changes shown (not the entire file) and provide focused, actionable feedback.

**IMPORTANT**: 
- Focus ONLY on the lines that were added (+) or modified
- Do not comment on unchanged context lines
- Reference specific line numbers from the diff
- Be concise and specific to the actual changes

Review focusing on:
{', '.join(enabled_categories)}

For each issue found, provide:
1. Severity level (critical, high, medium, low)
2. Category (security, performance, best_practices, code_quality, bugs, documentation, testing, style)
3. Line number from the diff
4. Clear description of the issue IN THE CHANGED CODE
5. Specific recommendation for fixing it
6. Code example if helpful

Format your response as follows:

## Summary
[Brief assessment of the code changes - 2-3 sentences max]

## Issues Found

### [Severity] - [Category] - Line [number]
**Issue**: [Clear, specific description]
**Recommendation**: [Actionable fix]
**Example**: [Code snippet if helpful]

## Overall Score
[Score from 0-10 based on the quality of the changes]

If no issues are found in the changes, state "No issues found in these changes" and give a score of 10.

Be specific, constructive, and focus only on production-quality standards for the CHANGED code."""
    
    def _build_analysis_prompt(
        self,
        file_path: str,
        code_diff: str,
        changes_metadata: Dict[str, Any] = None,
        change_type: str = "modified"
    ) -> str:
        """Build the analysis prompt for diff-based review."""
        
        # Build context about the change
        change_summary = ""
        if changes_metadata:
            additions = changes_metadata.get('total_additions', 0)
            deletions = changes_metadata.get('total_deletions', 0)
            change_summary = f"\n**Change Summary**: +{additions} lines added, -{deletions} lines removed"
        
        prompt = f"""Review the following code changes from: **{file_path}**
**Change Type**: {change_type}{change_summary}

## Code Changes to Review:
```
{code_diff[:8000]}  # Limit to prevent token overflow
```

**Instructions**:
- Focus ONLY on the lines marked with '+' (additions)
- Consider the context lines (unmarked) for understanding
- Ignore lines marked with '-' unless they indicate a problematic deletion
- Reference line numbers from the "new file" side of the diff
- Be specific about what changed and why it matters

Please analyze these specific changes and provide detailed, actionable feedback."""
        
        return prompt
    
    def _parse_analysis_result(self, analysis_text: str, file_path: str) -> Dict[str, Any]:
        """
        Parse AI response into structured format.
        
        Args:
            analysis_text: Raw text from AI
            file_path: File being analyzed
            
        Returns:
            Structured analysis result
        """
        issues = []
        summary = ""
        overall_score = 7  # Default score
        
        # Parse the response (simplified parsing)
        lines = analysis_text.split('\n')
        current_issue = None
        in_summary = False
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('## Summary'):
                in_summary = True
                continue
            
            if line.startswith('## Issues Found'):
                in_summary = False
                continue
            
            if line.startswith('## Overall Score'):
                in_summary = False
                # Try to extract score
                try:
                    score_text = lines[lines.index(line) + 1] if lines.index(line) + 1 < len(lines) else ""
                    # Extract number from text
                    import re
                    match = re.search(r'(\d+)', score_text)
                    if match:
                        overall_score = int(match.group(1))
                except:
                    pass
                continue
            
            if in_summary and line:
                summary += line + " "
            
            # Parse issues
            if line.startswith('###'):
                if current_issue:
                    issues.append(current_issue)
                
                # Parse issue header: ### [Severity] - [Category] - Line [number]
                parts = line[3:].strip().split('-')
                severity = parts[0].strip().lower() if len(parts) > 0 else 'medium'
                category = parts[1].strip().lower() if len(parts) > 1 else 'code_quality'
                
                # Extract line number if present
                line_number = None
                if len(parts) > 2:
                    import re
                    match = re.search(r'(\d+)', parts[2])
                    if match:
                        line_number = int(match.group(1))
                
                current_issue = {
                    'severity': severity,
                    'category': category,
                    'line': line_number,
                    'description': '',
                    'recommendation': '',
                    'file': file_path
                }
            
            elif current_issue:
                if line.startswith('**Issue**:'):
                    current_issue['description'] = line.replace('**Issue**:', '').strip()
                elif line.startswith('**Recommendation**:'):
                    current_issue['recommendation'] = line.replace('**Recommendation**:', '').strip()
        
        # Add last issue
        if current_issue:
            issues.append(current_issue)
        
        return {
            'file': file_path,
            'issues': issues,
            'summary': summary.strip(),
            'overall_score': overall_score
        }
    
    def generate_summary(self, file_analyses: List[Dict[str, Any]]) -> str:
        """
        Generate overall PR summary from individual file analyses.
        
        Args:
            file_analyses: List of file analysis results
            
        Returns:
            Formatted summary text
        """
        try:
            # Collect all issues
            all_issues = []
            for analysis in file_analyses:
                all_issues.extend(analysis.get('issues', []))
            
            # Build summary prompt
            prompt = f"""Summarize the following code review findings for a pull request:

Total files analyzed: {len(file_analyses)}
Total issues found: {len(all_issues)}

Issues by severity:
- Critical: {sum(1 for i in all_issues if i.get('severity') == 'critical')}
- High: {sum(1 for i in all_issues if i.get('severity') == 'high')}
- Medium: {sum(1 for i in all_issues if i.get('severity') == 'medium')}
- Low: {sum(1 for i in all_issues if i.get('severity') == 'low')}

Issues by category:
"""
            
            # Count by category
            categories = {}
            for issue in all_issues:
                cat = issue.get('category', 'other')
                categories[cat] = categories.get(cat, 0) + 1
            
            for cat, count in categories.items():
                prompt += f"- {cat}: {count}\n"
            
            prompt += "\nProvide a concise executive summary (3-5 sentences) and recommendation on whether the PR should be approved, needs changes, or requires major revisions."
            
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert code reviewer providing executive summaries of code reviews."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return "Unable to generate summary due to an error."
