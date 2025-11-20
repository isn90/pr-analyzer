"""
Test script for PR Analyzer
This script helps test the analyzer locally before deploying to Azure Pipelines
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all imports work correctly."""
    print("Testing imports...")
    try:
        from src.utils.config import Config
        from src.utils.logger import setup_logger
        from src.providers.azure_devops import AzureDevOpsProvider
        from src.providers.github import GitHubProvider
        from src.analyzers.ai_analyzer import AIAnalyzer
        from src.analyzers.code_analyzer import CodeAnalyzer
        from src.reporters.pr_reporter import PRReporter
        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    try:
        from src.utils.config import Config
        config = Config()
        
        # Test basic config access
        assert config.get('analysis.max_file_size') is not None
        assert config.get('openai.model') is not None
        assert config.get('reporting.summary_enabled') is not None
        
        print("✓ Configuration loaded successfully")
        print(f"  - Max file size: {config.get('analysis.max_file_size')}")
        print(f"  - OpenAI model: {config.get('openai.model')}")
        print(f"  - Summary enabled: {config.get('reporting.summary_enabled')}")
        return True
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False


def test_logger():
    """Test logger setup."""
    print("\nTesting logger...")
    try:
        from src.utils.config import Config
        from src.utils.logger import setup_logger
        
        config = Config()
        logger = setup_logger(config)
        
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        
        print("✓ Logger configured successfully")
        return True
    except Exception as e:
        print(f"✗ Logger test failed: {e}")
        return False


def test_environment():
    """Test environment variables."""
    print("\nTesting environment variables...")
    
    required_vars = [
        'AZURE_OPENAI_ENDPOINT',
        'AZURE_OPENAI_API_KEY',
        'AZURE_OPENAI_DEPLOYMENT',
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"✗ Missing environment variables: {', '.join(missing)}")
        print("\nPlease set the following environment variables:")
        print("  - AZURE_OPENAI_ENDPOINT")
        print("  - AZURE_OPENAI_API_KEY")
        print("  - AZURE_OPENAI_DEPLOYMENT")
        return False
    else:
        print("✓ All required environment variables set")
        print(f"  - Endpoint: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
        print(f"  - Deployment: {os.getenv('AZURE_OPENAI_DEPLOYMENT')}")
        return True


def test_azure_openai_connection():
    """Test Azure OpenAI connection."""
    print("\nTesting Azure OpenAI connection...")
    try:
        from src.utils.config import Config
        from src.analyzers.ai_analyzer import AIAnalyzer
        
        config = Config()
        analyzer = AIAnalyzer(config)
        
        print("✓ Azure OpenAI client initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Azure OpenAI connection failed: {e}")
        print("\nPlease verify:")
        print("  - AZURE_OPENAI_ENDPOINT is correct")
        print("  - AZURE_OPENAI_API_KEY is valid")
        print("  - AZURE_OPENAI_DEPLOYMENT exists")
        return False


def test_provider_initialization():
    """Test provider initialization."""
    print("\nTesting provider initialization...")
    
    # Test Azure DevOps provider
    if os.getenv('AZURE_DEVOPS_PAT') and os.getenv('SYSTEM_TEAMFOUNDATIONCOLLECTIONURI'):
        try:
            from src.providers.azure_devops import AzureDevOpsProvider
            
            provider = AzureDevOpsProvider(
                organization_url=os.getenv('SYSTEM_TEAMFOUNDATIONCOLLECTIONURI'),
                project=os.getenv('SYSTEM_TEAMPROJECT', 'TestProject'),
                repository=os.getenv('BUILD_REPOSITORY_NAME', 'TestRepo'),
                pat=os.getenv('AZURE_DEVOPS_PAT')
            )
            print("✓ Azure DevOps provider initialized")
            return True
        except Exception as e:
            print(f"✗ Azure DevOps provider initialization failed: {e}")
            return False
    
    # Test GitHub provider
    elif os.getenv('GITHUB_TOKEN'):
        try:
            from src.providers.github import GitHubProvider
            
            provider = GitHubProvider(
                repository=os.getenv('BUILD_REPOSITORY_NAME', 'owner/repo'),
                token=os.getenv('GITHUB_TOKEN')
            )
            print("✓ GitHub provider initialized")
            return True
        except Exception as e:
            print(f"✗ GitHub provider initialization failed: {e}")
            return False
    else:
        print("⚠ Skipping provider test - no credentials provided")
        return True


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("PR Analyzer - Test Suite")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("Logger", test_logger),
        ("Environment", test_environment),
        ("Azure OpenAI Connection", test_azure_openai_connection),
        ("Provider Initialization", test_provider_initialization),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ {name} test crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The PR Analyzer is ready to use.")
        return True
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
