# Houdini ROP Manager / Light Manager

Python tools for SideFX Houdini focused on lighting and render output workflows.

This repository currently contains:
- A Light Manager UI for Arnold/Houdini lighting workflows
- A ROP Manager UI for creating, browsing, and editing render output nodes (Arnold, Mantra, Karma)

## Requirements

- Houdini 20
- Python environment with Houdini's `hou` module available (run from inside Houdini)
- Qt bindings:
  - `PySide6` preferred
  - `PySide2` fallback

## Project Structure

- `rop_manager.py`
  - ROP Manager tool script with `create_rop_manager_window()` entry point.
- `light_manager_houdini.py`
  - Light Manager tool script with `create_light_manager_window()` entry point.

## Quick Start (Houdini Shelf Tool)

Run from a Houdini shelf script or Python Source Editor.

### Launch Light Manager

```python
import light_manager_houdini
light_manager_houdini.create_light_manager_window()
```

### Launch ROP Manager

```python
import rop_manager
rop_manager.create_rop_manager_window()
```

## Notes

- These tools are intended to run inside Houdini, not from a standalone system Python.
- The scripts keep a global window instance to avoid opening duplicate UI windows.
- `light_manager_houdini.py` currently includes a hardcoded `ROP_MANAGER_PATH` constant.

## Author

Miguel Agenjo
- www.miguelagenjo.com
