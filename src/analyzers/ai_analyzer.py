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
        file_content: str = ""
    ) -> Dict[str, Any]:
        """
        Analyze code changes using Azure OpenAI.
        
        Args:
            file_path: Path to the file being analyzed
            code_diff: Git diff of the changes
            file_content: Full content of the file (optional)
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            prompt = self._build_analysis_prompt(file_path, code_diff, file_content)
            
            logger.debug(f"Analyzing {file_path} with AI...")
            
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
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
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for AI analysis."""
        enabled_categories = self.config.get_enabled_categories()
        
        return f"""You are an expert code reviewer analyzing pull request changes. 
Your task is to review code changes and provide comprehensive feedback focusing on:

{', '.join(enabled_categories)}

For each issue found, provide:
1. Severity level (critical, high, medium, low)
2. Category (security, performance, best_practices, code_quality, bugs, documentation, testing, style)
3. Line number (if applicable)
4. Clear description of the issue
5. Specific recommendation for fixing it
6. Code example if helpful

Format your response as follows:

## Summary
[Brief overall assessment of the changes]

## Issues Found

### [Severity] - [Category] - Line [number]
**Issue**: [Clear description]
**Recommendation**: [How to fix]
**Example**: [Code example if applicable]

## Overall Score
[Score from 0-10 based on code quality]

Be specific, constructive, and focus on production-quality code standards."""
    
    def _build_analysis_prompt(
        self,
        file_path: str,
        code_diff: str,
        file_content: str
    ) -> str:
        """Build the analysis prompt."""
        prompt = f"""Review the following code changes from file: {file_path}

"""
        
        if code_diff:
            prompt += f"""## Code Changes (Diff):
```
{code_diff[:5000]}  # Limit diff size
```

"""
        
        if file_content:
            prompt += f"""## Full File Content:
```
{file_content[:3000]}  # Limit content size
```

"""
        
        prompt += """Please analyze these changes thoroughly and provide detailed feedback."""
        
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
