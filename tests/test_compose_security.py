import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_all_port_bindings_are_localhost():
    text = (ROOT / "docker-compose.yml").read_text()
    binds = re.findall(r'-\s*"([^"]*\d+:\d+)"', text)
    assert binds, "no port bindings found in docker-compose.yml"
    for b in binds:
        host = b.split(":")[0]
        assert host == "127.0.0.1", f"non-localhost port binding: {b}"


def test_temporal_ui_is_not_world_bound():
    text = (ROOT / "docker-compose.yml").read_text()
    assert "0.0.0.0" not in text
