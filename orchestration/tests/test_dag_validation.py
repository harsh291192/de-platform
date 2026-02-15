"""Validate all Airflow DAGs load without errors."""

import pytest


def test_dags_folder_exists():
    """Basic check — dags folder exists."""
    import os

    assert os.path.exists("orchestration/dags"), "orchestration/dags folder missing"


def test_no_dag_import_errors():
    """All DAGs should import without syntax or import errors."""
    try:
        from airflow.models import DagBag

        dag_bag = DagBag(dag_folder="orchestration/dags", include_examples=False)
        assert (
            len(dag_bag.import_errors) == 0
        ), f"DAG import errors found: {dag_bag.import_errors}"
    except ImportError:
        pytest.skip("Airflow not installed — skipping DAG validation")
