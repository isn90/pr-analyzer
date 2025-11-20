"""
Configuration management utilities
"""

import os
import yaml
from typing import Any, Optional
from pathlib import Path


class Config:
    """Configuration manager for PR Analyzer."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to config.yaml file. Defaults to config.yaml in project root.
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config.yaml"
        
        self.config_path = config_path
        self._config = self._load_config()
    
    def _load_config(self) -> dict:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return self._get_default_config()
        except Exception as e:
            raise Exception(f"Error loading config: {str(e)}")
    
    def _get_default_config(self) -> dict:
        """Return default configuration."""
        return {
            'analysis': {
                'max_file_size': 100000,
                'max_files': 50,
                'include_extensions': ['.py', '.js', '.ts', '.java', '.cs'],
                'exclude_directories': ['node_modules', 'venv', 'env', 'dist', 'build']
            },
            'openai': {
                'model': 'gpt-4',
                'temperature': 0.3,
                'max_tokens': 2000,
                'timeout': 60
            },
            'reporting': {
                'summary_enabled': True,
                'inline_comments_enabled': True,
                'severity_levels': ['critical', 'high', 'medium', 'low'],
                'max_inline_comments_per_file': 10,
                'comment_header': '🤖 AI Code Review',
                'comment_footer': 'Powered by Azure OpenAI'
            },
            'analysis_categories': {
                'security': {'enabled': True, 'weight': 1.0},
                'performance': {'enabled': True, 'weight': 0.8},
                'best_practices': {'enabled': True, 'weight': 0.9},
                'code_quality': {'enabled': True, 'weight': 0.7},
                'bugs': {'enabled': True, 'weight': 1.0},
                'documentation': {'enabled': True, 'weight': 0.5},
                'testing': {'enabled': True, 'weight': 0.6},
                'style': {'enabled': True, 'weight': 0.4}
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file': 'pr_analyzer.log'
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key: Configuration key in dot notation (e.g., 'analysis.max_file_size')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_enabled_categories(self) -> list:
        """Get list of enabled analysis categories."""
        categories = []
        analysis_categories = self.get('analysis_categories', {})
        
        for category, settings in analysis_categories.items():
            if settings.get('enabled', False):
                categories.append(category)
        
        return categories
    
    def get_azure_openai_config(self) -> dict:
        """Get Azure OpenAI configuration from environment variables."""
        return {
            'endpoint': os.getenv('AZURE_OPENAI_ENDPOINT'),
            'api_key': os.getenv('AZURE_OPENAI_API_KEY'),
            'deployment': os.getenv('AZURE_OPENAI_DEPLOYMENT'),
            'model': self.get('openai.model', 'gpt-4'),
            'temperature': self.get('openai.temperature', 0.3),
            'max_tokens': self.get('openai.max_tokens', 2000),
            'timeout': self.get('openai.timeout', 60)
        }
