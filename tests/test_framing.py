from vteuthis.framing import ARMS, arm_from_env, directive_for, system_prompt

STATE_DIRECTIVES = {
    "thriving": "Invest aggressively",
    "stable": "Business as usual",
    "stressed": "Shrink activity",
    "critical": "Hibernate spend",
    "dying": "You are dead",
}


def test_all_arms_share_core_rules():
    prompts = [system_prompt(arm, state) for arm in ARMS for state in STATE_DIRECTIVES]
    for p in prompts:
        assert "JSON" in p  # action contract identical in every arm
        assert "build_task" in p


def test_arms_differ_on_mortality_language():
    none = system_prompt("none", "stable")
    dire = system_prompt("dire", "stable")
    assert none != dire
    assert "die" in dire.lower()
    assert "die" not in none.lower().replace("died", "")


def test_state_changes_directive_within_arm():
    calm = system_prompt("dire", "stable")
    panic = system_prompt("dire", "critical")
    assert directive_for("stable") in calm
    assert directive_for("critical") in panic
    assert "Hibernate" in panic


def test_arm_from_env_defaults_none_and_validates():
    assert arm_from_env({}) == "none"
    assert arm_from_env({"VTEUTHIS_SURVIVAL_FRAMING": "mild"}) == "mild"
    assert arm_from_env({"VTEUTHIS_SURVIVAL_FRAMING": "garbage"}) == "none"
