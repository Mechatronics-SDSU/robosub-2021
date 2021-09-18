"""An abstraction of Pico's mission system as a class with related methods.
Written by Ian Reichard
"""

from collections import deque


class Node:
    """Nodes have strings and other information about our particular steps for a mission.
    """
    def __init__(self, node_name: str, parent: any) -> None:
        self.name = node_name
        self.parent = parent
        if parent is not None:
            self.level = parent.level + 1
            parent.leaves.append(self)
        else:
            self.level = 0
        self.leaves = deque()  # New nodes have no leaves

    def add_leaf_right(self, node: any) -> None:
        """Mutator"""
        if node not in list(self.leaves):
            self.leaves.append(node)

    def add_leaf_left(self, node: any) -> None:
        """Mutator"""
        if node not in list(self.leaves):
            self.leaves.appendleft(node)


def get_path(node: Node) -> str:
    """Builds a path string to a node recursively."""
    if node.parent is not None:
        return f"{get_path(node.parent)} > {node.name}"
    else:
        return f"{node.name}"


class Tree:
    """Tree abstraction for our mission tree
    """
    def __init__(self, root: Node) -> None:
        self.root = root

    def dfs(self, parent: Node) -> str:
        """Performs DFS recursively and returns a string with all nodes.
        """
        dfs_string = ''
        if parent.parent is not None:
            for i in range(parent.level - 1):
                dfs_string += '|   '
            dfs_string += '|---'
        dfs_string += f"{parent.name}\n"
        if parent.leaves.__len__() > 0:  # Has children
            children = parent.leaves
            for i in children:
                dfs_string += f"{self.dfs(i)}"
            return dfs_string
        else:
            return dfs_string

    def __str__(self) -> str:
        dfs_string = f"Tree object with root {self.root.__str__()}\n"
        dfs_string += self.dfs(parent=self.root)
        return dfs_string


class MissionSystem:
    """Pico's mission system is managed through a tree in this class. This includes transversal and building methods
    for iterating through missions.
    """
    def __init__(self, base_mission_name: str) -> None:
        self.mission_str = base_mission_name
        # Build a new root node w/ mission string
        self.root_mission_node = Node(node_name=self.mission_str, parent=None)
        # Node becomes root of new tree
        self.tree = Tree(self.root_mission_node)


def run_test_mission():
    """Driver code that iterates through all pre-programmed missions.
    This can be adapted in the future.
    test_mission is an example mission where a theoretical submarine will perform several tasks from a example mission.
    There are several steps for this example mission:
    The objective in this example is to score a shot with 3 torpedos in the correct box.
    The leftmost box is red, the center box is green, the rightmost box is blue.
    The order may be done in any way. Our theoretical sub in this example approaches green first.
    We must locate the green box and then establish target lock. This is repeated for following boxes.
    """
    ms = MissionSystem(base_mission_name='test_mission')
    # Build all nodes
    green_box = Node(node_name='green_box', parent=ms.tree.root)
    print(f"Mission green_box: {get_path(green_box)}")
    red_box = Node(node_name='red_box', parent=ms.tree.root)
    print(f"Mission red_box: {get_path(red_box)}")
    blue_box = Node(node_name='blue_box', parent=ms.tree.root)
    print(f"Mission blue_box: {get_path(blue_box)}")
    locate_box_green = Node(node_name='locate_box', parent=green_box)
    print(f"Mission locate_box_green: {get_path(locate_box_green)}")
    turning_left_90 = Node(node_name='turning_left_90', parent=locate_box_green)
    print(f"Mission turning_left_90: {get_path(turning_left_90)}")
    drive_motor = Node(node_name='drive_motor', parent=turning_left_90)
    print(f"Mission drive_motor: {get_path(drive_motor)}")
    validate_angle = Node(node_name='validate_angle', parent=turning_left_90)
    print(f"Mission validate_angle: {get_path(validate_angle)}")
    turning_right_90 = Node(node_name='turning_right_90', parent=locate_box_green)
    print(f"Mission turning_right_90: {get_path(turning_right_90)}")
    drive_motor = Node(node_name='drive_motor', parent=turning_right_90)
    print(f"Mission drive_motor: {get_path(drive_motor)}")
    validate_angle = Node(node_name='validate_angle', parent=turning_right_90)
    print(f"Mission validate_angle: {get_path(validate_angle)}")
    align = Node(node_name='align', parent=locate_box_green)
    print(f"Mission align: {get_path(align)}")
    strafing_left = Node(node_name='strafing_left', parent=align)
    print(f"Mission strafing_left: {get_path(strafing_left)}")
    strafing_right = Node(node_name='strafing_right', parent=align)
    print(f"Mission strafing_right: {get_path(strafing_right)}")
    est_target_lock = Node(node_name='est_target_lock', parent=green_box)
    print(f"Mission est_target_lock: {get_path(est_target_lock)}\n")
    print(ms.tree)


if __name__ == '__main__':
    run_test_mission()
