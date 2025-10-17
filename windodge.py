# Name: windodge.py
# Version: 0.6
# Author: Santarl
# Email: rfsjay@gmail.com
# Date: October 17, 2025

import ctypes
import time
import sys
import math
import argparse
from ctypes import wintypes
from ctypes import CFUNCTYPE

# Make the process DPI-aware so DWM coordinates are consistent
try:
    # PROCESS_PER_MONITOR_DPI_AWARE (1) for Windows 8.1+
    # This ensures that coordinates from DWM APIs are consistent with physical pixels.
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except AttributeError:
    # Fallback for older Windows (Vista-8)
    ctypes.windll.user32.SetProcessDPIAware()

# --- Windows API Definitions ---
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
dwmapi = ctypes.windll.dwmapi # For visual bounds (DWM)

# Structures
class RECT(wintypes.RECT):
    def width(self):
        return self.right - self.left

    def height(self):
        return self.bottom - self.top

class POINT(wintypes.POINT):
    pass

class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", POINT)
    ]

# Function prototypes
user32.GetWindowRect.restype = wintypes.BOOL
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]

user32.SetWindowPos.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]

user32.GetCursorPos.restype = wintypes.BOOL
user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]

user32.GetSystemMetrics.restype = ctypes.c_int # Now used for full screen dimensions
user32.GetSystemMetrics.argtypes = [ctypes.c_int]

user32.WindowFromPoint.restype = wintypes.HWND
user32.WindowFromPoint.argtypes = [POINT]

user32.IsWindowVisible.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]

user32.GetAncestor.restype = wintypes.HWND
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]

user32.IsWindow.restype = wintypes.BOOL
user32.IsWindow.argtypes = [wintypes.HWND]

user32.IsZoomed.restype = wintypes.BOOL
user32.IsZoomed.argtypes = [wintypes.HWND]

user32.ShowWindow.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]

# DWM API for extended frame bounds (visual rect)
DWMWA_EXTENDED_FRAME_BOUNDS = 9
dwmapi.DwmGetWindowAttribute.restype = ctypes.c_long # HRESULT
dwmapi.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.POINTER(RECT), wintypes.DWORD]


# Window Text/Class functions
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.restype = ctypes.c_int
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]

# Hook functions
user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, CFUNCTYPE(ctypes.c_int, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM), wintypes.HINSTANCE, wintypes.DWORD]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.CallNextHookEx.restype = wintypes.LPARAM
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.GetMessageW.restype = wintypes.BOOL
user32.GetMessageW.argtypes = [ctypes.POINTER(MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.TranslateMessage.restype = wintypes.BOOL
user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
user32.DispatchMessageW.restype = wintypes.LPARAM
user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
user32.PostQuitMessage.restype = None
user32.PostQuitMessage.argtypes = [ctypes.c_int]

kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetConsoleWindow.restype = wintypes.HWND
kernel32.GetConsoleWindow.argtypes = []

# Constants
HWND_TOPMOST = wintypes.HWND(-1)
HWND_NOTOPMOST = wintypes.HWND(-2)
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_SHOWWINDOW = 0x0040
SWP_NOACTIVATE = 0x0010
SWP_ASYNCWINDOWPOS = 0x4000

SM_CXSCREEN = 0
SM_CYSCREEN = 1

WH_MOUSE_LL = 14
WM_LBUTTONDOWN = 0x0201
HC_ACTION = 0
GA_ROOT = 2

SW_MINIMIZE = 6

# --- GLOBAL CONFIGURATION VARIABLES (will be set by argparse) ---
WINDOW_SCREEN_FRACTION = 0.25
CORNER_GAP_PIXELS = 50
ANIMATION_DURATION_SECONDS = 0.25
ANIMATION_FPS = 60
VALID_INTERNAL_CORNERS = []
NO_RESIZE = False
NUM_WINDOWS_TO_CONTROL = 1
SCREEN_COVERAGE_THRESHOLD = 0.90

# Map mathematical quadrants (user input) to internal corner indices (Windows API)
# Internal Corner Indices: 0=Top-Left, 1=Top-Right, 2=Bottom-Right, 3=Bottom-Left
MATH_QUAD_TO_INTERNAL_CORNER = {
    '1': 1, # Top-Right (Math Q1)
    '2': 0, # Top-Left (Math Q2)
    '3': 3, # Bottom-Left (Math Q3)
    '4': 2  # Bottom-Right (Math Q4)
}
INTERNAL_CORNER_TO_MATH_QUAD_NAME = {
    0: "Top-Left (Q2)",
    1: "Top-Right (Q1)",
    2: "Bottom-Right (Q4)",
    3: "Bottom-Left (Q3)"
}

# Global variables for hook management
g_hook_id = None
g_selected_hwnds = []

# Global flag for DWM availability - will be checked once at startup
G_DWM_AVAILABLE = True 

# --- Mouse Hook Callback ---
@CFUNCTYPE(ctypes.c_int, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
def mouse_hook_proc(nCode, wParam, lParam):
    global g_selected_hwnds, g_hook_id, NUM_WINDOWS_TO_CONTROL
    if nCode == HC_ACTION and wParam == WM_LBUTTONDOWN:
        mouse_pos = POINT()
        user32.GetCursorPos(ctypes.byref(mouse_pos))
        hwnd_at_cursor = user32.WindowFromPoint(mouse_pos)
        top_level_hwnd = user32.GetAncestor(hwnd_at_cursor, GA_ROOT)

        if top_level_hwnd and user32.IsWindowVisible(top_level_hwnd):
            console_hwnd = kernel32.GetConsoleWindow()
            if top_level_hwnd != console_hwnd and top_level_hwnd not in g_selected_hwnds:
                g_selected_hwnds.append(top_level_hwnd)
                print(f"Selected window {len(g_selected_hwnds)}/{NUM_WINDOWS_TO_CONTROL}: {top_level_hwnd}")
                if len(g_selected_hwnds) == NUM_WINDOWS_TO_CONTROL:
                    user32.PostQuitMessage(0)
                return 1
            elif top_level_hwnd == console_hwnd:
                print("Clicked on console. Please click another window.")
            elif top_level_hwnd in g_selected_hwnds:
                print("This window is already selected. Please choose a different one.")
        else:
            print("No visible top-level window found at cursor position, or clicked on an invalid area.")
    return user32.CallNextHookEx(g_hook_id, nCode, wParam, lParam)

# --- Utility Functions ---
def get_full_screen_dimensions():
    """Returns the (width, height) of the primary monitor's full screen area."""
    return user32.GetSystemMetrics(SM_CXSCREEN), user32.GetSystemMetrics(SM_CYSCREEN)

def get_window_rect(hwnd, retries=5, delay=0.01):
    """
    Returns the bounding box RECT (includes DWM shadows) for a given window handle.
    Includes retries as GetWindowRect can sometimes return 0,0,0,0 initially.
    """
    rect = RECT()
    for _ in range(retries):
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)) and (rect.width() > 0 and rect.height() > 0):
            return rect
        time.sleep(delay)
    return None

def get_window_visual_rect(hwnd, retries=5, delay=0.01):
    """
    Returns the RECT of the visible part of the window (excludes DWM shadows).
    Returns None if DWM call fails or rect is invalid.
    """
    global G_DWM_AVAILABLE
    if not G_DWM_AVAILABLE:
        # If DWM not available or failed initial check, we cannot get true visual rect.
        # For consistency, return bounding rect but expect less precise visual alignment.
        return get_window_rect(hwnd, retries, delay)

    rect = RECT()
    for _ in range(retries):
        hr = dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect))
        if hr == 0 and (rect.width() > 0 and rect.height() > 0): # S_OK and valid rect
            return rect
        time.sleep(delay)
    # If DWM call fails after retries, set global flag and fall back
    G_DWM_AVAILABLE = False
    print(f"Warning: DwmGetWindowAttribute failed for {hwnd} after retries. Falling back to GetWindowRect for visual estimation. Visual positioning might be less precise.")
    return get_window_rect(hwnd, retries=1) # Only one retry for fallback

def get_window_frame_paddings(hwnd):
    """Calculates paddings (left, top, right, bottom) between bounding rect and visual rect."""
    global G_DWM_AVAILABLE
    if not G_DWM_AVAILABLE:
        # If DWM not available, assume no invisible padding for positioning.
        return 0, 0, 0, 0

    win_rect = get_window_rect(hwnd)
    vis_rect = get_window_visual_rect(hwnd, retries=1) # Use 1 retry to avoid excessive delay here
    
    if not win_rect or not vis_rect:
        return 0, 0, 0, 0

    # These are the "sizes" of the invisible borders/shadows
    pad_l = vis_rect.left - win_rect.left
    pad_t = vis_rect.top - win_rect.top
    pad_r = win_rect.right - vis_rect.right
    pad_b = win_rect.bottom - vis_rect.bottom
    return pad_l, pad_t, pad_r, pad_b

def get_window_info(hwnd):
    length = user32.GetWindowTextLengthW(hwnd)
    buff = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buff, length + 1)
    title = buff.value if length > 0 else "N/A"

    c_buff = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, c_buff, 256)
    class_name = c_buff.value if c_buff.value else "N/A"
    return title, class_name

def is_mouse_in_window(hwnd, current_visual_rect):
    """Checks if the mouse cursor is within the VISUAL boundaries of the given window."""
    if not user32.IsWindow(hwnd) or not user32.IsWindowVisible(hwnd): return False
    mouse_pos = POINT()
    if not user32.GetCursorPos(ctypes.byref(mouse_pos)): return False
    
    rect = current_visual_rect # Use the provided visual rect
    if not rect: return False
    return rect.left <= mouse_pos.x < rect.right and rect.top <= mouse_pos.y < rect.bottom

def is_window_too_large(hwnd, screen_w, screen_h, threshold):
    """
    Checks if a window is maximized or covers more than the specified threshold
    percentage of the screen area. Uses visual rect for accurate area check.
    """
    if user32.IsZoomed(hwnd): return True
    
    rect = get_window_visual_rect(hwnd)
    if not rect: return False

    window_area = rect.width() * rect.height()
    screen_area = screen_w * screen_h
    
    if screen_area == 0: return False

    return (window_area / screen_area) > threshold

def get_target_visual_coordinates(corner_index, screen_w, screen_h, vis_w, vis_h, gap):
    """
    Calculates target (x, y) for the VISUAL part of the window,
    relative to the full screen (0,0), applying the specified gap.
    """
    x, y = 0, 0
    
    if corner_index == 0: # Top-Left
        x = gap
        y = gap
    elif corner_index == 1: # Top-Right
        x = screen_w - vis_w - gap
        y = gap
    elif corner_index == 2: # Bottom-Right
        x = screen_w - vis_w - gap
        y = screen_h - vis_h - gap
    elif corner_index == 3: # Bottom-Left
        x = gap
        y = screen_h - vis_h - gap
    else: # Fallback (shouldn't happen)
        x, y = 0, 0

    return x, y

def do_rects_overlap(rect1, rect2, tolerance=0):
    """Checks if two RECT objects overlap, with an optional tolerance."""
    return not (rect1.left >= rect2.right - tolerance or rect1.right <= rect2.left + tolerance or
                rect1.top >= rect2.bottom - tolerance or rect1.bottom <= rect2.top + tolerance)

def is_overlapping_any_other_window(check_visual_rect, all_windows_states, current_window_hwnd, tolerance=0):
    """
    Checks if check_visual_rect overlaps with any other window's current_visual_rect
    in all_windows_states, excluding the current_window_hwnd itself.
    """
    for window_state in all_windows_states:
        if window_state['hwnd'] == current_window_hwnd: continue
        other_rect = window_state.get('current_visual_rect')
        if other_rect and do_rects_overlap(check_visual_rect, other_rect, tolerance):
            return True
    return False

def get_ideal_directional_corner(current_corner_index, mouse_x, mouse_y, visual_rect):
    """
    Determines the *ideal* target corner based on mouse position relative to window's visual center.
    This does NOT check for overlaps or validity; it's purely directional.
    """
    vx, vy = visual_rect.left, visual_rect.top
    vw, vh = visual_rect.width(), visual_rect.height()
    mid_x = vx + vw / 2
    mid_y = vy + vh / 2

    mouse_right = mouse_x > mid_x
    mouse_bottom = mouse_y > mid_y
    
    cci = current_corner_index
    itc = cci # Default

    if cci == 0: # TL (Q2)
        if mouse_right and mouse_bottom: itc = 3 if abs(mouse_x-mid_x) > abs(mouse_y-mid_y) else 1
        elif mouse_right: itc = 3 # Dodge horizontally to BL
        elif mouse_bottom: itc = 1 # Dodge vertically to TR
        else: itc = 2 # Diagonal repel to BR
    elif cci == 1: # TR (Q1)
        if not mouse_right and mouse_bottom: itc = 2 if abs(mouse_x-mid_x) > abs(mouse_y-mid_y) else 0
        elif not mouse_right: itc = 2 # Dodge horizontally to BR
        elif mouse_bottom: itc = 0 # Dodge vertically to TL
        else: itc = 3 # Diagonal repel to BL
    elif cci == 2: # BR (Q4)
        if not mouse_right and not mouse_bottom: itc = 1 if abs(mouse_x-mid_x) > abs(mouse_y-mid_y) else 3
        elif not mouse_right: itc = 1 # Dodge horizontally to TR
        elif not mouse_bottom: itc = 3 # Dodge vertically to BL
        else: itc = 0 # Diagonal repel to TL
    elif cci == 3: # BL (Q3)
        if mouse_right and not mouse_bottom: itc = 0 if abs(mouse_x-mid_x) > abs(mouse_y-mid_y) else 2
        elif mouse_right: itc = 0 # Dodge horizontally to TL
        elif not mouse_bottom: itc = 2 # Dodge vertically to BR
        else: itc = 1 # Diagonal repel to TR
            
    return itc

def get_safe_target_corner(current_corner_index, ideal_corner_index, all_windows_states, current_window_hwnd, screen_w, screen_h, vis_w, vis_h, gap):
    """
    Finds a safe (non-overlapping and allowed) target corner, prioritizing ideal_corner_index.
    If ideal is not safe/allowed, it cycles through other allowed corners.
    """
    
    # Try the ideal corner first if it's allowed
    if ideal_corner_index in VALID_INTERNAL_CORNERS:
        potential_x, potential_y = get_target_visual_coordinates(ideal_corner_index, screen_w, screen_h, vis_w, vis_h, gap)
        potential_rect = RECT(potential_x, potential_y, potential_x + vis_w, potential_y + vis_h)
        if not is_overlapping_any_other_window(potential_rect, all_windows_states, current_window_hwnd):
            return ideal_corner_index # Ideal corner is safe and allowed!

    # If ideal corner failed, try other allowed corners in a cyclic fashion starting from current
    
    try: start_idx = VALID_INTERNAL_CORNERS.index(current_corner_index)
    except ValueError: start_idx = 0 
        
    ordered_corners_to_try = []
    for i in range(len(VALID_INTERNAL_CORNERS)):
        idx = (start_idx + i) % len(VALID_INTERNAL_CORNERS)
        ordered_corners_to_try.append(VALID_INTERNAL_CORNERS[idx])
        
    for corner_to_try in ordered_corners_to_try:
        # If there's only one valid corner and it was already tried (and failed), we just return it.
        # Otherwise, skip if it's the current corner and we have other options.
        if corner_to_try == current_corner_index and len(VALID_INTERNAL_CORNERS) > 1:
            continue

        potential_x, potential_y = get_target_visual_coordinates(corner_to_try, screen_w, screen_h, vis_w, vis_h, gap)
        potential_rect = RECT(potential_x, potential_y, potential_x + vis_w, potential_y + vis_h)
        if not is_overlapping_any_other_window(potential_rect, all_windows_states, current_window_hwnd):
            return corner_to_try # Found a safe and allowed corner

    # If no safe and allowed corner is found, return the current corner (stay put)
    return current_corner_index

def ease_out_quad(t): return t * (2 - t)

def move_window(hwnd, target_vis_x, target_vis_y, target_vis_w, target_vis_h, frame_paddings, animate=False, always_on_top=False):
    """
    Moves/resizes the window.
    `target_vis_x, target_vis_y, target_vis_w, target_vis_h` are for the VISUAL rectangle.
    `frame_paddings` are used to convert these to bounding box coordinates for SetWindowPos.
    """
    pad_l, pad_t, pad_r, pad_b = frame_paddings
    
    # Calculate desired bounding box coordinates for SetWindowPos
    target_bounds_x = target_vis_x - pad_l
    target_bounds_y = target_vis_y - pad_t
    target_bounds_w = target_vis_w + pad_l + pad_r
    target_bounds_h = target_vis_h + pad_t + pad_b

    flags = SWP_SHOWWINDOW | SWP_NOACTIVATE
    insert = HWND_TOPMOST if always_on_top else 0 # Z-order only on final set if animating

    if not animate:
        user32.SetWindowPos(hwnd, insert, int(target_bounds_x), int(target_bounds_y), int(target_bounds_w), int(target_bounds_h), flags)
    else:
        # Animation requires current bounding box position
        current_bounds_rect = get_window_rect(hwnd)
        if not current_bounds_rect: # Cannot animate if current bounds are unknown
            user32.SetWindowPos(hwnd, insert, int(target_bounds_x), int(target_bounds_y), int(target_bounds_w), int(target_bounds_h), flags)
            return
            
        start_bounds_x, start_bounds_y = current_bounds_rect.left, current_bounds_rect.top
        
        total_frames = int(ANIMATION_DURATION_SECONDS * ANIMATION_FPS)
        if total_frames <= 0: # If duration is too short, just instant move
            user32.SetWindowPos(hwnd, insert, int(target_bounds_x), int(target_bounds_y), int(target_bounds_w), int(target_bounds_h), flags)
            return

        frame_interval = 1.0 / ANIMATION_FPS
        start_time = time.perf_counter()

        # During animation, we maintain Z-order to prevent flickering
        animation_flags = SWP_NOACTIVATE | SWP_NOZORDER | SWP_NOSIZE
        
        for frame in range(1, total_frames + 1):
            elapsed = time.perf_counter() - start_time
            progress = ease_out_quad(min(elapsed / ANIMATION_DURATION_SECONDS, 1.0))
            
            cur_bx = start_bounds_x + (target_bounds_x - start_bounds_x) * progress
            cur_by = start_bounds_y + (target_bounds_y - start_bounds_y) * progress
            
            user32.SetWindowPos(hwnd, 0, int(cur_bx), int(cur_by), 0, 0, animation_flags) # 0,0 for size means SWP_NOSIZE is used
            
            tgt_time = start_time + frame * frame_interval
            sleep_time = tgt_time - time.perf_counter()
            if sleep_time > 0: time.sleep(sleep_time)
            if progress >= 1.0: break
            
        # Final set to ensure exact position and size, applying desired Z-order
        user32.SetWindowPos(hwnd, insert, int(target_bounds_x), int(target_bounds_y), int(target_bounds_w), int(target_bounds_h), flags)


# --- Main ---
def main():
    global WINDOW_SCREEN_FRACTION, CORNER_GAP_PIXELS, ANIMATION_FPS, VALID_INTERNAL_CORNERS, NO_RESIZE, NUM_WINDOWS_TO_CONTROL, SCREEN_COVERAGE_THRESHOLD
    global g_hook_id, g_selected_hwnds, G_DWM_AVAILABLE

    parser = argparse.ArgumentParser(
        description="windodge.py: Makes selected Windows dodge your mouse with smooth animation. Supports up to 4 windows, preventing overlap. Pauses if a window is maximized or too large. Allows windows to overlap taskbar.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        '--size',
        type=float,
        default=WINDOW_SCREEN_FRACTION,
        help=(
            f"Window size as a fraction of screen width/height (e.g., 0.25 for 25%%).\n"
            f"Aspect ratio of the original window will be preserved.\n"
            f"This parameter is ignored if --no-resize is used.\n"
            f"Default: {WINDOW_SCREEN_FRACTION}"
        )
    )
    parser.add_argument(
        '--fps',
        type=int,
        default=ANIMATION_FPS,
        help=f"Animation frames per second (higher = smoother, more CPU).\nDefault: {ANIMATION_FPS}"
    )
    parser.add_argument(
        '--gap',
        type=int,
        default=CORNER_GAP_PIXELS,
        help=f"Pixel gap between window and screen borders.\nDefault: {CORNER_GAP_PIXELS}"
    )
    parser.add_argument(
        '--positions',
        type=str,
        default="1234",
        help=(
            "Which corners the window can move to. Specify as a string of numbers 1-4 (no spaces).\n"
            "   1: Top-Right (Math Q1)\n"
            "   2: Top-Left (Math Q2)\n"
            "   3: Bottom-Left (Math Q3)\n"
            "   4: Bottom-Right (Math Q4)\n"
            "Example: '12' for Top-Left and Top-Right only.\n"
            "Default: '1234' (all corners)"
        )
    )
    parser.add_argument(
        '--no-resize', '-N',
        action='store_true',
        help="Do not resize the selected window; only move it. Ignores --size parameter."
    )
    parser.add_argument(
        '--num-windows', '-n',
        type=int,
        default=NUM_WINDOWS_TO_CONTROL,
        choices=range(1, 5), # Limit to 1 to 4 windows
        help=f"Number of windows to control (1-4). You will click each window to select it.\nDefault: {NUM_WINDOWS_TO_CONTROL}"
    )
    parser.add_argument(
        '--pause-threshold',
        type=float,
        default=SCREEN_COVERAGE_THRESHOLD,
        help=(
            f"Percentage of screen area (0.0 to 1.0) a window can cover before pausing dodging.\n"
            f"Also pauses if window is maximized. Default: {SCREEN_COVERAGE_THRESHOLD}"
        )
    )

    args = parser.parse_args()

    # Apply arguments to global configuration
    WINDOW_SCREEN_FRACTION = args.size
    ANIMATION_FPS = args.fps
    CORNER_GAP_PIXELS = args.gap
    NO_RESIZE = args.no_resize
    NUM_WINDOWS_TO_CONTROL = args.num_windows
    SCREEN_COVERAGE_THRESHOLD = args.pause_threshold

    # Initial check for DWM functionality
    try:
        test_rect = RECT()
        # Use a dummy window handle (0) for a basic DWM check
        hr = dwmapi.DwmGetWindowAttribute(0, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(test_rect), ctypes.sizeof(test_rect))
        if hr != 0: # If it fails for a dummy window, assume DWM not fully available
            G_DWM_AVAILABLE = False
            print("Warning: DWM API for extended frame bounds not fully available or failed to query. Window positioning might be less precise.")
    except Exception:
        G_DWM_AVAILABLE = False
        print("Warning: dwmapi.DwmGetWindowAttribute call failed. Window positioning might be less precise.")


    # Validate and set VALID_INTERNAL_CORNERS
    valid_math_quads = [str(i) for i in range(1, 5)]
    parsed_positions = []
    for char in args.positions:
        if char not in valid_math_quads:
            print(f"Error: Invalid position '{char}' in --positions. Must be 1, 2, 3, or 4.")
            sys.exit(1)
        parsed_positions.append(MATH_QUAD_TO_INTERNAL_CORNER[char])
    
    VALID_INTERNAL_CORNERS = sorted(list(set(parsed_positions))) # Remove duplicates and sort for consistent cycling
    if not VALID_INTERNAL_CORNERS:
        print("Error: No valid positions specified for the window. Exiting.")
        sys.exit(1)
    
    if NUM_WINDOWS_TO_CONTROL > len(VALID_INTERNAL_CORNERS):
        print(f"Warning: You requested {NUM_WINDOWS_TO_CONTROL} windows but only {len(VALID_INTERNAL_CORNERS)} unique positions are allowed (--positions).")
        print("This may lead to windows not being able to find a unique, non-overlapping spot.")


    print(f"--- {__file__} ---") # Prints the script's filename
    print(f"Config: Number of windows: {NUM_WINDOWS_TO_CONTROL}")
    print(f"Config: Size {WINDOW_SCREEN_FRACTION*100:.0f}%, Gap {CORNER_GAP_PIXELS}px")
    print(f"Animation: {ANIMATION_DURATION_SECONDS}s duration at {ANIMATION_FPS} FPS")
    if NO_RESIZE:
        print("Window resizing is DISABLED (--no-resize flag active).")
    print(f"Dodging PAUSED if any window is maximized or covers >{SCREEN_COVERAGE_THRESHOLD*100:.0f}% of screen.")
    
    active_corners_names = [INTERNAL_CORNER_TO_MATH_QUAD_NAME[idx] for idx in VALID_INTERNAL_CORNERS]
    print(f"Active Corners: {', '.join(active_corners_names)}")

    print(f"\nIMPORTANT: LEFT-CLICK on {NUM_WINDOWS_TO_CONTROL} unique windows to control (not this console).")

    h_instance = kernel32.GetModuleHandleW(None)
    g_hook_id = user32.SetWindowsHookExW(WH_MOUSE_LL, mouse_hook_proc, h_instance, 0)
    if not g_hook_id:
        return print("Failed to install mouse hook. Ensure you have sufficient permissions (e.g., run as administrator). Exiting.")

    msg = MSG()
    while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) > 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))

    if g_hook_id: user32.UnhookWindowsHookEx(g_hook_id)

    if len(g_selected_hwnds) < NUM_WINDOWS_TO_CONTROL:
        return print(f"Only {len(g_selected_hwnds)}/{NUM_WINDOWS_TO_CONTROL} windows selected. Exiting.")

    full_screen_w, full_screen_h = get_full_screen_dimensions()
    print(f"Detected full screen dimensions: {full_screen_w}x{full_screen_h} (Windows may apply display scaling)")

    controlled_windows = [] # List to hold state for each controlled window

    for i, hwnd in enumerate(g_selected_hwnds):
        if not user32.IsWindow(hwnd):
            print(f"Warning: Selected window {i+1} (handle {hwnd}) is no longer valid. Skipping.")
            continue

        window_title, window_class = get_window_info(hwnd)
        print(f"\n--- Initializing Window {i+1} ---")
        print(f"Window handle: {hwnd}")
        print(f"Window title: '{window_title}' (Class: '{window_class}')")

        initial_visual_rect = get_window_visual_rect(hwnd)
        if not initial_visual_rect:
            print(f"Could not get initial visual dimensions for window {i+1}. Skipping.")
            continue
        
        initial_vis_w = initial_visual_rect.width()
        initial_vis_h = initial_visual_rect.height()

        min_size = 100
        if initial_vis_w <= 0 or initial_vis_h <= 0:
            print("Warning: Original window has invalid (zero or negative) visual dimensions. Using default minimum.")
            initial_vis_w = min_size
            initial_vis_h = min_size
            
        final_vis_w, final_vis_h = initial_vis_w, initial_vis_h # Start with original visual size

        if not NO_RESIZE:
            target_w_fraction = int(full_screen_w * WINDOW_SCREEN_FRACTION)
            target_h_fraction = int(full_screen_h * WINDOW_SCREEN_FRACTION)

            # Preserve aspect ratio
            aspect_ratio = initial_vis_w / initial_vis_h if initial_vis_h > 0 else 1.0
            
            # Scale to fit within target_w_fraction and target_h_fraction while maintaining aspect ratio
            scale_by_width = target_w_fraction / initial_vis_w if initial_vis_w > 0 else 1.0
            scale_by_height = target_h_fraction / initial_vis_h if initial_vis_h > 0 else 1.0
            actual_scale_factor = min(scale_by_width, scale_by_height)
            
            final_vis_w = int(initial_vis_w * actual_scale_factor)
            final_vis_h = int(initial_vis_h * actual_scale_factor)

            final_vis_w = max(final_vis_w, min_size)
            final_vis_h = max(final_vis_h, min_size)
        
        # Calculate maximum allowed dimensions for the visual window to fit with gaps within the full screen
        max_allowed_vis_w = full_screen_w - 2 * CORNER_GAP_PIXELS
        max_allowed_vis_h = full_screen_h - 2 * CORNER_GAP_PIXELS

        if final_vis_w > max_allowed_vis_w or final_vis_h > max_allowed_vis_h:
            print(f"Warning: Window visual size with current gap ({CORNER_GAP_PIXELS}px) exceeds full screen boundaries ({max_allowed_vis_w}x{max_allowed_vis_h}). Scaling down to fit.")
            
            # Recalculate aspect ratio from potentially scaled size to be safe
            # current_aspect_ratio_calc = final_vis_w / final_vis_h if final_vis_h > 0 else 1.0 # Not used for scaling
            
            scale_factor_w = max_allowed_vis_w / final_vis_w if final_vis_w > 0 else 1.0
            scale_factor_h = max_allowed_vis_h / final_vis_h if final_vis_h > 0 else 1.0
            
            actual_scale_factor_to_fit_gap = min(scale_factor_w, scale_factor_h)
            
            final_vis_w = int(final_vis_w * actual_scale_factor_to_fit_gap)
            final_vis_h = int(final_vis_h * actual_scale_factor_to_fit_gap)
            
            final_vis_w = max(final_vis_w, min_size)
            final_vis_h = max(final_vis_h, min_size)

        if final_vis_w <= 0 or final_vis_h <= 0:
            print("Calculated final visual window dimensions are invalid. Skipping this window.")
            continue

        print(f"Final visual window dimensions: {final_vis_w}x{final_vis_h} with a {CORNER_GAP_PIXELS}px gap.")

        # Get frame paddings (offsets between bounding box and visual content)
        # These are crucial for accurate positioning with SetWindowPos
        frame_paddings = get_window_frame_paddings(hwnd)

        # Assign initial unique corner to each window
        initial_corner_index = VALID_INTERNAL_CORNERS[i % len(VALID_INTERNAL_CORNERS)]
        target_vis_x, target_vis_y = get_target_visual_coordinates(initial_corner_index, full_screen_w, full_screen_h, final_vis_w, final_vis_h, CORNER_GAP_PIXELS)
        
        # Check for overlap with already placed windows for initial placement
        potential_initial_visual_rect = RECT(target_vis_x, target_vis_y, target_vis_x + final_vis_w, target_vis_y + final_vis_h)
        if is_overlapping_any_other_window(potential_initial_visual_rect, controlled_windows, hwnd):
            print(f"Initial corner {INTERNAL_CORNER_TO_MATH_QUAD_NAME[initial_corner_index]} overlaps with another window. Finding new initial spot...")
            found_initial_spot = False
            
            for try_offset in range(len(VALID_INTERNAL_CORNERS)):
                candidate_corner = VALID_INTERNAL_CORNERS[(i + try_offset) % len(VALID_INTERNAL_CORNERS)]
                candidate_vis_x, candidate_vis_y = get_target_visual_coordinates(candidate_corner, full_screen_w, full_screen_h, final_vis_w, final_vis_h, CORNER_GAP_PIXELS)
                candidate_visual_rect = RECT(candidate_vis_x, candidate_vis_y, candidate_vis_x + final_vis_w, candidate_vis_y + final_vis_h)
                if not is_overlapping_any_other_window(candidate_visual_rect, controlled_windows, hwnd):
                    initial_corner_index = candidate_corner
                    target_vis_x, target_vis_y = candidate_vis_x, candidate_vis_y
                    found_initial_spot = True
                    break
            if not found_initial_spot:
                print(f"Could not find a unique initial non-overlapping spot for window {i+1}. Skipping this window.")
                continue

        # Perform initial move and resize using calculated visual coordinates and frame paddings
        move_window(hwnd, target_vis_x, target_vis_y, final_vis_w, final_vis_h, frame_paddings, animate=False, always_on_top=True)
        
        current_visual_rect_after_move = get_window_visual_rect(hwnd) # Get actual visual rect after move
        
        if not current_visual_rect_after_move:
             print(f"Failed to get visual rect after initial move for window {i+1}. Skipping.")
             continue

        controlled_windows.append({
            'hwnd': hwnd,
            'corner': initial_corner_index,
            'current_visual_rect': current_visual_rect_after_move,
            'vis_w': final_vis_w,
            'vis_h': final_vis_h,
            'frame_paddings': frame_paddings # Store paddings for future moves
        })
        print(f"Window {i+1} initialized at {INTERNAL_CORNER_TO_MATH_QUAD_NAME[initial_corner_index]} and set to always on top.")

    if not controlled_windows:
        return print("No valid windows to control. Exiting.")

    # Minimize console window if controlling multiple or if not in --no-resize (where it might be in the way)
    # The console window will also be DPI aware now.
    if NUM_WINDOWS_TO_CONTROL > 1 or not NO_RESIZE:
        console_hwnd = kernel32.GetConsoleWindow()
        if console_hwnd:
            user32.ShowWindow(console_hwnd, SW_MINIMIZE)

    try:
        paused_state = False
        while True:
            # Remove any controlled windows that have been closed
            controlled_windows[:] = [win for win in controlled_windows if user32.IsWindow(win['hwnd'])]
            if not controlled_windows:
                print("All controlled windows have been closed. Exiting.")
                break

            # Check if any window is in a "too large" state
            any_window_large = False
            for window_state in controlled_windows:
                hwnd = window_state['hwnd']
                # Always re-affirm always-on-top for all windows, even if paused
                user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_ASYNCWINDOWPOS)

                if is_window_too_large(hwnd, full_screen_w, full_screen_h, SCREEN_COVERAGE_THRESHOLD):
                    any_window_large = True
            
            if any_window_large:
                if not paused_state:
                    print("\n--- Script Paused: A controlled window is maximized or covers >90% of screen. ---")
                    paused_state = True
                time.sleep(0.5) # Longer sleep during pause when paused
                continue # Skip dodging logic
            
            # If not paused, or just resumed
            if paused_state:
                print("--- Script Resumed: All controlled windows are now within normal bounds. ---")
                paused_state = False

            # --- Normal Dodging Logic (only executed if not paused) ---
            for window_state in controlled_windows:
                hwnd = window_state['hwnd']
                mouse_pos = POINT()
                user32.GetCursorPos(ctypes.byref(mouse_pos))

                current_visual_rect = get_window_visual_rect(hwnd)
                if not current_visual_rect:
                    print(f"Could not get visual rectangle for {hwnd}, assuming it's closing.")
                    continue 

                window_state['current_visual_rect'] = current_visual_rect # Update rect in state

                if is_mouse_in_window(hwnd, current_visual_rect):
                    # print(f"Mouse entered window {hwnd}! Dodging directionally...")
                    
                    ideal_corner_index = get_ideal_directional_corner(window_state['corner'], mouse_pos.x, mouse_pos.y, current_visual_rect)
                    
                    # Find a safe target corner (non-overlapping and allowed)
                    target_corner_index = get_safe_target_corner(
                        window_state['corner'],
                        ideal_corner_index,
                        controlled_windows,
                        hwnd,
                        full_screen_w, full_screen_h,
                        window_state['vis_w'],
                        window_state['vis_h'],
                        CORNER_GAP_PIXELS
                    )
                    
                    if target_corner_index != window_state['corner']:
                        print(f"Window {hwnd} moving from {INTERNAL_CORNER_TO_MATH_QUAD_NAME[window_state['corner']]} to {INTERNAL_CORNER_TO_MATH_QUAD_NAME[target_corner_index]}.")
                        window_state['corner'] = target_corner_index

                        target_vis_x, target_vis_y = get_target_visual_coordinates(target_corner_index, full_screen_w, full_screen_h, window_state['vis_w'], window_state['vis_h'], CORNER_GAP_PIXELS)
                        
                        move_window(hwnd, target_vis_x, target_vis_y, window_state['vis_w'], window_state['vis_h'], window_state['frame_paddings'], animate=True, always_on_top=True)
                        
                        # Update the window's visual rect after smooth move
                        window_state['current_visual_rect'] = get_window_visual_rect(hwnd) 
                        time.sleep(0.2) # Cooldown after dodge to prevent rapid re-trigger
            time.sleep(0.02) # Check frequently for responsiveness
    except KeyboardInterrupt:
        print("\nScript terminated by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        for window_state in controlled_windows:
            if user32.IsWindow(window_state['hwnd']):
                user32.SetWindowPos(window_state['hwnd'], HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)
                print(f"Always on top status removed from window {window_state['hwnd']}.")

if __name__ == "__main__":
    main()