# windodge.py
pip mode for windows where the window dodges the mouse so you can interact with elements under it (poor man's dual display)

# usage
```
uv run https://raw.githubusercontent.com/santarl/windodge.py/refs/heads/main/windodge.py
```
or clone, run_windodgepy.bat.

you can also use the shortcut to run it with a minimized console window or use the hotkey ctrl+alt+d after copying the shortcut to desktop
or search for windodgepy in start menu and pin to start/taskbar

# screenshots
study session:

https://github.com/user-attachments/assets/86947385-877e-4f39-b6df-a2d3f041cd2a

with two windows:

https://github.com/user-attachments/assets/5037a45d-7ca5-421d-b00a-78e6240f1b58

# flags

```
> uv run https://raw.githubusercontent.com/santarl/windodge.py/refs/heads/main/windodge.py --help
usage: windodgePywrHM.py [-h] [--size SIZE] [--fps FPS] [--gap GAP] [--positions POSITIONS] [--no-resize] [--num-windows {1,2,3,4}]
                         [--pause-threshold PAUSE_THRESHOLD]

A script that makes selected Windows dodge your mouse with smooth animation. Supports up to 4 windows, preventing overlap. Pauses if a window is maximized or too large.

options:
  -h, --help            show this help message and exit
  --size SIZE           Window size as a fraction of screen width/height (e.g., 0.25 for 25%).
                        Aspect ratio of the original window will be preserved.
                        This parameter is ignored if --no-resize is used.
                        Default: 0.25
  --fps FPS             Animation frames per second (higher = smoother, more CPU).
                        Default: 60
  --gap GAP             Pixel gap between window and screen borders.
                        Default: 50
  --positions POSITIONS
                        Which corners the window can move to. Specify as a string of numbers 1-4 (no spaces).
                           1: Top-Right (Math Q1)
                           2: Top-Left (Math Q2)
                           3: Bottom-Left (Math Q3)
                           4: Bottom-Right (Math Q4)
                        Example: '12' for Top-Left and Top-Right only.
                        Default: '1234' (all corners)
  --no-resize, -N       Do not resize the selected window; only move it. Ignores --size parameter.
  --num-windows, -n {1,2,3,4}
                        Number of windows to control (1-4). You will click each window to select it.
                        Default: 1
  --pause-threshold PAUSE_THRESHOLD
                        Percentage of screen area (0.0 to 1.0) a window can cover before pausing dodging.
                        Also pauses if window is maximized. Default: 0.9
```
