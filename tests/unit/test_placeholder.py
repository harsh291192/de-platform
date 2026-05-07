"""
Placeholder test — ensures pytest finds at least one test.
Delete this file once real unit tests are added.
"""


def test_project_structure():
    """Verify basic project structure exists."""
    import os

    assert os.path.exists("ingestion"), "ingestion/ folder missing"
    assert os.path.exists("processing"), "processing/ folder missing"
    assert os.path.exists("dbt"), "dbt/ folder missing"
    assert os.path.exists("orchestration"), "orchestration/ folder missing"
    assert os.path.exists("tests"), "tests/ folder missing"
