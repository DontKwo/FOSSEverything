import pytest
from tests.matrix.ui.run_ui_matrix import run_ui_matrix


@pytest.mark.ui_matrix
def test_ui_matrix_smoke() -> None:
    # Run fast UI matrix smoke test subset across tools.
    res = run_ui_matrix(smoke=True, max_seconds=60.0)
    assert res["failed"] == 0, f"Smoke UI matrix had failures: {res['failures']}"
