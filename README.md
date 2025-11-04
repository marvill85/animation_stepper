# Maya Stepper Mask

**Maya Stepper Mask** is a Python toolkit for Autodesk Maya that simplifies frame stepping management and scene control. It provides a customizable UI, utility functions, and smart filtering for NURBS and constraint nodes, helping artists and technical directors streamline fps workflows in Maya.

## Features

- **Custom Stepper UI:** Easily set and manage step options with persistent selection states.  
- **Scene Filtering:** Automatically detect and handle NURBS curves and constraint nodes.  
- **Global & Local Modes:** Toggle between selection-based and global step control.  
- **Utility Functions:** Modular `fps_utils` (or `stepper_utils`) for reusable operations across scripts.
- 
## Requirements

- Autodesk Maya 2023 or newer  
- Python 3.0+  

## Installation

It is working in custom menu implementation.
It assumes it is called from Maya Main submenu, not otherwise.

To refactor, change the menu UI commands like in this example:
before:
step.set_stepper_mask(step='1s')
after:
set_stepper_mask(step='1s')
