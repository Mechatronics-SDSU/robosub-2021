"""Pico's mission system using the mission builder.
Designed for the original minisub competition tasks.
Written by Ian Reichard
"""

import time

import src.utils.mission_tree as mission_sys


def build_gate_mission(gate_node: mission_sys.Node) -> None:
    """Given the root node of the gate mission, build out the mission step by step.
    :param gate_node: Node for the parent gate mission.
    """
    submerge = mission_sys.Node(node_name='submerge', parent=gate_node)
    engage_down_thrusters = mission_sys.Node(node_name='engage_down_thrusters', parent=submerge)
    locate = mission_sys.Node(node_name='locate', parent=gate_node)
    radial_search = mission_sys.Node(node_name='radial_search', parent=locate)
    turn_port_step = mission_sys.Node(node_name='turn_port_step', parent=radial_search)
    video_analysis = mission_sys.Node(node_name='video_analysis', parent=radial_search)
    linear_search = mission_sys.Node(node_name='linear_search', parent=locate)
    forward_step = mission_sys.Node(node_name='forward_step', parent=linear_search)
    video_analysis = mission_sys.Node(node_name='video_analysis', parent=linear_search)
    perform_alignment = mission_sys.Node(node_name='perform_alignment', parent=gate_node)
    approach = mission_sys.Node(node_name='approach', parent=perform_alignment)
    move_step = mission_sys.Node(node_name='move_step', parent=approach)
    turn_step = mission_sys.Node(node_name='turn_step', parent=approach)
    video_analysis = mission_sys.Node(node_name='video_analysis', parent=approach)
    nav_backwards = mission_sys.Node(node_name='nav_backwards', parent=gate_node)
    engage_aft_thrusters = mission_sys.Node(node_name='engage_aft_thrusters', parent=nav_backwards)


def build_buoy_mission(buoy_node: mission_sys.Node) -> None:
    """Given the root node of the buoy mission, build out the mission step by step.
    :param buoy_node: Node for the parent buoy mission.
    """
    locate = mission_sys.Node(node_name='locate', parent=buoy_node)
    radial_search = mission_sys.Node(node_name='radial_search', parent=locate)
    turn_port_step = mission_sys.Node(node_name='turn_port_step', parent=radial_search)
    video_analysis = mission_sys.Node(node_name='video_analysis', parent=radial_search)
    linear_search = mission_sys.Node(node_name='linear_search', parent=locate)
    forward_step = mission_sys.Node(node_name='forward_step', parent=linear_search)
    video_analysis = mission_sys.Node(node_name='video_analysis', parent=linear_search)
    contact = mission_sys.Node(node_name='contact', parent=buoy_node)
    perform_alignment = mission_sys.Node(node_name='perform_alignment', parent=contact)
    move_step = mission_sys.Node(node_name='move_step', parent=perform_alignment)
    turn_step = mission_sys.Node(node_name='turn_step', parent=perform_alignment)
    video_analysis = mission_sys.Node(node_name='video_analysis', parent=perform_alignment)
    bump = mission_sys.Node(node_name='bump', parent=contact)
    engage_forward_thrusters = mission_sys.Node(node_name='engage_forward_thrusters', parent=bump)
    circle_perimeter = mission_sys.Node(node_name='circle_perimeter', parent=buoy_node)
    perform_alignment = mission_sys.Node(node_name='perform_alignment', parent=circle_perimeter)
    engage_aft_thrusters = mission_sys.Node(node_name='engage_aft_thrusters', parent=perform_alignment)
    move_step = mission_sys.Node(node_name='move_step', parent=perform_alignment)
    turn_step = mission_sys.Node(node_name='turn_step', parent=perform_alignment)
    circle_step = mission_sys.Node(node_name='circle_step', parent=circle_perimeter)


def build_rise_mission(rise_node: mission_sys.Node) -> None:
    """Given the root node of the rise mission, build out the mission step by step.
    :param rise_node: Node for the parent rise mission.
    """
    locate = mission_sys.Node(node_name='locate', parent=rise_node)
    radial_search = mission_sys.Node(node_name='radial_search', parent=locate)
    turn_port_step = mission_sys.Node(node_name='turn_port_step', parent=radial_search)
    video_analysis = mission_sys.Node(node_name='video_analysis', parent=radial_search)
    linear_search = mission_sys.Node(node_name='linear_search', parent=locate)
    forward_step = mission_sys.Node(node_name='forward_step', parent=linear_search)
    video_analysis = mission_sys.Node(node_name='video_analysis', parent=linear_search)
    perform_alignment = mission_sys.Node(node_name='perform_alignment', parent=rise_node)
    move_step = mission_sys.Node(node_name='move_step', parent=perform_alignment)
    turn_step = mission_sys.Node(node_name='turn_step', parent=perform_alignment)
    engage_up_thrusters = mission_sys.Node(node_name='engage_up_thrusters', parent=rise_node)


def build_tree(missions: tuple) -> mission_sys.MissionSystem:
    """Builds Pico's mission tree for the minisub tasks.
    :param missions: string list of all missions we are doing for this run.
    :return MissionSystem object with a member tree.
    """
    ms = mission_sys.MissionSystem(base_mission_name='(root)')
    if len(missions) == 0:  # No missions
        return ms
    if 'gate' in missions:  # Add gate mission data
        gate_mission_node = mission_sys.Node(node_name='gate_mission', parent=ms.tree.root)
        build_gate_mission(gate_node=gate_mission_node)
    if 'buoy' in missions:  # Add gate mission data
        buoy_mission_node = mission_sys.Node(node_name='buoy_mission', parent=ms.tree.root)
        build_buoy_mission(buoy_node=buoy_mission_node)
    if 'rise' in missions:  # Add gate mission data
        rise_mission_node = mission_sys.Node(node_name='rise_mission', parent=ms.tree.root)
        build_rise_mission(rise_node=rise_mission_node)
    return ms


def main() -> None:
    """Driver that builds Pico's mission tree and iterates through all missions.
    """
    ms = build_tree(missions=('gate', 'buoy', 'rise'))
    print(ms.tree)


if __name__ == '__main__':
    main()
