# TrailBuster Test Suite

This directory contains comprehensive tests for the TrailBuster Salesforce Trailhead automation tool.

## Test Structure

```
tests/
├── __init__.py                 # Package initialization
├── conftest.py                 # PyTest configuration and fixtures
├── run_tests.py               # Custom test runner script
├── test_helpers.py            # Test utilities and helper functions
├── README.md                  # This file
├── fixtures/                  # Test data and HTML fixtures
│   ├── __init__.py
│   ├── test_data.py          # Sample data for testing
│   ├── mock_lesson.html      # Mock lesson HTML for testing
│   ├── mock_module.html      # Mock module HTML for testing
│   ├── mock_trail.html       # Mock trail HTML for testing
│   ├── lesson.html           # Real Trailhead lesson HTML (copied from root)
│   ├── module.html           # Real Trailhead module HTML (copied from root)
│   └── trail.html            # Real Trailhead trail HTML (copied from root)
├── unit/                      # Unit tests
│   ├── __init__.py
│   └── test_parse.py         # Tests for salesforce/parse.py functions
└── integration/               # Integration tests
    ├── __init__.py
    └── test_crawl.py         # Tests for crawl.py functionality
```

## Running Tests

### Using the Custom Test Runner

The custom test runner (`run_tests.py`) provides comprehensive test execution with dependency checking:

```bash
# Run all tests
python tests/run_tests.py

# Run specific test types
python tests/run_tests.py unit          # Unit tests only
python tests/run_tests.py integration   # Integration tests only
python tests/run_tests.py parse         # Parse function tests only
python tests/run_tests.py crawl         # Crawl function tests only

# Check dependencies
python tests/run_tests.py --check-deps

# Set up test environment
python tests/run_tests.py --setup-env

# Verbose output
python tests/run_tests.py --verbose
```

### Using unittest

Standard Python unittest runner:

```bash
# Run all tests
python -m unittest discover tests

# Run specific test files
python -m unittest tests.unit.test_parse
python -m unittest tests.integration.test_crawl

# Run specific test classes
python -m unittest tests.unit.test_parse.TestParseModule
python -m unittest tests.integration.test_crawl.TestTrailheadCrawlerIntegration

# Run with verbose output
python -m unittest discover tests -v
```

### Using pytest (if installed)

```bash
# Run all tests
pytest

# Run specific test types
pytest tests/unit/              # Unit tests only
pytest tests/integration/       # Integration tests only

# Run with coverage
pytest --cov=salesforce --cov=crawl

# Run with specific markers
pytest -m unit                  # Unit tests only
pytest -m integration           # Integration tests only
```

## Test Categories

### Unit Tests (`tests/unit/`)

Test individual functions and components in isolation:

- **test_parse.py**: Tests for all functions in `salesforce/parse.py`
  - Content extraction functions (`_extract_title`, `_extract_learning_objectives`, etc.)
  - Main parsing functions (`parse_lesson`, `parse_module`)
  - Dataclass functionality (`ContentItem`, `LessonContent`, `ModuleContent`)
  - Error handling and edge cases
  - Real HTML fixture parsing

### Integration Tests (`tests/integration/`)

Test complete workflows and component interactions:

- **test_crawl.py**: Tests for `TrailheadCrawler` class and crawling workflows
  - Module crawling with mocked authentication
  - Trail crawling and multi-module processing
  - File operations and data persistence
  - Progress tracking and resume functionality
  - Batch URL processing
  - Error handling and retry logic

## Test Fixtures

### Mock HTML Files

Created specifically for testing with known, controlled content:

- **mock_lesson.html**: Simple lesson page with all expected elements
- **mock_module.html**: Module overview page with lesson links
- **mock_trail.html**: Trail page with module links

### Real HTML Files

Actual Trailhead pages copied from the root directory:

- **lesson.html**: Real lesson page from Trailhead
- **module.html**: Real module page from Trailhead  
- **trail.html**: Real trail page from Trailhead

### Test Data

- **test_data.py**: Sample data objects and HTML templates for testing

## Dependencies

### Required for Running Tests

- `playwright`: For browser automation testing
- `python-dotenv`: For environment variable handling
- Standard library modules: `unittest`, `json`, `tempfile`, etc.

### Optional

- `pytest`: Alternative test runner with additional features
- `pytest-cov`: Coverage reporting for pytest

### Setup Commands

```bash
# Install Playwright browsers
python -m playwright install

# Install test dependencies (if using pip)
pip install playwright python-dotenv

# Install test dependencies (if using poetry)
poetry install --with dev
```

## Test Environment Setup

The test suite includes automatic environment setup and dependency checking:

1. **Dependency Verification**: Checks that all required modules are importable
2. **Playwright Setup**: Verifies that Playwright browsers are installed
3. **Fixture Validation**: Ensures all required test fixtures exist
4. **Temporary Directories**: Creates isolated temporary directories for each test

## Test Data and Mocking

### Mocking Strategy

- **SalesforceAuth**: Mocked to avoid actual authentication during tests
- **Playwright Pages**: Mocked or use real browser instances with local HTML files
- **File System**: Tests use temporary directories to avoid affecting real files

### Test Data Philosophy

- **Controlled Data**: Mock HTML files with known, predictable content
- **Real Data**: Actual Trailhead HTML files to test real-world parsing
- **Edge Cases**: Empty pages, malformed HTML, missing elements

## Writing New Tests

### Unit Test Example

```python
def test_new_parse_function(self):
    \"\"\"Test a new parsing function.\"\"\"
    self._load_fixture("mock_lesson.html")
    result = new_parse_function(self.page)
    
    self.assertIsNotNone(result)
    self.assertIsInstance(result, ExpectedType)
    # Add specific assertions
```

### Integration Test Example

```python
@patch('crawl.parse_module')
def test_new_crawl_feature(self, mock_parse):
    \"\"\"Test a new crawling feature.\"\"\"
    mock_parse.return_value = mock_module_data
    
    result = self.crawler.new_crawl_method(test_url, self.mock_auth)
    
    self.assertIsNotNone(result)
    # Add specific assertions
```

### Best Practices

1. **Test Names**: Use descriptive names that explain what is being tested
2. **Setup/Teardown**: Use proper setup and teardown to ensure test isolation
3. **Assertions**: Include multiple specific assertions, not just "not None"
4. **Error Cases**: Test both success and failure scenarios
5. **Mock Appropriately**: Mock external dependencies but test real logic
6. **Documentation**: Add docstrings explaining what each test validates

## Continuous Integration

The test suite is designed to work in CI environments:

- Uses headless browser mode by default
- Creates temporary directories that are automatically cleaned up
- Provides detailed output and error reporting
- Returns appropriate exit codes for CI systems

## Troubleshooting

### Common Issues

1. **Playwright Not Installed**: Run `python -m playwright install`
2. **Import Errors**: Ensure the project root is in Python path
3. **File Permissions**: Ensure write permissions for temporary directories
4. **Browser Issues**: Try running tests with `--headless` flag

### Debug Mode

For debugging test failures:

```bash
# Run with verbose output
python tests/run_tests.py --verbose

# Run specific failing test
python -m unittest tests.unit.test_parse.TestParseModule.test_failing_method -v

# Add print statements or use debugger in test code
```

## Coverage Reports

If using pytest with coverage:

```bash
# Generate coverage report
pytest --cov=salesforce --cov=crawl --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Contributing

When adding new functionality to TrailBuster:

1. **Add Unit Tests**: Test individual functions in isolation
2. **Add Integration Tests**: Test complete workflows
3. **Update Fixtures**: Add new mock data if needed
4. **Update Documentation**: Update this README and test docstrings
5. **Run Full Suite**: Ensure all tests pass before submitting