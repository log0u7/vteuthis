
from vteuthis.activities import burn_share


def test_burn_share_splits_evenly():
    assert burn_share(1.0, 0.0, 3) == 0.3333
    assert burn_share(1.0, 0.0, 2) == 0.5


def test_burn_share_clamps_negative_delta():
    assert burn_share(0.5, 1.0, 3) == 0.0


def test_burn_share_no_agents_is_zero():
    assert burn_share(1.0, 0.0, 0) == 0.0


def test_burn_share_single_agent_bears_all():
    assert burn_share(2.0, 0.0, 1) == 2.0
