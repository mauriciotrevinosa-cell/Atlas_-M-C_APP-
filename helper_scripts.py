#!/usr/bin/env python3
"""
ATLAS HELPER SCRIPTS

Automation scripts for Project Atlas development.

Scripts:
1. generate_module.py - Auto-generate module structure
2. validate_phase.py - Validate phase completion
3. run_all_tests.py - Run comprehensive test suite
4. build_docs.py - Generate documentation

Copyright © 2026 M&C. All Rights Reserved.
"""

__version__ = "1.0.0"
__author__ = "M&C"

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional
import subprocess
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== SCRIPT 1: generate_module.py ====================

def generate_module(module_name: str, module_type: str, output_dir: str):
    """
    Auto-generate module structure with boilerplate code
    
    Args:
        module_name: Name of module (e.g., "vpin")
        module_type: Type (feature, engine, risk, etc.)
        output_dir: Output directory
    
    Example:
        >>> generate_module("vpin", "feature", "features/microstructure/")
    """
    logger.info(f"Generating module: {module_name} (type: {module_type})")
    
    templates = {
        "feature": FEATURE_TEMPLATE,
        "engine": ENGINE_TEMPLATE,
        "risk": RISK_TEMPLATE,
        "generic": GENERIC_TEMPLATE
    }
    
    template = templates.get(module_type, templates["generic"])
    
    # Create directory
    module_path = Path(output_dir) / module_name
    module_path.mkdir(parents=True, exist_ok=True)
    
    # Generate __init__.py
    init_content = f'''"""
{module_name.title()} Module

Copyright © 2026 M&C. All Rights Reserved.
"""

from .{module_name} import {module_name.title()}

__all__ = ['{module_name.title()}']
'''
    
    (module_path / "__init__.py").write_text(init_content)
    
    # Generate main module file
    main_content = template.format(
        module_name=module_name,
        class_name=module_name.title()
    )
    
    (module_path / f"{module_name}.py").write_text(main_content)
    
    # Generate test file
    test_content = TEST_TEMPLATE.format(
        module_name=module_name,
        class_name=module_name.title()
    )
    
    test_dir = Path("tests/unit")
    test_dir.mkdir(parents=True, exist_ok=True)
    (test_dir / f"test_{module_name}.py").write_text(test_content)
    
    logger.info(f"✅ Module generated at {module_path}")
    logger.info(f"✅ Tests generated at {test_dir}/test_{module_name}.py")


# Templates
FEATURE_TEMPLATE = '''"""
{class_name} Feature

Mathematical foundation and implementation.

References:
- [Add reference here]

Copyright © 2026 M&C. All Rights Reserved.
"""

import pandas as pd
import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class {class_name}:
    """
    {class_name} calculator
    
    Args:
        param1: Description
    
    Example:
        >>> calculator = {class_name}(param1=value)
        >>> result = calculator.calculate(data)
    """
    
    def __init__(self, param1: float):
        if param1 <= 0:
            raise ValueError(f"param1 must be > 0, got {{param1}}")
        
        self.param1 = param1
        logger.info(f"Initialized {class_name}")
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        Calculate {module_name}
        
        Args:
            data: OHLCV DataFrame
        
        Returns:
            pd.Series: Calculated values
        """
        try:
            # Implementation here
            result = data['Close'].rolling(window=int(self.param1)).mean()
            
            logger.debug(f"Calculated {module_name}")
            return result
            
        except Exception as e:
            logger.error(f"{class_name} calculation failed: {{str(e)}}")
            raise
'''

TEST_TEMPLATE = '''"""
Tests for {class_name}

Copyright © 2026 M&C. All Rights Reserved.
"""

import pytest
import pandas as pd
import numpy as np
from atlas.{module_name} import {class_name}


class Test{class_name}:
    """Test suite for {class_name}"""
    
    def test_initialization(self):
        """Test normal initialization"""
        obj = {class_name}(param1=10)
        assert obj.param1 == 10
    
    def test_invalid_input(self):
        """Test input validation"""
        with pytest.raises(ValueError):
            {class_name}(param1=-1)
    
    def test_calculation(self):
        """Test calculation"""
        # Create test data
        dates = pd.date_range('2024-01-01', periods=50)
        data = pd.DataFrame({{
            'Open': range(100, 150),
            'High': range(101, 151),
            'Low': range(99, 149),
            'Close': range(100, 150),
            'Volume': [1000000] * 50
        }}, index=dates)
        
        obj = {class_name}(param1=10)
        result = obj.calculate(data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
'''


# ==================== SCRIPT 2: validate_phase.py ====================

def validate_phase(phase_number: int) -> Dict[str, any]:
    """
    Validate that a phase is complete
    
    Checks:
    - All required files exist
    - All files have proper structure
    - Tests pass
    - Code coverage > 80%
    
    Args:
        phase_number: Phase to validate (0-15)
    
    Returns:
        dict: Validation results
    
    Example:
        >>> results = validate_phase(1)
        >>> if results['passed']:
        >>>     print("Phase 1 complete!")
    """
    logger.info(f"Validating Phase {phase_number}")
    
    phase_requirements = {
        0: {
            "files": [
                "README.md",
                "pyproject.toml",
                "LICENSE",
                "configs/settings.toml"
            ],
            "tests": []
        },
        1: {
            "files": [
                "data_layer/__init__.py",
                "data_layer/base.py",
                "data_layer/sources/yahoo.py",
                "data_layer/quality/validator.py",
                "data_layer/normalization/normalizer.py",
                "data_layer/cache/cache_manager.py"
            ],
            "tests": [
                "tests/unit/test_data_layer.py"
            ]
        },
        2: {
            "files": [
                "market_state/__init__.py",
                "market_state/regime.py",
                "market_state/volatility.py",
                "market_state/internals.py"
            ],
            "tests": [
                "tests/unit/test_market_state.py"
            ]
        },
        3: {
            "files": [
                "features/__init__.py",
                "features/registry.py",
                "features/technical/trend.py",
                "features/technical/momentum.py",
                "features/technical/volatility.py",
                "features/technical/volume.py",
                "features/microstructure/vpin.py",
                "features/microstructure/kyle_lambda.py",
                "features/microstructure/order_book_imbalance.py"
            ],
            "tests": [
                "tests/unit/test_features.py"
            ]
        },
        8: {
            "files": [
                "monte_carlo/__init__.py",
                "monte_carlo/simulator.py"
            ],
            "tests": [
                "tests/unit/test_monte_carlo.py"
            ]
        }
    }
    
    if phase_number not in phase_requirements:
        logger.error(f"Phase {phase_number} not defined")
        return {"passed": False, "error": "Phase not defined"}
    
    requirements = phase_requirements[phase_number]
    results = {
        "phase": phase_number,
        "passed": True,
        "files": {},
        "tests": {},
        "coverage": 0
    }
    
    # Check files
    for file_path in requirements["files"]:
        full_path = Path("python/src/atlas") / file_path
        exists = full_path.exists()
        
        results["files"][file_path] = {
            "exists": exists,
            "size": full_path.stat().st_size if exists else 0
        }
        
        if not exists:
            results["passed"] = False
            logger.error(f"❌ Missing: {file_path}")
        else:
            logger.info(f"✅ Found: {file_path}")
    
    # Run tests
    if requirements["tests"]:
        for test_file in requirements["tests"]:
            test_path = Path(test_file)
            
            if not test_path.exists():
                results["tests"][test_file] = {"passed": False, "error": "File not found"}
                results["passed"] = False
                continue
            
            try:
                # Run pytest
                cmd = ["pytest", str(test_path), "-v", "--tb=short"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                passed = result.returncode == 0
                
                results["tests"][test_file] = {
                    "passed": passed,
                    "output": result.stdout
                }
                
                if passed:
                    logger.info(f"✅ Tests passed: {test_file}")
                else:
                    logger.error(f"❌ Tests failed: {test_file}")
                    results["passed"] = False
                    
            except Exception as e:
                logger.error(f"Error running tests: {e}")
                results["tests"][test_file] = {"passed": False, "error": str(e)}
                results["passed"] = False
    
    # Check coverage
    try:
        cmd = ["pytest", "--cov=atlas", "--cov-report=term-missing"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Parse coverage from output
        for line in result.stdout.split('\n'):
            if "TOTAL" in line:
                coverage_str = line.split()[-1].rstrip('%')
                results["coverage"] = float(coverage_str)
                
                if results["coverage"] < 80:
                    logger.warning(f"⚠️  Coverage below 80%: {results['coverage']}%")
                else:
                    logger.info(f"✅ Coverage: {results['coverage']}%")
                    
    except Exception as e:
        logger.error(f"Error checking coverage: {e}")
    
    # Final summary
    if results["passed"]:
        logger.info(f"🎉 Phase {phase_number} validation PASSED")
    else:
        logger.error(f"❌ Phase {phase_number} validation FAILED")
    
    return results


# ==================== SCRIPT 3: run_all_tests.py ====================

def run_all_tests(verbose: bool = True, coverage: bool = True):
    """
    Run all tests with comprehensive reporting
    
    Args:
        verbose: Show detailed output
        coverage: Generate coverage report
    
    Example:
        >>> run_all_tests(verbose=True, coverage=True)
    """
    logger.info("Running all tests...")
    
    # Build pytest command
    cmd = ["pytest", "tests/"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=atlas", "--cov-report=html", "--cov-report=term"])
    
    cmd.extend([
        "--tb=short",
        "--maxfail=5",  # Stop after 5 failures
        "-ra"  # Show summary of all test outcomes
    ])
    
    try:
        logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, text=True)
        
        if result.returncode == 0:
            logger.info("✅ All tests passed!")
            
            if coverage:
                logger.info("📊 Coverage report generated at htmlcov/index.html")
        else:
            logger.error(f"❌ Tests failed (exit code: {result.returncode})")
            
        return result.returncode == 0
        
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        return False


# ==================== SCRIPT 4: build_docs.py ====================

def build_docs(output_dir: str = "docs/build"):
    """
    Generate documentation from docstrings
    
    Uses Sphinx to build comprehensive docs.
    
    Args:
        output_dir: Output directory for docs
    
    Example:
        >>> build_docs("docs/build")
    """
    logger.info("Building documentation...")
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Generate API docs
        cmd = [
            "sphinx-apidoc",
            "-f",  # Force overwrite
            "-o", "docs/source/api",
            "python/src/atlas"
        ]
        
        subprocess.run(cmd, check=True)
        logger.info("✅ API docs generated")
        
        # Build HTML docs
        cmd = [
            "sphinx-build",
            "-b", "html",
            "docs/source",
            str(output_path)
        ]
        
        subprocess.run(cmd, check=True)
        logger.info(f"✅ Docs built at {output_path}/index.html")
        
        return True
        
    except Exception as e:
        logger.error(f"Error building docs: {e}")
        return False


# ==================== CLI Interface ====================

def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Atlas Helper Scripts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate new module
  python helper_scripts.py generate vpin feature features/microstructure
  
  # Validate phase
  python helper_scripts.py validate 1
  
  # Run all tests
  python helper_scripts.py test --verbose --coverage
  
  # Build docs
  python helper_scripts.py docs
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Generate module
    gen_parser = subparsers.add_parser('generate', help='Generate new module')
    gen_parser.add_argument('name', help='Module name')
    gen_parser.add_argument('type', help='Module type (feature, engine, risk, generic)')
    gen_parser.add_argument('output', help='Output directory')
    
    # Validate phase
    val_parser = subparsers.add_parser('validate', help='Validate phase completion')
    val_parser.add_argument('phase', type=int, help='Phase number (0-15)')
    
    # Run tests
    test_parser = subparsers.add_parser('test', help='Run all tests')
    test_parser.add_argument('--verbose', action='store_true', help='Verbose output')
    test_parser.add_argument('--coverage', action='store_true', default=True, help='Generate coverage')
    
    # Build docs
    docs_parser = subparsers.add_parser('docs', help='Build documentation')
    docs_parser.add_argument('--output', default='docs/build', help='Output directory')
    
    args = parser.parse_args()
    
    if args.command == 'generate':
        generate_module(args.name, args.type, args.output)
    
    elif args.command == 'validate':
        results = validate_phase(args.phase)
        sys.exit(0 if results['passed'] else 1)
    
    elif args.command == 'test':
        success = run_all_tests(verbose=args.verbose, coverage=args.coverage)
        sys.exit(0 if success else 1)
    
    elif args.command == 'docs':
        success = build_docs(args.output)
        sys.exit(0 if success else 1)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()


# ==================== ADDITIONAL UTILITIES ====================

def quick_setup():
    """
    Quick setup for new development environment
    
    Installs dependencies, creates directories, etc.
    """
    logger.info("Running quick setup...")
    
    # Create directory structure
    dirs = [
        "python/src/atlas",
        "python/tests/unit",
        "python/tests/integration",
        "python/examples",
        "docs/source",
        "data/cache",
        "data/raw",
        "data/processed"
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ Created: {dir_path}")
    
    # Install dependencies
    try:
        logger.info("Installing dependencies...")
        subprocess.run(["pip", "install", "-e", "python/"], check=True)
        subprocess.run(["pip", "install", "-r", "requirements-dev.txt"], check=True)
        logger.info("✅ Dependencies installed")
    except Exception as e:
        logger.error(f"Error installing dependencies: {e}")
    
    logger.info("🎉 Quick setup complete!")


def benchmark_performance():
    """
    Run performance benchmarks on critical modules
    
    Useful for detecting performance regressions.
    """
    logger.info("Running performance benchmarks...")
    
    try:
        cmd = ["pytest", "tests/performance/", "-v", "--benchmark-only"]
        result = subprocess.run(cmd, text=True)
        
        if result.returncode == 0:
            logger.info("✅ Benchmarks complete")
        else:
            logger.error("❌ Benchmarks failed")
            
        return result.returncode == 0
        
    except Exception as e:
        logger.error(f"Error running benchmarks: {e}")
        return False


# ==================== EXPORTS ====================

__all__ = [
    'generate_module',
    'validate_phase',
    'run_all_tests',
    'build_docs',
    'quick_setup',
    'benchmark_performance'
]
