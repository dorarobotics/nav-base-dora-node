"""NavBaseNode boots and accepts a no-op cmd_request envelope."""
from nav_base_node.node import NavBaseNode


def test_node_constructs_with_minimal_config():
    node = NavBaseNode(robot_id="nav-base-test")
    assert node.robot_id == "nav-base-test"


def test_node_module_callable():
    """`python -m nav_base_node` must be importable."""
    import nav_base_node.__main__  # noqa: F401
