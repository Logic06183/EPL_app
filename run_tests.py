#!/usr/bin/env python3

import sys
import pytest
import argparse
import logging
from pathlib import Path

# Suppress warnings during testing
logging.getLogger("tensorflow").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)

def main():
    parser = argparse.ArgumentParser(description='Run FPL Prediction App tests')
    parser.add_argument('--unit', action='store_true', help='Run only unit tests')
    parser.add_argument('--integration', action='store_true', help='Run only integration tests')
    parser.add_argument('--api', action='store_true', help='Run only API tests')
    parser.add_argument('--fast', action='store_true', help='Skip slow tests')
    parser.add_argument('--coverage', action='store_true', help='Run with coverage report')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--file', '-f', help='Run specific test file')
    parser.add_argument('--function', help='Run specific test function')
    
    args = parser.parse_args()
    
    # Build pytest arguments
    pytest_args = []
    
    if args.verbose:
        pytest_args.extend(['-v', '-s'])
    
    if args.coverage:
        pytest_args.extend([
            '--cov=src',
            '--cov-report=html:htmlcov',
            '--cov-report=term-missing',
            '--cov-fail-under=70'
        ])
    
    # Test selection
    if args.unit:
        pytest_args.extend(['-m', 'unit or not integration and not api'])
    elif args.integration:
        pytest_args.extend(['-m', 'integration'])
    elif args.api:
        pytest_args.extend(['-m', 'api'])
    
    if args.fast:
        pytest_args.extend(['-m', 'not slow'])
    
    if args.file:
        pytest_args.append(f'tests/{args.file}')
        if args.function:
            pytest_args[-1] += f'::{args.function}'
    elif args.function:
        pytest_args.extend(['-k', args.function])
    
    # Add default test directory if no specific file
    if not args.file:
        pytest_args.append('tests/')
    
    print("Running FPL Prediction App Tests")
    print("=" * 50)
    print(f"Command: pytest {' '.join(pytest_args)}")
    print("=" * 50)
    
    # Run pytest
    exit_code = pytest.main(pytest_args)
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code: {exit_code}")
    
    return exit_code

if __name__ == '__main__':
    sys.exit(main())