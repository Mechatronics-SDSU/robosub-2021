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
    red_box = Node(node_name='red_box', parent=ms.tree.root)
    blue_box = Node(node_name='blue_box', parent=ms.tree.root)
    locate_box_green = Node(node_name='locate_box', parent=green_box)
    turning_left_90 = Node(node_name='turning_left_90', parent=locate_box_green)
    drive_motor = Node(node_name='drive_motor', parent=turning_left_90)
    validate_angle = Node(node_name='validate_angle', parent=turning_left_90)
    turning_right_90 = Node(node_name='turning_right_90', parent=locate_box_green)
    drive_motor = Node(node_name='drive_motor', parent=turning_right_90)
    validate_angle = Node(node_name='validate_angle', parent=turning_right_90)
    align = Node(node_name='align', parent=locate_box_green)
    strafing_left = Node(node_name='strafing_left', parent=align)
    strafing_right = Node(node_name='strafing_right', parent=align)
    est_target_lock = Node(node_name='est_target_lock', parent=green_box)
    print(ms)
    print(ms.tree)


if __name__ == '__main__':
    run_test_mission()
