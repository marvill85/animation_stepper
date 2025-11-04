# ============================================================
# Maya FPS [stepper] Mask
# ============================================================
# Description:
#     A custom Maya Python toolkit designed to manage and control
#     frame rate (FPS) settings and related scene behaviors.
#     Includes utilities for UI management, scene filtering,
#     and dynamic control of constraints, NURBS, and playback modes.
#
# Key Features:
#     • Custom UI for FPS configuration and state persistence
#     • Automatic filtering of constraints and NURBS elements
#     • Smart scene selection and global mode handling
#     • Modular utility functions (fps_utils) for reusability
#     • Supports reload and hot-update for active Maya sessions
#
# Author: [marvill]
# Testing: [clojster]
# Version: 1.0
# Maya Version: 2023+
# Python Version: 3.0+
# Last Updated: November 2025
# ============================================================


import maya.cmds as cmds
import sys
sys.path.append("k:/SW_REPO/PLUGIN/IncognitoCustom/maya/2023/Incognito/ROSA_DARA")
import importlib
import stepper as step
importlib.reload(step)

# --- Ensure global persistent variable exists ---
if 'stepper_ui_state' not in globals():
    stepper_ui_state = {"selection_mode": 1}  # 1=Selected, 2=Hierarchy, 3=Global

# --- This is for user interface ---
def get_stepper_selection_mode():
    mode = stepper_ui_state["selection_mode"]
    return (["Selected", "Hierarchy", "Global"][mode - 1])

# Function to get Colorize state
def get_colorize():
    return step.stepper_ui_state.get("colorize", True)

# --- This is to obtain all animation curves related to object ---
def get_all_anim_curves(obj):
    # Recursively collects all animation curves connected to a given object.
    # Traverses through animBlendNode connections until all curves are found.
    visited = set()
    curves = set()

    def _collect_from(node):
        if node in visited:
            return
        visited.add(node)

        # get all incoming connections
        inputs = cmds.listConnections(node, s=True, d=False, plugs=False) or []
        for src in inputs:
            node_type = cmds.nodeType(src)
            if node_type.startswith("animBlendNode"):
                _collect_from(src)
            elif node_type.startswith("animCurve"):
                curves.add(src)

    _collect_from(obj)
    return sorted(curves)

# --- Filter to keep only NURBS curves and constraints ---
def filter_nurbscon(nodes):
    res = []
    for o in set(nodes):
        t = cmds.nodeType(o)
        if t == "transform" and any(cmds.nodeType(s) == "nurbsCurve" for s in cmds.listRelatives(o, s=True, path=True) or []):
            res.append(o)
        elif t.endswith("Constraint"):
            res.append(o)
    return res
    
# --- Filter to keep only objects which have at least one animCurve or animBlend node ---
def filter_animated(nodes):
    return [obj for obj in set(nodes)
            if any('animBlendNode' in cmds.nodeType(c) for c in cmds.listConnections(obj, s=True, d=False) or [])
               or cmds.listConnections(obj, type='animCurve', s=True, d=False)]

# --- Cameras and their parents don't get stepper mask ---
def filter_out_cameras(nodes):
    return [n for n in nodes 
            if not any(cmds.nodeType(x) == 'camera' 
                       for x in [n] + (cmds.listRelatives(n, allDescendents=True, fullPath=True) or []))]

# --- This is to disconnect animCurves and revert shapes from obj ---
def disconnect_anim_and_revert_shapes(candidates):
    filtered_candidates = filter_animated(candidates)
    disconnected_any = False
    for obj in filtered_candidates:
        anim_curves = get_all_anim_curves(obj)
        for curve in anim_curves:
            try:
                connections = cmds.listConnections(f"{curve}.input", s=True, d=False, plugs=True) or []
                for conn in connections:
                    source_node = conn.split('.')[0]
    
                    if cmds.nodeType(source_node) in ['unitConversion', 'unitToTimeConversion']:
                        incoming = cmds.listConnections(f"{source_node}.input", s=True, d=False, plugs=True) or []
                        if not incoming:
                            continue
                        incoming_node = incoming[0].split('.')[0]
                        if "stepper" in incoming_node.lower():
                            cmds.disconnectAttr(conn, f"{curve}.input")
                            try:
                                cmds.delete(source_node)
                            except:
                                cmds.warning(f"Could not delete {source_node}")
                            disconnected_any = True
                    else:
                        if "stepper" in source_node.lower():
                            cmds.disconnectAttr(conn, f"{curve}.input")
               disconnected_any = True
            except Exception as e:
                cmds.warning(f"Failed to process {curve}.input: {e}")
    
        if disconnected_any:
            shapes = cmds.listRelatives(obj, shapes=True, fullPath=True) or []
            for shape in shapes:
                try:
                    cmds.setAttr(f"{shape}.overrideRGBColors", 0)
                except Exception as e:
                    cmds.warning(f"Failed to revert override for {shape}: {e}")
    # remove from set
    sets = cmds.ls(type = "objectSet")
    for set in sets:
        if "anim_on" in set:
            cmds.sets(candidates, remove=set)
    

    print(f"Removed stepper_mask connections and restored shape overrides for {len(filtered_candidates)} of {len(candidates)} object(s)")
 
# --- This rebuilds stepper mask based on objects in special sets
def rebuild_stepper_masks():
    for set, step in {"anim_on_2s":"2s", "anim_on_4s":"4s"}.items():
        if cmds.objExists(set):
            if cmds.objectType(set)=="objectSet":
                candidates = cmds.sets(set, q=True)
                if candidates:
                    print(f"Rebuilding step mask for {len(candidates)} members of '{set}':")
                    set_stepper_mask(nodes=candidates, step=step, rebuild = True)

# --- Main function ---
def set_stepper_mask(nodes=None, step='2s', mode='None', rebuild = False):
    """
    Applies stepper12_mask to nodes objects or filtered hierarchy.
    Only objects with animCurves and animBlendNodes are processed.
    Cameras and their parents are filtered out.
    Parameters:
    - nodes: list of objects to process; defaults to current selection.
    - check_controls_set: if True, filter objects based on namespace + rigMain_controls_SET;
                          if False, use selection and all descendants directly.
    - step: 2s, 4s, 1s - connect to stepper time node by 2 frame step, 4 frame step or disconnect
    - mode: "Selected", "Hierarchy", "Global" - the scope of the action
    """
    
    mode = get_stepper_selection_mode()
    if rebuild: mode = "Selected"

    if not nodes:
        if mode == 'Global':
            cmds.warning("Collecting all scene objects. It may take some time...")
            nodes = cmds.ls(type = 'transform')
        elif mode=='Selected' or mode=='Hierarchy':
            if not nodes: nodes = cmds.ls(sl=True, type = 'transform')
        else:
            cmds.warning(f"No valid mode was selected: '{mode}'. Exiting")
            return    
    if not nodes: 
        cmds.warning("Select at least one object.")
        return

    candidates = []
    hierarchy = []

    # filter_out_cameras
    filtered_nodes = filter_out_cameras(nodes)
    removed = set(nodes) - set(filtered_nodes)
    if removed:
        cmds.warning(f"Camera nodes filtered out: {', '.join(removed)}")

    # filter only nurbs curves and constraints
    filtered_nodes = filter_nurbscon(filtered_nodes)
    
    if mode == "Hierarchy":
        for obj in filtered_nodes:        
            hierarchy = cmds.listRelatives(obj, allDescendents=True, fullPath=True, type = 'transform') or []
            hierarchy.append(obj)
            candidates.extend(hierarchy)
    else:
        candidates = filtered_nodes
        
    # filter out duplicates and constraints ***
    # candidates = list({n for n in candidates if not cmds.nodeType(n).endswith('Constraint')})

    if not candidates:
        cmds.warning("No candidates for animation found in the selection/hierarchy.")
        return

    # Keep only objects which have at least one animCurve or animBlend node
    filtered_candidates = filter_animated(candidates)
    '''
    filtered_candidates = [
        obj for obj in set(candidates)
        if any('animBlendNode' in cmds.nodeType(c) for c in cmds.listConnections(obj, s=True, d=False) or [])
           or cmds.listConnections(obj, type='animCurve', s=True, d=False)
    ]
    '''
    # --- Apply stepper_mask logic ---
    if step == '2s':
        mask_node = "stepper_mask_2s"
        stepper_set = "anim_on_2s"
        step = 2
        color = (1, 0.5, 1)
    elif step == '4s':
        mask_node = "stepper_mask_4s"
        stepper_set = "anim_on_4s"
        step = 4
        color = (0, 0.85, 1)
    elif step == '1s':
        disconnect_anim_and_revert_shapes(candidates)
        return
    else:
        cmds.warning("No valid option for step. Exiting.")
        return
        
    # update maya sets
    if cmds.objExists(stepper_set):
        if (cmds.objectType(stepper_set) == 'objectSet'):
            cmds.sets(candidates, include=stepper_set)
        else:
            cmds.warning(f"Cannot add candidates, `{stepper_set}` already exists and is not a set")
    else:
        cmds.sets(candidates, name = stepper_set)


                
    if not filtered_candidates:
        cmds.warning("No objects with animCurves found in the selection/hierarchy.")
        return
        
    # create / update custom node network 'mask_node'
    if not cmds.objExists(mask_node):
        mask_node = cmds.createNode("blendTwoAttr", name=mask_node)

        if cmds.objExists(f"{mask_node}.attributesBlender"):
            cmds.setAttr(f"{mask_node}.attributesBlender", 1)

        expr_name = "expr_" + mask_node
        if cmds.objExists(expr_name):
            cmds.delete(expr_name)
        cmds.expression(
            s=f"""{mask_node}.input[0] = frame;
{mask_node}.input[1] = floor((frame-1)/{step})*{step} + 1;""",
            n=expr_name
        )

    # Connect animCurves and set shapes
    for obj in filtered_candidates:
        anim_curves = get_all_anim_curves(obj)
        for curve in anim_curves:
            input_connected = cmds.listConnections(f"{curve}.input", s=True, d=False, plugs=True)
            if not input_connected:
                try:
                    cmds.connectAttr(f"{mask_node}.output", f"{curve}.input")
                except Exception as e:
                    cmds.warning(f"Failed to connect {curve}.input: {e}")

        shapes = cmds.listRelatives(obj, shapes=True, fullPath=True) or []
        for shape in shapes:
            try:
                cmds.setAttr(f"{shape}.overrideEnabled", 1)
                if get_colorize():
                    cmds.setAttr(f"{shape}.overrideRGBColors", 1)
                else:
                    cmds.setAttr(f"{shape}.overrideRGBColors", 0)                    
                cmds.setAttr(f"{shape}.overrideColorRGB", *color)   # The * unpacks the tuple
            except Exception as e:
                cmds.warning(f"Failed to set override color for {shape}: {e}")

    print(f"Connected animCurves and set shapes to {str(color)} for {len(filtered_candidates)} object(s)")


# --- User Interface ---
import maya.cmds as cmds
import stepper as step  # assuming your global stepper_ui_state is here

# --- User Interface ---
def stepper_ui():
    if cmds.window("stepper", exists=True):
        cmds.deleteUI("stepper")
    w = cmds.window("stepper", t="stepper", wh=(200, 100))
    cmds.columnLayout(adj=True, cal="center")
    cmds.separator(h=2, st="none")
    cmds.text(l="A N I M   S T E P P E R")
    cmds.separator(h=2, st="none")
    cmds.separator(h=2, style='in')  # horizontal line under the text

    # --- Two-column layout ---
    cmds.rowLayout(nc=2, cw2=(100, 100))

    # LEFT COLUMN – Buttons
    cmds.columnLayout(adj=True)
    colors = {
        "1's": ([0.6, 0.6, 0.6], "import stepper as step ; step.set_stepper_mask(step='1s')"),
        "2's": ([1, 0.85, 0.9], "import stepper as step ; step.set_stepper_mask(step='2s')"),
        "4's": ([0.4, 0.9, 0.8], "import stepper as step ; step.set_stepper_mask(step='4s')"),
    }
    cmds.rowLayout(nc=3, cw3=(30, 30, 30))
    [cmds.button(l=k, w=30, h=22, bgc=v[0], c=v[1]) for k, v in colors.items()]
    cmds.setParent("..")
    cmds.separator(h=4, st="none")

    # Colorize checkbox instead of Toggle Color button
    step.stepper_ui_state["colorize"] = True  # default checked
    step.stepper_ui_state["colorize_checkbox"] = cmds.checkBox(
        l="Colorize",
        value=True,
        cc=lambda val: step.stepper_ui_state.update(colorize=val)  # val is True/False
    )

    cmds.separator(h=2, st="none")
    cmds.button(l="Refresh", bgc=[0.6, 0.6, 0.6], h=20,
                c="import stepper as step ; step.rebuild_stepper_masks()")
    cmds.setParent("..")

    # RIGHT COLUMN – Radios
    cmds.columnLayout(adj=True)
    radio_col = cmds.radioCollection()
    labels = ["Selected", "Hierarchy", "Global"]
    buttons = [cmds.radioButton(l=l, align="left") for l in labels]

    # Restore previous state
    cmds.radioCollection(radio_col, e=True, select=buttons[step.stepper_ui_state["selection_mode"] - 1])

    # Update global variable on change
    for i, b in enumerate(buttons, 1):
        cmds.radioButton(b, e=True, onc=lambda _, m=i: step.stepper_ui_state.update(selection_mode=m))

    cmds.setParent("..")  # back to main column
    cmds.showWindow(w)

stepper_ui()
