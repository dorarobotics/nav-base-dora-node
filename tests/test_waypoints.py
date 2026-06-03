from nav_base_node.waypoints import Waypoints, load_waypoints


def test_load_waypoints_from_yaml(tmp_path):
    yml = tmp_path / "wp.yaml"
    yml.write_text(
        "home:\n"
        "  position: [0.0, 0.0, 0.0]\n"
        "  orientation: [0.0, 0.0, 0.0, 1.0]\n"
        "kitchen:\n"
        "  position: [3.0, 1.5, 0.0]\n"
        "  orientation: [0.0, 0.0, 0.707, 0.707]\n"
    )
    wp: Waypoints = load_waypoints(str(yml))
    assert "home" in wp.names()
    assert wp.lookup("kitchen")["position"] == [3.0, 1.5, 0.0]


def test_lookup_unknown_raises(tmp_path):
    yml = tmp_path / "wp.yaml"
    yml.write_text("home:\n  position: [0,0,0]\n  orientation: [0,0,0,1]\n")
    wp = load_waypoints(str(yml))
    try:
        wp.lookup("attic")
    except KeyError as e:
        assert "attic" in str(e)
    else:
        raise AssertionError("expected KeyError")
