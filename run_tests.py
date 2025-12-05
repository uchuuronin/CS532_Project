#!/usr/bin/env python3
"""
Test Runner Script
Runs all tests in the project with detailed output and coverage reporting
"""

import sys
import os
import subprocess
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """Print formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(80)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.RESET}\n")

def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def check_dependencies():
    """Check if required dependencies are installed"""
    print_header("Checking Dependencies")
    
    required_packages = ['pytest', 'pandas', 'numpy']
    missing = []
    
    for package in required_packages:
        try:
            __import__(package)
            print_success(f"{package} is installed")
        except ImportError:
            print_error(f"{package} is NOT installed")
            missing.append(package)
    
    if missing:
        print_warning(f"\nMissing packages: {', '.join(missing)}")
        print("Install them with: pip install pytest pandas numpy")
        return False
    
    return True

def run_tests(test_type='all', verbose=True, coverage=False):
    """Run tests based on type"""
    project_root = Path(__file__).parent
    tests_dir = project_root / "tests"
    
    # Build pytest command
    cmd = ['python3', '-m', 'pytest']
    
    if verbose:
        cmd.append('-v')
    
    if coverage:
        cmd.extend(['--cov=src', '--cov-report=html', '--cov-report=term'])
    
    # Select test files based on type
    if test_type == 'unit':
        test_files = [
            'test_producer.py',
            'test_stream_processor.py',
            'test_data_loader.py',
            'test_endpoint.py'
        ]
        cmd.extend([str(tests_dir / f) for f in test_files])
    elif test_type == 'integration':
        test_files = [
            'test_producer_integration.py',
            'test_stream_processor_integration.py',
            'test_data_loader_integration.py'
        ]
        cmd.extend([str(tests_dir / f) for f in test_files if (tests_dir / f).exists()])
    elif test_type == 'all':
        cmd.append(str(tests_dir))
    elif test_type == 'producer':
        cmd.append(str(tests_dir / 'test_producer.py'))
        if (tests_dir / 'test_producer_integration.py').exists():
            cmd.append(str(tests_dir / 'test_producer_integration.py'))
    elif test_type == 'stream_processor':
        cmd.append(str(tests_dir / 'test_stream_processor.py'))
        if (tests_dir / 'test_stream_processor_integration.py').exists():
            cmd.append(str(tests_dir / 'test_stream_processor_integration.py'))
    elif test_type == 'data_loader':
        cmd.append(str(tests_dir / 'test_data_loader.py'))
        if (tests_dir / 'test_data_loader_integration.py').exists():
            cmd.append(str(tests_dir / 'test_data_loader_integration.py'))
    else:
        print_error(f"Unknown test type: {test_type}")
        return False
    
    print_header(f"Running {test_type.upper()} Tests")
    print(f"Command: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, cwd=project_root, check=False)
        return result.returncode == 0
    except FileNotFoundError:
        print_error("pytest not found. Install with: pip install pytest")
        return False
    except Exception as e:
        print_error(f"Error running tests: {e}")
        return False

def list_tests():
    """List all available tests"""
    print_header("Available Tests")
    
    tests_dir = Path(__file__).parent / "tests"
    
    if not tests_dir.exists():
        print_error("Tests directory not found")
        return
    
    test_files = sorted(tests_dir.glob("test_*.py"))
    
    if not test_files:
        print_warning("No test files found")
        return
    
    print("Unit Tests:")
    for f in test_files:
        if 'integration' not in f.name:
            print(f"  - {f.name}")
    
    print("\nIntegration Tests:")
    integration_tests = [f for f in test_files if 'integration' in f.name]
    if integration_tests:
        for f in integration_tests:
            print(f"  - {f.name}")
    else:
        print_warning("  No integration tests found")
    
    print(f"\nTotal: {len(test_files)} test file(s)")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Run tests for the cryptocurrency data pipeline project',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 run_tests.py                    # Run all tests
  python3 run_tests.py --type unit        # Run only unit tests
  python3 run_tests.py --type integration # Run only integration tests
  python3 run_tests.py --type producer    # Run producer tests only
  python3 run_tests.py --coverage         # Run with coverage report
  python3 run_tests.py --list             # List all available tests
        """
    )
    
    parser.add_argument(
        '--type', '-t',
        choices=['all', 'unit', 'integration', 'producer', 'stream_processor', 'data_loader'],
        default='all',
        help='Type of tests to run (default: all)'
    )
    
    parser.add_argument(
        '--coverage', '-c',
        action='store_true',
        help='Generate coverage report'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Run tests in quiet mode'
    )
    
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List all available tests'
    )
    
    parser.add_argument(
        '--check-deps',
        action='store_true',
        help='Check if dependencies are installed'
    )
    
    args = parser.parse_args()
    
    # List tests
    if args.list:
        list_tests()
        return
    
    # Check dependencies
    if args.check_deps:
        if not check_dependencies():
            sys.exit(1)
        return
    
    # Check dependencies before running tests
    if not check_dependencies():
        print_warning("Some dependencies are missing. Tests may fail.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Run tests
    success = run_tests(
        test_type=args.type,
        verbose=not args.quiet,
        coverage=args.coverage
    )
    
    # Print summary
    print_header("Test Summary")
    if success:
        print_success("All tests passed!")
        sys.exit(0)
    else:
        print_error("Some tests failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()
