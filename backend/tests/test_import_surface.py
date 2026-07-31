"""Guard rail: every module under app/ must import with only the dev extra installed.

CI runs `pip install -e ".[dev]"`, never `.[ml]`. A module-scope `import torch` or
`from sklearn.cluster import DBSCAN` therefore breaks the whole application at import
time, and so does a genuine runtime dependency that nobody remembered to declare in
pyproject.toml. Both have happened. Heavy ML imports belong inside a lazy accessor such
as `_torch()` in app/ml/flood_lstm.py or `_dbscan()` in app/ml/wildfire_cluster.py.

This test walks the package and imports every module so that mistake fails here rather
than at request time in production.
"""

from __future__ import annotations

import importlib
import pkgutil

import pytest

import app


def _module_names() -> list[str]:
    names = sorted(info.name for info in pkgutil.walk_packages(app.__path__, prefix="app."))
    assert names, "walk_packages found no modules under app/"
    return names


@pytest.mark.parametrize("module_name", _module_names())
def test_module_imports_without_ml_extra(module_name: str) -> None:
    importlib.import_module(module_name)
