"""Tests des parties pures (sans navigateur) : egress, parsing, config."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import egress, kick, store


def test_egress_allowlist():
    assert egress.host_allowed("kick.com")
    assert egress.host_allowed("web.kick.com")
    assert egress.host_allowed("files.kick.com")
    assert not egress.host_allowed("evil.com")
    assert not egress.host_allowed("kick.com.evil.com")
    assert not egress.host_allowed("evilkick.com")
    assert egress.assert_allowed("https://web.kick.com/api/v1/drops/campaigns")
    for bad in ("https://evil.com/x", "http://example.org"):
        try:
            egress.assert_allowed(bad)
            assert False, "aurait du bloquer " + bad
        except egress.EgressError:
            pass


def test_parse_campaigns():
    resp = {
        "data": [
            {
                "id": 1, "name": "Drop A", "status": "active",
                "category": {"name": "GameX", "slug": "gamex"},
                "rewards": [{"id": 9, "name": "Skin"}],
                "channels": [{"slug": "streamer1"}, {"slug": "streamer2"}, {"nope": 1}],
            },
            {"id": 2, "name": "Inactive sans chaine", "status": "ended", "channels": []},
            "garbage",
        ]
    }
    out = kick.parse_campaigns(resp)
    assert len(out) == 1
    c = out[0]
    assert c["name"] == "Drop A" and c["game"] == "GameX"
    assert [ch["slug"] for ch in c["channels"]] == ["streamer1", "streamer2"]
    assert c["channels"][0]["url"] == "https://kick.com/streamer1"
    assert kick.parse_campaigns({}) == []
    assert kick.parse_campaigns("bad") == []


def test_config_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        store.DATA_DIR = d
        store.CONFIG_PATH = os.path.join(d, "config.json")
        cfg = store.load_config()
        assert cfg["target_minutes"] == 120 and cfg["mute"] is True
        cfg["selected_channels"] = ["a", "b"]
        store.save_config(cfg)
        again = store.load_config()
        assert again["selected_channels"] == ["a", "b"]


if __name__ == "__main__":
    test_egress_allowlist()
    test_parse_campaigns()
    test_config_roundtrip()
    print("OK: 3 tests passes")
