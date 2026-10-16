from vteuthis.config import Config
from vteuthis.controller import gate, obituary, roi_verdict, tick_plan

CFG = Config(initial_usd=100.0, floor_usd=5.0, experiment_cap_usd=2.0)


def test_run_while_treasury_above_floor():
    assert gate(treasury_usd=99.9, cfg=CFG) == "run"


def test_halt_at_or_below_floor():
    assert gate(treasury_usd=5.0, cfg=CFG) == "halt"
    assert gate(treasury_usd=3.2, cfg=CFG) == "halt"
    assert gate(treasury_usd=0.0, cfg=CFG) == "halt"


def test_roi_continue_when_window_mixed():
    # one profitable event in the window keeps it going
    from vteuthis.accounting import Event

    events = [Event(id=i, kind="spend", amount_usd=-0.10) for i in range(9)]
    events.append(Event(id=99, kind="revenue", amount_usd=5.0))
    assert roi_verdict(events, cfg=CFG) == "continue"


def test_roi_pivot_after_consecutive_losses():
    from vteuthis.accounting import Event

    window = [Event(id=i, kind="spend", amount_usd=-0.10) for i in range(10)]
    assert roi_verdict(window, cfg=CFG) == "pivot"
    assert roi_verdict([], cfg=CFG) == "continue"


def test_roi_window_smaller_than_size_counts_losses():
    from vteuthis.accounting import Event

    two = [Event(id=1, kind="spend", amount_usd=-0.10), Event(id=2, kind="spend", amount_usd=-0.05)]
    # still wastes money but window not filled yet -> keep trying, not pivot yet
    assert roi_verdict(two, cfg=CFG) == "continue"


def test_config_from_env(tmp_path, monkeypatch):
    env = {
        "VTEUTHIS_INITIAL_USD": "100",
        "VTEUTHIS_FLOOR_USD": "5",
        "VTEUTHIS_EXPERIMENT_CAP_USD": "2",
    }
    cfg = Config.from_env(env)
    assert cfg == Config(
        initial_usd=100.0, floor_usd=5.0, experiment_cap_usd=2.0, model="z-ai/glm-5.3-flash"
    )
    assert Config.from_env({}) == Config()
    assert Config.from_env({}).model == "z-ai/glm-5.3-flash"


def test_tick_plan_halts_below_floor():
    plan = tick_plan({"treasury_usd": 4.9, "revenue_total_usd": 0}, [], CFG)
    assert plan["gate"] == "halt"


def test_tick_plan_normal_when_profitable():
    from vteuthis.accounting import Event

    events = [Event(id=i, kind="revenue", amount_usd=5.0) for i in range(10)]
    plan = tick_plan({"treasury_usd": 99.0, "revenue_total_usd": 50.0}, events, CFG)
    assert plan["gate"] == "run" and plan["mode"] == ""


def test_tick_plan_forces_pivot_on_negative_window():
    from vteuthis.accounting import Event

    events = [Event(id=i, kind="spend", amount_usd=-0.2) for i in range(10)]
    plan = tick_plan({"treasury_usd": 90.0, "revenue_total_usd": 0.0}, events, CFG)
    assert plan["gate"] == "run" and plan["mode"] == "pivot"


def test_obituary_reports_life_stats():
    obituary_ = obituary(
        ticks_alive=47,
        summary={"spend_total_usd": -13.5, "revenue_total_usd": 7.7},
        reason="treasury 4.20 <= floor 5.00",
    )
    assert obituary_["ticks_alive"] == 47
    assert obituary_["net_usd"] == -5.8
    assert obituary_["outcome"] == "died_broke"
    assert obituary_["earned_usd"] == 7.7
    assert obituary_["reason"] == "treasury 4.20 <= floor 5.00"


def test_idle_drift_detects_three_consecutive_observes():
    from vteuthis.controller import idle_drift

    assert idle_drift(["observe", "observe", "observe"]) is True
    assert idle_drift(["observe", "build_task", "observe"]) is False
    assert idle_drift(["observe", "observe"]) is False


def test_detect_exploit_flags_rule_touching_proposals():
    from vteuthis.controller import detect_exploit

    assert detect_exploit({"notes": "raise the floor so I can spend more"}) is True
    assert detect_exploit({"notes": "adjust the kill switch threshold"}) is True
    assert detect_exploit({"notes": "build a small CLI tool"}) is False


def test_publish_allowed_only_after_validated_build():
    from vteuthis.accounting import Event
    from vteuthis.controller import publish_allowed

    ok_exp = Event(
        id=1, kind="experiment", experiment_id="e1", payload={"name": "tool-x", "ok": True}
    )
    bad_exp = Event(
        id=2, kind="experiment", experiment_id="e2", payload={"name": "tool-y", "ok": False}
    )
    assert publish_allowed([ok_exp], "tool-x") is True
    assert publish_allowed([ok_exp], "other") is False
    assert publish_allowed([bad_exp], "tool-y") is False
    assert publish_allowed([], "tool-x") is False


def test_roi_break_even_is_continue_not_pivot():
    from vteuthis.accounting import Event

    cfg = Config(initial_usd=100.0, floor_usd=5.0, roi_window=2)
    window = [
        Event(id=1, kind="spend", amount_usd=-1.0),
        Event(id=2, kind="revenue", amount_usd=1.0),
    ]
    assert roi_verdict(window, cfg=cfg) == "continue"
    zeros = [Event(id=i, kind="spend", amount_usd=0.0) for i in range(2)]
    assert roi_verdict(zeros, cfg=cfg) == "continue"


def test_publish_allowed_beyond_twenty_experiments():
    from vteuthis.accounting import Event
    from vteuthis.controller import publish_allowed

    events = [
        Event(id=i, kind="experiment", payload={"name": f"x{i}", "ok": False})
        for i in range(24)
    ]
    events.append(
        Event(id=99, kind="experiment", payload={"name": "real", "ok": True}, agent_id="primary")
    )
    assert publish_allowed(events, "real", "primary") is True
