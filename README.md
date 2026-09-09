# Houdini ROP Manager / Light Manager

Python tools for SideFX Houdini focused on lighting and render output workflows.

This repository currently contains:
- A Light Manager UI for Arnold/Houdini lighting workflows
- A ROP Manager UI for creating, browsing, and editing render output nodes (Arnold, Mantra, Karma)

  <img width="702" height="683" alt="UI" src="https://github.com/user-attachments/assets/c0c0f87c-0298-4b5d-bd6f-4a9b8f54d64f" />
  
  <img width="982" height="593" alt="ROP UI" src="https://github.com/user-attachments/assets/faab7dcf-e0ee-42b1-8541-a66014544f6e" />

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

```python
exec(open(r"YOUR\FOLDER\PATH\HERE\light_manager_houdini.py").read())
```

Or import modules directly:

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
- `light_manager_houdini.py` currently includes a hardcoded `ROP_MANAGER_PATH` variable. In order to be able to run ROP MANAGER from Light manager window, it is NEEDED to edit the `ROP_MANAGER_PATH` with YOUR CUSTOM PATH to `rop_manager.py` file.

  <img width="506" height="93" alt="path_example" src="https://github.com/user-attachments/assets/73aca199-500e-48fa-9f0b-11863a54a267" />


## Author

Miguel Agenjo
- www.miguelagenjo.com
