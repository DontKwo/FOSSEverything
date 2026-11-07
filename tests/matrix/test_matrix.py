import pytest
from tests.matrix.run_api_matrix import run_matrix


@pytest.mark.matrix
def test_matrix_smoke() -> None:
    # Run fast smoke matrix test subset verifying core API methods.
    res = run_matrix(smoke=True, max_seconds=45.0)
    assert res["failed"] == 0, f"Smoke matrix had failures: {res['failures']}"
