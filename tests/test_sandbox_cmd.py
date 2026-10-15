from pathlib import Path

from vteuthis.sandbox import build_docker_cmd


def cmd() -> list[str]:
    return build_docker_cmd("python:3.12-slim", Path("/tmp/task"), 1000, 1000)


def test_hardening_flags_present():
    c = cmd()
    for flag in (
        "--cap-drop",
        "--security-opt",
        "--pids-limit",
        "--memory-swap",
        "--tmpfs",
        "--read-only",
        "--network",
    ):
        assert flag in c, f"missing {flag}"
    assert "ALL" in c
    assert "no-new-privileges" in c
    assert "none" in c
    assert any("noexec" in x for x in c)
    assert "512m" in c


def test_no_new_privileges_and_cap_drop():
    c = cmd()
    assert c[c.index("--cap-drop") + 1] == "ALL"
    assert c[c.index("--security-opt") + 1] == "no-new-privileges"
    assert c[c.index("--pids-limit") + 1] == "64"
    assert c[c.index("--memory-swap") + 1] == "512m"
    assert "none" == c[c.index("--network") + 1]


def test_user_and_readonly_and_tmpfs():
    c = cmd()
    assert f"{1000}:{1000}" == c[c.index("--user") + 1]
    assert "--read-only" in c
    tmpfs = c[c.index("--tmpfs") + 1]
    assert tmpfs.startswith("/tmp:")
    assert "noexec" in tmpfs and "nosuid" in tmpfs
