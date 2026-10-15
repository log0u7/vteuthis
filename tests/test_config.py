from vteuthis.config import merge_env


def test_runtime_env_wins_over_file():
    assert merge_env({"A": "file"}, {"A": "runtime"}) == {"A": "runtime"}


def test_file_fills_gaps():
    merged = merge_env({"A": "1", "B": "2"}, {"A": "9"})
    assert merged == {"A": "9", "B": "2"}


def test_file_only_kept_when_no_runtime_override():
    assert merge_env({"B": "2"}, {}) == {"B": "2"}
