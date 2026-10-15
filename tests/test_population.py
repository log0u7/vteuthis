from vteuthis.population import partition, reallocate


def test_partition_splits_budget_cent_exact():
    slices = partition(100.0, ["a", "b", "c"])
    assert slices == {"a": 33.34, "b": 33.33, "c": 33.33}


def test_partition_empty_population():
    assert partition(100.0, []) == {}


def test_reallocate_redistributes_dead_to_survivors():
    before = {"a": 30.0, "b": 40.0, "c": 30.0}
    after = reallocate(before, dead=["b"])
    assert "b" not in after
    assert after == {"a": 50.0, "c": 50.0}
    assert round(sum(after.values()), 6) == 100.0


def test_reallocate_conserves_total_with_odd_split():
    before = {"a": 10.0, "b": 5.0, "c": 85.0}
    after = reallocate(before, dead=["c"])
    assert round(sum(after.values()), 6) == 100.0
    assert set(after) == {"a", "b"}


def test_reallocate_all_dead_empties_population():
    assert reallocate({"a": 5.0}, dead=["a"]) == {}


def test_reallocate_no_dead_is_identity():
    before = {"a": 10.0, "b": 10.0}
    assert reallocate(before, dead=[]) == before
