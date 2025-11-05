# Maya Stepper Mask

**Maya Stepper Mask** is a Python toolkit for Autodesk Maya 2023 +. 
It helps previewing animation by utilizing modified time.
The result is that playback appears to be "stepped" by 2 or 4s.

## Features

- **Custom Stepper UI:** Easily set and manage step options with persistent selection states.  
- **Scene Filtering:** Automatically detect and handle NURBS curves and constraint nodes.  
- **Global & Local Modes:** Toggle between selection-based and global step control.  

## Requirements
- Autodesk Maya 2023 or newer  
- Python 3.9+  

## Installation

The stepper.py is working when called from Maya main menu  custom menu implementation.
It assumes it is called from Maya Main submenu, not otherwise.

To refactor, change the menu UI commands like in this example:
before:
step.set_stepper_mask(step='1s')
after:
set_stepper_mask(step='1s')
