#!/usr/bin/env python3
"""Test runner for TrailBuster test suite."""

import argparse
import os
import sys
import unittest
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.test_helpers import create_comprehensive_test_suite, run_all_tests


def discover_tests(test_dir: str = None) -> unittest.TestSuite:
    """Discover all tests in the tests directory."""
    if test_dir is None:
        test_dir = str(Path(__file__).parent)

    loader = unittest.TestLoader()
    suite = loader.discover(test_dir, pattern="test_*.py")
    return suite


def run_unit_tests():
    """Run only unit tests."""
    test_dir = str(Path(__file__).parent / "unit")
    suite = discover_tests(test_dir)
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


def run_integration_tests():
    """Run only integration tests."""
    test_dir = str(Path(__file__).parent / "integration")
    suite = discover_tests(test_dir)
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


def run_parse_tests():
    """Run only parse-related tests."""
    from tests.unit.test_parse import TestParseModule, TestParseWithRealFixtures

    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestParseModule))
    suite.addTest(unittest.makeSuite(TestParseWithRealFixtures))

    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


def run_crawl_tests():
    """Run only crawl-related tests."""
    from tests.integration.test_crawl import (
        TestCrawlerFileOperations,
        TestTrailheadCrawlerIntegration,
    )

    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestTrailheadCrawlerIntegration))
    suite.addTest(unittest.makeSuite(TestCrawlerFileOperations))

    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


def check_dependencies():
    """Check if all required dependencies are available."""
    required_modules = ["playwright", "salesforce.auth", "salesforce.parse", "crawl"]

    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError as e:
            missing_modules.append((module, str(e)))

    if missing_modules:
        print("❌ Missing required dependencies:")
        for module, error in missing_modules:
            print(f"  - {module}: {error}")
        return False

    print("✅ All required dependencies are available")
    return True


def setup_test_environment():
    """Set up the test environment."""
    # Check if playwright browsers are installed
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            # Try to launch a browser to check if it's installed
            browser = p.chromium.launch(headless=True)
            browser.close()
        print("✅ Playwright browsers are installed")
    except Exception as e:
        print(f"❌ Playwright browsers not properly installed: {e}")
        print("💡 Run: python -m playwright install")
        return False

    # Check if HTML fixtures exist
    fixtures_path = Path(__file__).parent / "fixtures"
    required_fixtures = ["mock_lesson.html", "mock_module.html", "mock_trail.html"]

    missing_fixtures = []
    for fixture in required_fixtures:
        if not (fixtures_path / fixture).exists():
            missing_fixtures.append(fixture)

    if missing_fixtures:
        print(f"❌ Missing test fixtures: {', '.join(missing_fixtures)}")
        return False

    print("✅ Test environment is properly set up")
    return True


def print_test_summary(result: unittest.TestResult):
    """Print a summary of test results."""
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped) if hasattr(result, "skipped") else 0

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_tests - failures - errors - skipped}")
    print(f"Failed: {failures}")
    print(f"Errors: {errors}")
    print(f"Skipped: {skipped}")

    if failures > 0:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}")

    if errors > 0:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}")

    success_rate = (
        ((total_tests - failures - errors) / total_tests * 100)
        if total_tests > 0
        else 0
    )
    print(f"\nSuccess Rate: {success_rate:.1f}%")

    if failures == 0 and errors == 0:
        print("🎉 All tests passed!")
    else:
        print("❌ Some tests failed")

    return failures == 0 and errors == 0


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(description="TrailBuster Test Runner")
    parser.add_argument(
        "test_type",
        nargs="?",
        choices=["all", "unit", "integration", "parse", "crawl"],
        default="all",
        help="Type of tests to run (default: all)",
    )
    parser.add_argument(
        "--check-deps",
        action="store_true",
        help="Check dependencies before running tests",
    )
    parser.add_argument(
        "--setup-env", action="store_true", help="Set up test environment"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    print("🧪 TrailBuster Test Suite")
    print("=" * 40)

    # Check dependencies if requested
    if args.check_deps:
        if not check_dependencies():
            sys.exit(1)
        return

    # Set up environment if requested
    if args.setup_env:
        if not setup_test_environment():
            sys.exit(1)
        return

    # Check basic setup
    if not check_dependencies():
        print("\n💡 Run with --check-deps to see detailed dependency information")
        sys.exit(1)

    if not setup_test_environment():
        print("\n💡 Run with --setup-env to set up the test environment")
        sys.exit(1)

    # Run tests based on type
    print(f"\n🚀 Running {args.test_type} tests...\n")

    try:
        if args.test_type == "all":
            result = run_all_tests()
        elif args.test_type == "unit":
            result = run_unit_tests()
        elif args.test_type == "integration":
            result = run_integration_tests()
        elif args.test_type == "parse":
            result = run_parse_tests()
        elif args.test_type == "crawl":
            result = run_crawl_tests()
        else:
            print(f"❌ Unknown test type: {args.test_type}")
            sys.exit(1)

        # Print summary and exit with appropriate code
        success = print_test_summary(result)
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        import traceback

        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
