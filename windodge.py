# Name: windodge.py
# Version: 0.3
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

# --- Windows API Definitions ---
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

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

user32.GetSystemMetrics.restype = ctypes.c_int
user32.GetSystemMetrics.argtypes = [ctypes.c_int]

user32.WindowFromPoint.restype = wintypes.HWND
user32.WindowFromPoint.argtypes = [POINT]

user32.IsWindowVisible.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]

user32.GetAncestor.restype = wintypes.HWND
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]

user32.IsWindow.restype = wintypes.BOOL
user32.IsWindow.argtypes = [wintypes.HWND]

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

# --- GLOBAL CONFIGURATION VARIABLES (will be set by argparse) ---
WINDOW_SCREEN_FRACTION = 0.25
CORNER_GAP_PIXELS = 50
ANIMATION_DURATION_SECONDS = 0.25
ANIMATION_FPS = 60
VALID_INTERNAL_CORNERS = [] # List of allowed internal corner indices (0, 1, 2, 3)
NO_RESIZE = False
NUM_WINDOWS_TO_CONTROL = 1

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
g_selected_hwnds = [] # List to store selected window handles

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
                    user32.PostQuitMessage(0) # All windows selected, terminate hook message loop
                return 1 # Consume the click event
            elif top_level_hwnd == console_hwnd:
                print("Clicked on console. Please click another window.")
            elif top_level_hwnd in g_selected_hwnds:
                print("This window is already selected. Please choose a different one.")
        else:
            print("No visible top-level window found at cursor position, or clicked on an invalid area.")
    return user32.CallNextHookEx(g_hook_id, nCode, wParam, lParam)

# --- Utility Functions ---
def get_screen_dimensions():
    return user32.GetSystemMetrics(SM_CXSCREEN), user32.GetSystemMetrics(SM_CYSCREEN)

def get_window_rect(hwnd, retries=5, delay=0.01):
    """
    Returns (left, top, right, bottom) for a given window handle.
    Includes retries as GetWindowRect can sometimes return 0,0,0,0 initially.
    """
    rect = RECT()
    for _ in range(retries):
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)) and (rect.width() > 0 and rect.height() > 0):
            return rect
        time.sleep(delay)
    return None # Failed after retries

def get_window_info(hwnd):
    length = user32.GetWindowTextLengthW(hwnd)
    buff = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buff, length + 1)
    title = buff.value if length > 0 else "N/A"

    c_buff = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, c_buff, 256)
    class_name = c_buff.value if c_buff.value else "N/A"
    return title, class_name

def is_mouse_in_window(hwnd):
    if not user32.IsWindow(hwnd) or not user32.IsWindowVisible(hwnd): return False
    mouse_pos = POINT()
    if not user32.GetCursorPos(ctypes.byref(mouse_pos)): return False
    rect = get_window_rect(hwnd)
    if not rect: return False
    return rect.left <= mouse_pos.x < rect.right and rect.top <= mouse_pos.y < rect.bottom

def get_corner_coordinates(corner_index, screen_w, screen_h, win_w, win_h, gap):
    """Calculates target (x, y) for a specific internal corner index."""
    if corner_index == 0: return gap, gap # Top-Left
    elif corner_index == 1: return screen_w - win_w - gap, gap # Top-Right
    elif corner_index == 2: return screen_w - win_w - gap, screen_h - win_h - gap # Bottom-Right
    elif corner_index == 3: return gap, screen_h - win_h - gap # Bottom-Left
    return 0, 0 # Fallback

def do_rects_overlap(rect1, rect2, tolerance=0):
    """Checks if two RECT objects overlap, with an optional tolerance."""
    return not (rect1.left >= rect2.right - tolerance or rect1.right <= rect2.left + tolerance or
                rect1.top >= rect2.bottom - tolerance or rect1.bottom <= rect2.top + tolerance)

def is_overlapping_any_other_window(check_rect, all_windows_states, current_window_hwnd, tolerance=0):
    """
    Checks if check_rect overlaps with any other window in all_windows_states,
    excluding the current_window_hwnd itself.
    """
    for window_state in all_windows_states:
        if window_state['hwnd'] == current_window_hwnd:
            continue # Don't check against itself

        other_rect = window_state['current_rect']
        if other_rect and do_rects_overlap(check_rect, other_rect, tolerance):
            return True
    return False

def get_ideal_directional_corner(current_corner_index, mouse_x, mouse_y, window_rect):
    """
    Determines the *ideal* target corner based on mouse position relative to window's center.
    This does NOT check for overlaps or validity; it's purely directional.
    """
    wx, wy = window_rect.left, window_rect.top
    ww, wh = window_rect.width(), window_rect.height()
    
    mid_x = wx + ww / 2
    mid_y = wy + wh / 2

    mouse_right_of_center = mouse_x > mid_x
    mouse_bottom_of_center = mouse_y > mid_y
    
    diff_x_from_center = abs(mouse_x - mid_x)
    diff_y_from_center = abs(mouse_y - mid_y)

    ideal_target_corner = current_corner_index # Default

    if current_corner_index == 0: # Current: Top-Left (Q2)
        if mouse_right_of_center and mouse_bottom_of_center:
            if diff_x_from_center > diff_y_from_center: ideal_target_corner = 3 # Bottom-Left
            else: ideal_target_corner = 1 # Top-Right
        elif mouse_right_of_center: ideal_target_corner = 3 # Bottom-Left
        elif mouse_bottom_of_center: ideal_target_corner = 1 # Top-Right
        else: ideal_target_corner = 2 # Bottom-Right

    elif current_corner_index == 1: # Current: Top-Right (Q1)
        if not mouse_right_of_center and mouse_bottom_of_center:
            if diff_x_from_center > diff_y_from_center: ideal_target_corner = 2 # Bottom-Right
            else: ideal_target_corner = 0 # Top-Left
        elif not mouse_right_of_center: ideal_target_corner = 2 # Bottom-Right
        elif mouse_bottom_of_center: ideal_target_corner = 0 # Top-Left
        else: ideal_target_corner = 3 # Bottom-Left

    elif current_corner_index == 2: # Current: Bottom-Right (Q4)
        if not mouse_right_of_center and not mouse_bottom_of_center:
            if diff_x_from_center > diff_y_from_center: ideal_target_corner = 1 # Top-Right
            else: ideal_target_corner = 3 # Bottom-Left
        elif not mouse_right_of_center: ideal_target_corner = 1 # Top-Right
        elif not mouse_bottom_of_center: ideal_target_corner = 3 # Bottom-Left
        else: ideal_target_corner = 0 # Top-Left

    elif current_corner_index == 3: # Current: Bottom-Left (Q3)
        if mouse_right_of_center and not mouse_bottom_of_center:
            if diff_x_from_center > diff_y_from_center: ideal_target_corner = 0 # Top-Left
            else: ideal_target_corner = 2 # Bottom-Right
        elif mouse_right_of_center: ideal_target_corner = 0 # Top-Left
        elif not mouse_bottom_of_center: ideal_target_corner = 2 # Bottom-Right
        else: ideal_target_corner = 1 # Top-Right
            
    return ideal_target_corner

def get_safe_target_corner(current_corner_index, ideal_corner_index, all_windows_states, current_window_hwnd, screen_w, screen_h, win_w, win_h, gap):
    """
    Finds a safe (non-overlapping and allowed) target corner, prioritizing ideal_corner_index.
    If ideal is not safe/allowed, it cycles through other allowed corners.
    """
    
    # Try the ideal corner first if it's allowed
    if ideal_corner_index in VALID_INTERNAL_CORNERS:
        potential_x, potential_y = get_corner_coordinates(ideal_corner_index, screen_w, screen_h, win_w, win_h, gap)
        potential_rect = RECT(potential_x, potential_y, potential_x + win_w, potential_y + win_h)
        if not is_overlapping_any_other_window(potential_rect, all_windows_states, current_window_hwnd):
            return ideal_corner_index # Ideal corner is safe and allowed!

    # If ideal corner failed, try other allowed corners in a cyclic fashion starting from current
    
    # Create a test order: start from current_corner_index, then cycle through VALID_INTERNAL_CORNERS
    try:
        start_idx_in_valid = VALID_INTERNAL_CORNERS.index(current_corner_index)
    except ValueError: # Current corner is somehow not in VALID_INTERNAL_CORNERS - fall back to first valid
        start_idx_in_valid = 0 
        
    ordered_corners_to_try = []
    for i in range(len(VALID_INTERNAL_CORNERS)):
        idx = (start_idx_in_valid + i) % len(VALID_INTERNAL_CORNERS)
        ordered_corners_to_try.append(VALID_INTERNAL_CORNERS[idx])
        
    # Remove the current corner from this list if it's the only option or already checked as ideal
    # (it might be the first in ordered_corners_to_try if it was the initial starting point)
    # We want to try *other* corners first if the ideal one failed
    # But if current_corner_index is the *only* valid one and ideal failed, we return current.
    
    for corner_to_try in ordered_corners_to_try:
        if corner_to_try == current_corner_index and len(VALID_INTERNAL_CORNERS) > 1: # Don't try staying in same spot unless no other option
            continue

        potential_x, potential_y = get_corner_coordinates(corner_to_try, screen_w, screen_h, win_w, win_h, gap)
        potential_rect = RECT(potential_x, potential_y, potential_x + win_w, potential_y + win_h)
        if not is_overlapping_any_other_window(potential_rect, all_windows_states, current_window_hwnd):
            return corner_to_try # Found a safe and allowed corner

    # If no safe and allowed corner is found, return the current corner (stay put)
    return current_corner_index

def ease_out_quad(t):
    """Quadratic easing out: starts fast, slows down at end. t is 0.0 to 1.0"""
    return t * (2 - t)

def instant_move_window(hwnd, x, y, width, height, always_on_top=True):
    """Teleports window to coordinates instantly, maintaining size and Z-order."""
    flags = SWP_SHOWWINDOW | SWP_NOACTIVATE
    insert = HWND_TOPMOST if always_on_top else HWND_NOTOPMOST
    user32.SetWindowPos(hwnd, insert, int(x), int(y), int(width), int(height), flags)

def smooth_move_window(hwnd, start_x, start_y, end_x, end_y, width, height):
    """Interpolates window position smoothly over time."""
    if not user32.IsWindow(hwnd): return

    total_frames = int(ANIMATION_DURATION_SECONDS * ANIMATION_FPS)
    if total_frames <= 0: # Skip animation if duration is too short or FPS too low
        instant_move_window(hwnd, end_x, end_y, width, height)
        return

    frame_interval = 1.0 / ANIMATION_FPS
    flags = SWP_NOACTIVATE | SWP_NOZORDER | SWP_NOSIZE 

    start_time = time.perf_counter()

    for frame in range(total_frames + 1): # Include the "end" frame
        elapsed_time = time.perf_counter() - start_time
        linear_progress = min(elapsed_time / ANIMATION_DURATION_SECONDS, 1.0)
        
        eased_progress = ease_out_quad(linear_progress)

        current_x = start_x + (end_x - start_x) * eased_progress
        current_y = start_y + (end_y - start_y) * eased_progress

        user32.SetWindowPos(hwnd, 0, int(current_x), int(current_y), 0, 0, flags)
        
        # Calculate when the next frame should be rendered
        target_next_frame_time = start_time + (frame + 1) * frame_interval
        sleep_time = target_next_frame_time - time.perf_counter()
        if sleep_time > 0:
            time.sleep(sleep_time)
        
        if linear_progress >= 1.0:
            break
    
    # Ensure window is exactly at the final position and size with correct Z-order
    instant_move_window(hwnd, end_x, end_y, width, height, always_on_top=True)


# --- Main ---
def main():
    global WINDOW_SCREEN_FRACTION, CORNER_GAP_PIXELS, ANIMATION_FPS, VALID_INTERNAL_CORNERS, NO_RESIZE, NUM_WINDOWS_TO_CONTROL
    global g_hook_id, g_selected_hwnds

    parser = argparse.ArgumentParser(
        description="A script that makes selected Windows dodge your mouse with smooth animation. Supports up to 4 windows, preventing overlap.",
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

    args = parser.parse_args()

    # Apply arguments to global configuration
    WINDOW_SCREEN_FRACTION = args.size
    ANIMATION_FPS = args.fps
    CORNER_GAP_PIXELS = args.gap
    NO_RESIZE = args.no_resize
    NUM_WINDOWS_TO_CONTROL = args.num_windows

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


    print("--- Smooth Directional Window Dodging Script ---")
    print(f"Config: Number of windows: {NUM_WINDOWS_TO_CONTROL}")
    print(f"Config: Size {WINDOW_SCREEN_FRACTION*100:.0f}%, Gap {CORNER_GAP_PIXELS}px")
    print(f"Animation: {ANIMATION_DURATION_SECONDS}s duration at {ANIMATION_FPS} FPS")
    if NO_RESIZE:
        print("Window resizing is DISABLED (--no-resize flag active).")
    
    active_corners_names = [INTERNAL_CORNER_TO_MATH_QUAD_NAME[idx] for idx in VALID_INTERNAL_CORNERS]
    print(f"Active Corners: {', '.join(active_corners_names)}")

    print(f"\nIMPORTANT: LEFT-CLICK on {NUM_WINDOWS_TO_CONTROL} unique windows to control (not this console).")

    h_instance = kernel32.GetModuleHandleW(None)
    g_hook_id = user32.SetWindowsHookExW(WH_MOUSE_LL, mouse_hook_proc, h_instance, 0)
    if not g_hook_id:
        return print("Failed to install mouse hook. Ensure you have sufficient permissions (e.g., run as administrator). Exiting.")

    msg = MSG()
    # The message loop will run until PostQuitMessage(0) is called from the hook,
    # which happens after all desired windows are selected.
    while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) > 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))

    if g_hook_id: user32.UnhookWindowsHookEx(g_hook_id)

    if len(g_selected_hwnds) < NUM_WINDOWS_TO_CONTROL:
        return print(f"Only {len(g_selected_hwnds)}/{NUM_WINDOWS_TO_CONTROL} windows selected. Exiting.")

    scr_w, scr_h = get_screen_dimensions()
    print(f"Detected screen dimensions: {scr_w}x{scr_h} (Note: May reflect logical resolution due to display scaling)")

    controlled_windows = [] # List to hold state for each controlled window

    for i, hwnd in enumerate(g_selected_hwnds):
        if not user32.IsWindow(hwnd):
            print(f"Warning: Selected window {i+1} (handle {hwnd}) is no longer valid. Skipping.")
            continue

        window_title, window_class = get_window_info(hwnd)
        print(f"\n--- Initializing Window {i+1} ---")
        print(f"Window handle: {hwnd}")
        print(f"Window title: '{window_title}' (Class: '{window_class}')")

        initial_window_rect = get_window_rect(hwnd)
        if not initial_window_rect:
            print(f"Could not get initial dimensions for window {i+1}. Skipping.")
            continue
        
        initial_w = initial_window_rect.width()
        initial_h = initial_window_rect.height()

        min_size = 100
        if initial_w <= 0 or initial_h <= 0:
            print("Warning: Original window has invalid (zero or negative) dimensions. Using default minimum.")
            initial_w = min_size
            initial_h = min_size
            
        final_win_w, final_win_h = initial_w, initial_h # Start with original size

        if not NO_RESIZE:
            target_w = int(scr_w * WINDOW_SCREEN_FRACTION)
            target_h = int(scr_h * WINDOW_SCREEN_FRACTION)

            aspect_ratio = initial_w / initial_h
            
            scale_by_width = target_w / initial_w
            scale_by_height = target_h / initial_h
            actual_scale_factor = min(scale_by_width, scale_by_height)
            
            final_win_w = int(initial_w * actual_scale_factor)
            final_win_h = int(initial_h * actual_scale_factor)

            final_win_w = max(final_win_w, min_size)
            final_win_h = max(final_win_h, min_size)
        
        max_available_w = scr_w - 2 * CORNER_GAP_PIXELS
        max_available_h = scr_h - 2 * CORNER_GAP_PIXELS

        if final_win_w > max_available_w or final_win_h > max_available_h:
            print("Warning: Window size with gap exceeds screen boundaries. Scaling down to fit.")
            # Recalculate aspect ratio from potentially scaled size to be safe
            current_aspect_ratio_calc = final_win_w / final_win_h if final_win_h > 0 else 1.0 
            
            scale_by_max_w = max_available_w / final_win_w if final_win_w > 0 else 1.0
            scale_by_max_h = max_available_h / final_win_h if final_win_h > 0 else 1.0
            
            actual_scale_factor_to_fit_gap = min(scale_by_max_w, scale_by_max_h)
            
            final_win_w = int(final_win_w * actual_scale_factor_to_fit_gap)
            final_win_h = int(final_win_h * actual_scale_factor_to_fit_gap)
            
            final_win_w = max(final_win_w, min_size)
            final_win_h = max(final_win_h, min_size)

        if final_win_w <= 0 or final_win_h <= 0:
            print("Calculated final window dimensions are invalid. Skipping this window.")
            continue

        print(f"Final window dimensions: {final_win_w}x{final_win_h} with a {CORNER_GAP_PIXELS}px gap.")

        # Assign initial unique corner to each window
        initial_corner_index = VALID_INTERNAL_CORNERS[i % len(VALID_INTERNAL_CORNERS)]
        initial_x, initial_y = get_corner_coordinates(initial_corner_index, scr_w, scr_h, final_win_w, final_win_h, CORNER_GAP_PIXELS)
        
        # Check for overlap with already placed windows
        initial_rect_for_overlap_check = RECT(initial_x, initial_y, initial_x + final_win_w, initial_y + final_win_h)
        if is_overlapping_any_other_window(initial_rect_for_overlap_check, controlled_windows, hwnd):
            # If initial corner overlaps, try to find another free corner for initial placement
            print(f"Initial corner {INTERNAL_CORNER_TO_MATH_QUAD_NAME[initial_corner_index]} overlaps. Finding new initial spot...")
            found_initial_spot = False
            for try_idx in range(len(VALID_INTERNAL_CORNERS)):
                candidate_corner = VALID_INTERNAL_CORNERS[(i + try_idx) % len(VALID_INTERNAL_CORNERS)]
                candidate_x, candidate_y = get_corner_coordinates(candidate_corner, scr_w, scr_h, final_win_w, final_win_h, CORNER_GAP_PIXELS)
                candidate_rect = RECT(candidate_x, candidate_y, candidate_x + final_win_w, candidate_y + final_win_h)
                if not is_overlapping_any_other_window(candidate_rect, controlled_windows, hwnd):
                    initial_corner_index = candidate_corner
                    initial_x, initial_y = candidate_x, candidate_y
                    found_initial_spot = True
                    break
            if not found_initial_spot:
                print(f"Could not find a unique initial non-overlapping spot for window {i+1}. Skipping this window.")
                continue


        instant_move_window(hwnd, initial_x, initial_y, final_win_w, final_win_h, True)
        current_rect_after_move = get_window_rect(hwnd) # Get actual rect after move
        
        if not current_rect_after_move:
             print(f"Failed to get rect after initial move for window {i+1}. Skipping.")
             continue

        controlled_windows.append({
            'hwnd': hwnd,
            'current_corner_index': initial_corner_index,
            'current_rect': current_rect_after_move,
            'final_win_w': final_win_w,
            'final_win_h': final_win_h
        })
        print(f"Window {i+1} initialized at {INTERNAL_CORNER_TO_MATH_QUAD_NAME[initial_corner_index]} and set to always on top.")

    if not controlled_windows:
        return print("No valid windows to control. Exiting.")

    try:
        while True:
            # Clean up invalid windows
            controlled_windows[:] = [win for win in controlled_windows if user32.IsWindow(win['hwnd'])]
            if not controlled_windows:
                print("All controlled windows have been closed. Exiting.")
                break

            for window_state in controlled_windows:
                hwnd = window_state['hwnd']
                # Reaffirm always-on-top status periodically
                user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_ASYNCWINDOWPOS)

                mouse_pos = POINT()
                user32.GetCursorPos(ctypes.byref(mouse_pos))

                if is_mouse_in_window(hwnd):
                    print(f"Mouse entered window {hwnd}! Dodging directionally...")
                    
                    current_rect = get_window_rect(hwnd)
                    if not current_rect:
                        print(f"Could not get window rectangle for {hwnd}, assuming it's closing.")
                        continue # This window will be removed in the next cleanup

                    window_state['current_rect'] = current_rect # Update rect in state

                    ideal_corner_index = get_ideal_directional_corner(window_state['current_corner_index'], mouse_pos.x, mouse_pos.y, current_rect)
                    
                    # Find a safe target corner (non-overlapping and allowed)
                    target_corner_index = get_safe_target_corner(
                        window_state['current_corner_index'],
                        ideal_corner_index,
                        controlled_windows,
                        hwnd,
                        scr_w, scr_h,
                        window_state['final_win_w'],
                        window_state['final_win_h'],
                        CORNER_GAP_PIXELS
                    )
                    
                    if target_corner_index != window_state['current_corner_index']:
                        print(f"Window {hwnd} moving from {INTERNAL_CORNER_TO_MATH_QUAD_NAME[window_state['current_corner_index']]} to {INTERNAL_CORNER_TO_MATH_QUAD_NAME[target_corner_index]}.")
                        window_state['current_corner_index'] = target_corner_index

                        target_x, target_y = get_corner_coordinates(target_corner_index, scr_w, scr_h, window_state['final_win_w'], window_state['final_win_h'], CORNER_GAP_PIXELS)
                        
                        smooth_move_window(hwnd, current_rect.left, current_rect.top, target_x, target_y, window_state['final_win_w'], window_state['final_win_h'])
                        
                        # Update the window's rect after smooth move
                        window_state['current_rect'] = get_window_rect(hwnd) 
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