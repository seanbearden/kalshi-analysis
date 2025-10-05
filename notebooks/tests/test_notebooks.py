"""Tests for Jupyter notebook execution.

Tests that notebooks can execute without errors.
Uses pytest and nbconvert to validate notebook cells.
"""

import pytest
from pathlib import Path
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor, CellExecutionError


# List of notebooks to test
NOTEBOOKS = [
    "01_data_exploration.ipynb",
    "02_strategy_backtest.ipynb",
    "03_calibration_analysis.ipynb",
    "04_strategy_optimization.ipynb",
]


@pytest.mark.parametrize("notebook_name", NOTEBOOKS)
def test_notebook_execution(notebook_name, notebooks_dir, has_database):
    """Test that notebook executes without errors.

    Args:
        notebook_name: Name of notebook file
        notebooks_dir: Path to notebooks directory
        has_database: Whether test database is available
    """
    notebook_path = notebooks_dir / notebook_name

    if not notebook_path.exists():
        pytest.skip(f"Notebook {notebook_name} not found")

    # Skip database-dependent notebooks if no database
    if not has_database:
        pytest.skip(f"Skipping {notebook_name} - requires database connection")

    # Read notebook
    with open(notebook_path) as f:
        nb = nbformat.read(f, as_version=4)

    # Configure execution
    ep = ExecutePreprocessor(
        timeout=300,  # 5 minutes max per notebook
        kernel_name='python3',
        allow_errors=False  # Fail on any cell error
    )

    try:
        # Execute notebook
        ep.preprocess(nb, {'metadata': {'path': str(notebooks_dir)}})

    except CellExecutionError as e:
        # Provide detailed error information
        pytest.fail(
            f"Notebook {notebook_name} failed to execute:\n"
            f"Cell {e.traceback_text}"
        )


@pytest.mark.parametrize("notebook_name", NOTEBOOKS)
def test_notebook_syntax(notebook_name, notebooks_dir):
    """Test that notebook has valid JSON structure and no syntax errors.

    This test runs even without a database.
    """
    notebook_path = notebooks_dir / notebook_name

    if not notebook_path.exists():
        pytest.skip(f"Notebook {notebook_name} not found")

    # Read and validate notebook structure
    with open(notebook_path) as f:
        nb = nbformat.read(f, as_version=4)

    # Basic validation
    assert 'cells' in nb, "Notebook missing cells"
    assert len(nb['cells']) > 0, "Notebook has no cells"

    # Check for common issues in cells
    for i, cell in enumerate(nb['cells']):
        if cell['cell_type'] == 'code':
            source = ''.join(cell['source'])

            # Check for syntax errors (basic validation)
            if source.strip():
                try:
                    compile(source, f'<cell {i}>', 'exec')
                except SyntaxError as e:
                    pytest.fail(
                        f"Syntax error in {notebook_name} cell {i}:\n{e}"
                    )


def test_notebooks_have_markdown_cells(notebooks_dir):
    """Test that notebooks have documentation (markdown cells)."""
    for notebook_name in NOTEBOOKS:
        notebook_path = notebooks_dir / notebook_name

        if not notebook_path.exists():
            continue

        with open(notebook_path) as f:
            nb = nbformat.read(f, as_version=4)

        markdown_cells = [c for c in nb['cells'] if c['cell_type'] == 'markdown']

        assert len(markdown_cells) > 0, (
            f"{notebook_name} should have markdown cells for documentation"
        )


def test_notebooks_import_utils(notebooks_dir):
    """Test that notebooks properly import utils modules."""
    # Only check notebooks that use utils
    notebooks_using_utils = [
        "03_calibration_analysis.ipynb",
        "04_strategy_optimization.ipynb",
    ]

    for notebook_name in notebooks_using_utils:
        notebook_path = notebooks_dir / notebook_name

        if not notebook_path.exists():
            continue

        with open(notebook_path) as f:
            nb = nbformat.read(f, as_version=4)

        # Check for utils imports
        has_utils_import = False
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                source = ''.join(cell['source'])
                if 'from utils' in source or 'import utils' in source:
                    has_utils_import = True
                    break

        assert has_utils_import, (
            f"{notebook_name} should import from utils module"
        )
