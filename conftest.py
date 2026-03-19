from __future__ import annotations

from pathlib import Path
from typing import List, Sequence

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add a flag to optionally include integration tests."""
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Include integration tests (tests under tests/integration).",
    )


def _is_integration_test(nodeid: str, fspath: Path) -> bool:
    """Return True if this test item should be treated as an integration test.

    Currently anything under tests/integration/ is considered integration.
    """
    parts: Sequence[str] = tuple(fspath.parts)
    return "tests" in parts and "integration" in parts


def pytest_collection_modifyitems(
    config: pytest.Config, items: List[pytest.Item]
) -> None:
    """Mark integration tests and skip them by default unless --integration is set."""
    include_integration = config.getoption("--integration")

    for item in items:
        # Normalise to a Path instance; item.fspath is a py.path.local
        fspath = Path(str(item.fspath))

        if _is_integration_test(item.nodeid, fspath):
            item.add_marker(pytest.mark.integration)

            if not include_integration:
                skip_marker = pytest.mark.skip(
                    reason="integration test (run with --integration to include)"
                )
                item.add_marker(skip_marker)

