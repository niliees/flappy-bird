import io
import pygame, sys, random
import os
from pathlib import Path
import tkinter as tk
from tkinter import simpledialog, messagebox
import requests
import threading
import json
import numpy as np
import math
import uuid
import time
import webbrowser
from datetime import datetime, timedelta
from pygame import rect

# Firebase Configuration
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyCs0xM154UTEUxhOCv-FqqL1i6zHlZHfug",
    "authDomain": "nsce-fr1.firebaseapp.com",
    "databaseURL": "https://nsce-fr1-default-rtdb.europe-west1.firebasedatabase.app",
    "projectId": "nsce-fr1",
    "storageBucket": "nsce-fr1.firebasestorage.app",
    "messagingSenderId": "344286384535",
    "appId": "1:344286384535:web:2340d545eda9bc21f474d2",
    "measurementId": "G-H7CH1CVCE4"
}

FIREBASE_DB_URL = FIREBASE_CONFIG["databaseURL"]
VERIFY_BASE_URL = "https://verify.nsce.fr"
VERIFY_API_URL = f"{VERIFY_BASE_URL}/api"

sync_status_cache = {
    "status": "unknown",
    "last_check": 0,
    "check_interval": 5.0
}


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    path = os.path.join(base_path, relative_path)

    if not os.path.exists(path):
        current_dir_path = os.path.join(os.path.abspath("."), relative_path)
        if os.path.exists(current_dir_path):
            return current_dir_path
        raise FileNotFoundError(f"Datei '{relative_path}' konnte nicht gefunden werden.")

    return path


# Extended Firebase Functions
def load_extended_data_from_firebase():
    """Load all extended data from Firebase"""
    global player_stats, achievements, unlocked_themes, player_coins, ghost_recorder

    try:
        if not user_id:
            return False

        # Load player stats
        url = f"{FIREBASE_DB_URL}/users/{user_id}/extended_data.json"
        response = requests.get(url, timeout=5)

        if response.status_code == 200 and response.json():
            data = response.json()

            if 'stats' in data:
                player_stats.update(data['stats'])

            if 'achievements' in data:
                for ach_id, ach_data in data['achievements'].items():
                    if ach_id in achievements:
                        achievements[ach_id].update(ach_data)

            if 'unlocked_themes' in data:
                unlocked_themes.extend(data['unlocked_themes'])

            if 'coins' in data:
                player_coins = data['coins']

            if 'ghost_data' in data and data['ghost_data']:
                ghost_recorder.best_run_positions = data['ghost_data'].get('positions', [])
                ghost_recorder.best_score = data['ghost_data'].get('score', 0)

            print("Extended data loaded from Firebase")
            return True

    except Exception as e:
        print(f"Error loading extended data: {e}")

    return False


def save_extended_data_to_firebase():
    """Save extended data to Firebase"""
    if not user_id:
        return False

    extended_data = {
        'stats': player_stats,
        'achievements': {k: v for k, v in achievements.items() if v['unlocked']},
        'unlocked_themes': unlocked_themes,
        'coins': player_coins,
        'ghost_data': {
            'positions': ghost_recorder.best_run_positions,
            'score': ghost_recorder.best_score
        },
        'last_updated': int(time.time())
    }

    try:
        url = f"{FIREBASE_DB_URL}/users/{user_id}/extended_data.json"
        response = requests.put(url, json=extended_data, timeout=5)

        if response.status_code == 200:
            print("Extended data saved to Firebase")
            return True
        else:
            print(f"Failed to save extended data: {response.status_code}")
            return False

    except Exception as e:
        print(f"Error saving extended data: {e}")
        return False


def save_extended_data_async():
    """Save extended data asynchronously"""

    def _save():
        save_extended_data_to_firebase()

    thread = threading.Thread(target=_save)
    thread.daemon = True
    thread.start()


# Original Firebase functions (keeping existing ones)
def load_settings_from_firebase():
    """Load settings from Firebase Realtime Database (primary storage)"""
    global HighScore, current_theme, current_difficulty_preset, fullscreen, user_id

    try:
        local_user_id = load_local_user_id()

        if local_user_id:
            user_id = local_user_id
            url = f"{FIREBASE_DB_URL}/users/{user_id}/settings.json"
            response = requests.get(url, timeout=5)

            if response.status_code == 200 and response.json():
                settings = response.json()
                HighScore = settings.get('high_score', 0)
                current_theme = settings.get('theme', 'Classic')
                current_difficulty_preset = settings.get('difficulty', 'Normal')
                fullscreen = settings.get('fullscreen', False)
                print(f"Settings loaded from Firebase for user: {user_id}")
                return True

        user_id = str(uuid.uuid4())
        save_local_user_id(user_id)
        save_settings_to_firebase()
        print(f"New user created: {user_id}")
        return True

    except Exception as e:
        print(f"Error loading from Firebase: {e}")
        if not user_id:
            user_id = str(uuid.uuid4())
            save_local_user_id(user_id)
        return False


def save_settings_to_firebase():
    """Save settings to Firebase Realtime Database (primary storage)"""
    if not user_id:
        print("No user_id available for saving settings")
        return False

    settings = {
        'user_id': user_id,
        'high_score': HighScore,
        'theme': current_theme,
        'difficulty': current_difficulty_preset,
        'fullscreen': fullscreen,
        'last_updated': int(time.time())
    }

    try:
        url = f"{FIREBASE_DB_URL}/users/{user_id}/settings.json"
        response = requests.put(url, json=settings, timeout=5)

        if response.status_code == 200:
            print("Settings saved to Firebase successfully")
            return True
        else:
            print(f"Failed to save to Firebase: {response.status_code}")
            return False

    except Exception as e:
        print(f"Error saving to Firebase: {e}")
        return False


def load_local_user_id():
    """Load user_id from C:/NSCE/user_id.txt (fallback only)"""
    try:
        nsce_path = "C:/NSCE"
        user_id_file = os.path.join(nsce_path, "user_id.txt")

        if os.path.exists(user_id_file):
            with open(user_id_file, 'r') as f:
                user_id = f.read().strip()
                if user_id:
                    return user_id

    except Exception as e:
        print(f"Error loading user_id from C:/NSCE/: {e}")
    return None


def save_local_user_id(uid):
    """Save user_id to C:/NSCE/user_id.txt (fallback only)"""
    try:
        nsce_path = "C:/NSCE"
        user_id_file = os.path.join(nsce_path, "user_id.txt")

        os.makedirs(nsce_path, exist_ok=True)

        with open(user_id_file, 'w') as f:
            f.write(uid)

        print(f"User ID saved to {user_id_file}")

    except Exception as e:
        print(f"Error saving user_id to C:/NSCE/: {e}")


def sync_high_score_to_firebase():
    """Special function to sync high score immediately when achieved"""
    if not user_id:
        return

    try:
        url = f"{FIREBASE_DB_URL}/users/{user_id}/settings/high_score.json"
        response = requests.put(url, json=HighScore, timeout=3)

        if response.status_code == 200:
            print(f"High score {HighScore} synced to Firebase")
        else:
            print(f"Failed to sync high score: {response.status_code}")

    except Exception as e:
        print(f"Error syncing high score: {e}")


def save_settings_async():
    """Save settings asynchronously to avoid blocking the game"""

    def _save():
        save_settings_to_firebase()

    thread = threading.Thread(target=_save)
    thread.daemon = True
    thread.start()


def update_high_score(new_score):
    """Update high score and sync to Firebase immediately"""
    global HighScore

    if new_score > HighScore:
        HighScore = new_score

        def _sync():
            sync_high_score_to_firebase()

        thread = threading.Thread(target=_sync)
        thread.daemon = True
        thread.start()

        print(f"New high score: {HighScore}")


# Verification functions (keeping existing ones)
def check_uid_verification_status(uid):
    """Check if UID is already verified via verify.nsce.fr API"""
    try:
        response = requests.get(f"{VERIFY_API_URL}/check-uid/{uid}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('verified', False)
        else:
            print(f"Error checking UID status: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error checking verification status: {e}")
        return False


def start_verification_process(uid=None):
    """Start verification process via verify.nsce.fr API"""
    try:
        payload = {}
        if uid:
            payload['uid'] = uid

        response = requests.post(f"{VERIFY_API_URL}/request", json=payload, timeout=10)

        if response.status_code == 200:
            data = response.json()

            if data.get('alreadyVerified'):
                return True, None, data.get('message', 'Already verified')

            return False, {
                'verificationId': data.get('verificationId'),
                'uid': data.get('uid'),
                'verifyUrl': data.get('verifyUrl')
            }, None
        else:
            return False, None, f"API Error: {response.status_code}"

    except Exception as e:
        return False, None, f"Connection error: {str(e)}"


def show_code_input_dialog():
    """SIMPLIFIED: Direct 6-digit code input without explanations"""
    root = tk.Tk()
    root.title("Enter 6-digit Code")
    root.geometry("350x200")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f'+{x}+{y}')

    result = {"code": None, "cancelled": False}

    def on_submit():
        code = code_entry.get().strip()
        if len(code) == 6 and code.isdigit():
            result["code"] = code
            root.destroy()
        else:
            error_label.config(text="Must be exactly 6 digits!", fg="red")

    def on_cancel():
        result["cancelled"] = True
        root.destroy()

    tk.Label(root, text="Enter 6-digit Code", font=("Arial", 16, "bold")).pack(pady=15)
    tk.Label(root, text="Enter the code from the verification website:",
             font=("Arial", 10)).pack(pady=5)

    code_entry = tk.Entry(root, font=("Arial", 16), width=8, justify="center")
    code_entry.pack(pady=15)
    code_entry.focus()

    error_label = tk.Label(root, text="", font=("Arial", 9))
    error_label.pack()

    button_frame = tk.Frame(root)
    button_frame.pack(pady=15)

    tk.Button(button_frame, text="Submit", command=on_submit,
              bg="#4CAF50", fg="white", font=("Arial", 10, "bold"),
              width=10).pack(side="left", padx=5)
    tk.Button(button_frame, text="Cancel", command=on_cancel,
              bg="#f44336", fg="white", font=("Arial", 10),
              width=10).pack(side="left", padx=5)

    root.bind('<Return>', lambda e: on_submit())
    root.bind('<Escape>', lambda e: on_cancel())

    root.mainloop()

    if result["cancelled"]:
        return None
    return result["code"]


def verify_6_digit_code(verification_id, code):
    """Verify the 6-digit code with the backend"""
    try:
        response = requests.get(f"{VERIFY_API_URL}/get-code/{verification_id}", timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('ready'):
                if data.get('code') == code:
                    return True, data.get('uid'), "Code correct"
                else:
                    return False, None, "Wrong code"
            else:
                return False, None, "Email verification not completed yet"
        elif response.status_code == 404:
            return False, None, "Verification session not found"
        else:
            return False, None, f"API Error: {response.status_code}"

    except Exception as e:
        return False, None, f"Connection error: {str(e)}"


def wait_for_verification_completion(verification_id):
    """Simplified - just shows code input"""
    try:
        print("Showing code input dialog...")
        code = show_code_input_dialog()

        if not code:
            return False, "User cancelled", None

        print(f"User entered code: {code}")

        success, uid, message = verify_6_digit_code(verification_id, code)

        if success:
            print(f"Code verification successful! UID: {uid}")
            save_local_user_id(uid)
            return True, uid, message
        else:
            print(f"Code verification failed: {message}")
            return False, message, None

    except Exception as e:
        print(f"Exception in wait_for_verification_completion: {e}")
        return False, f"Error: {str(e)}", None


def upload_highscore(name):
    """Simplified upload function - goes directly to code input"""
    global upload_status, user_id

    try:
        upload_status = "Checking verification status..."
        print(f"Starting verification check for user: {name}")

        local_uid = load_local_user_id()
        print(f"Local UID found: {local_uid}")

        if local_uid:
            upload_status = "Checking if already verified..."
            is_verified = check_uid_verification_status(local_uid)
            print(f"UID verification status: {is_verified}")

            if is_verified:
                upload_status = "Already verified! Uploading score..."
                user_id = local_uid
                upload_highscore_direct(name)
                return

        upload_status = "Starting verification process..."
        print("Starting verification process...")
        already_verified, verify_data, error = start_verification_process(local_uid)

        if error:
            upload_status = f"Verification error: {error}"
            print(f"Verification error: {error}")
            return

        if already_verified:
            upload_status = "Already verified! Uploading score..."
            print("Became verified during process")
            upload_highscore_direct(name)
            return

        verify_url = verify_data['verifyUrl']
        verification_id = verify_data['verificationId']
        target_uid = verify_data['uid']

        print(f"Verification URL: {verify_url}")
        print(f"Verification ID: {verification_id}")

        upload_status = f"Opening browser: {verify_url}"

        try:
            webbrowser.open(verify_url)
            print("Browser opened automatically")
            upload_status = "Browser opened - complete verification then enter code"
        except Exception as e:
            print(f"Could not open browser: {e}")
            upload_status = f"Go to: {verify_url} then enter code"

        max_attempts = 3
        for attempt in range(max_attempts):
            print(f"Code input attempt {attempt + 1}/{max_attempts}")

            upload_status = f"Enter 6-digit code (Attempt {attempt + 1}/{max_attempts})"
            success, verified_uid, message = wait_for_verification_completion(verification_id)

            if success:
                upload_status = "Email verified! Uploading highscore..."
                user_id = verified_uid
                print(f"Verification successful! UID: {verified_uid}")
                upload_highscore_direct(name)
                return
            else:
                upload_status = f"Wrong code: {message}"
                print(f"Verification attempt {attempt + 1} failed: {message}")

                if attempt < max_attempts - 1:
                    upload_status = f"Wrong code. Try again ({attempt + 2}/{max_attempts})"
                else:
                    upload_status = f"Verification failed after {max_attempts} attempts"
                    return

    except Exception as e:
        upload_status = f"Verification error: {str(e)}"
        print(f"Exception in upload_highscore: {e}")
        import traceback
        traceback.print_exc()


def show_upload_dialog():
    """Simplified upload dialog"""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    name = simpledialog.askstring("Upload Highscore", "Enter your name:", parent=root)
    root.destroy()

    if name and name.strip():
        upload_thread = threading.Thread(target=upload_highscore, args=(name.strip(),))
        upload_thread.daemon = True
        upload_thread.start()
        return True
    return False


def upload_highscore_direct(name):
    """Direct upload function (original logic)"""
    global upload_status, user_id

    try:
        url = "https://flappy-bird.nsce.fr/api/upload_score"
        data = {
            "name": name,
            "score": HighScore,
            "user_id": user_id,
            "theme": current_theme,
            "difficulty": current_difficulty_preset
        }
        response = requests.post(url, json=data, timeout=10)

        if response.status_code == 200:
            result = response.json()
            upload_status = result.get("message", "Score uploaded successfully!")
        else:
            upload_status = f"Upload failed: {response.status_code}"
    except Exception as e:
        upload_status = f"Upload error: {str(e)}"


def change_theme(new_theme):
    """Change theme and save to Firebase"""
    global current_theme
    current_theme = new_theme
    save_settings_async()


def change_difficulty(new_difficulty):
    """Change difficulty and save to Firebase"""
    global current_difficulty_preset
    current_difficulty_preset = new_difficulty
    save_settings_async()


def load_settings():
    """Main settings loading function (Firebase primary, no local fallback)"""
    success = load_settings_from_firebase()
    if not success:
        print("Using default settings - Firebase unavailable")


def save_settings():
    """Main settings saving function (Firebase only)"""
    save_settings_to_firebase()


def check_sync_status_async():
    """Check sync status in background thread"""
    global sync_status_cache

    def _check():
        try:
            if not user_id:
                sync_status_cache["status"] = "no_user"
                return

            url = f"{FIREBASE_DB_URL}/users/{user_id}/settings/high_score.json"
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                sync_status_cache["status"] = "connected"
            else:
                sync_status_cache["status"] = "error"
        except:
            sync_status_cache["status"] = "offline"

        sync_status_cache["last_check"] = time.time()

    thread = threading.Thread(target=_check)
    thread.daemon = True
    thread.start()


def draw_sync_status():
    """Draw sync status indicator (OPTIMIZED - no network requests in main loop)"""
    current_time = time.time()

    if current_time - sync_status_cache["last_check"] > sync_status_cache["check_interval"]:
        check_sync_status_async()

    status = sync_status_cache["status"]

    if status == "connected":
        status_color = (0, 255, 0)
        status_text = "●"
    elif status == "error":
        status_color = (255, 165, 0)
        status_text = "⚠"
    else:
        status_color = (255, 0, 0)
        status_text = "●"

    status_surface = font_tiny.render(status_text, True, status_color)
    screen.blit(status_surface, (window_w - 30, 10))


# Optimized filter functions with caching
filter_cache = {}


def get_cached_filtered_image(base_image, filter_func, cache_key):
    """Get filtered image from cache or create and cache it"""
    if cache_key not in filter_cache:
        if filter_func:
            filter_cache[cache_key] = filter_func(base_image)
        else:
            filter_cache[cache_key] = base_image.copy()
    return filter_cache[cache_key]


def clear_filter_cache():
    """Clear filter cache to free memory"""
    global filter_cache
    filter_cache.clear()


def apply_hsl_filter(surface, hue_shift=0, saturation_mult=1.0, lightness_mult=1.0):
    """Erweiterte HSL-Filter-Funktion für präzise Farbmanipulation"""
    arr = pygame.surfarray.array3d(surface).astype(float)
    h, w, c = arr.shape

    r, g, b = arr[:, :, 0] / 255.0, arr[:, :, 1] / 255.0, arr[:, :, 2] / 255.0

    max_val = np.maximum(np.maximum(r, g), b)
    min_val = np.minimum(np.minimum(r, g), b)
    diff = max_val - min_val

    l = (max_val + min_val) / 2.0
    s = np.where(diff == 0, 0, np.where(l < 0.5, diff / (max_val + min_val), diff / (2.0 - max_val - min_val)))

    h_val = np.zeros_like(r)
    mask_r = (max_val == r) & (diff != 0)
    mask_g = (max_val == g) & (diff != 0)
    mask_b = (max_val == b) & (diff != 0)

    h_val[mask_r] = (60 * ((g[mask_r] - b[mask_r]) / diff[mask_r]) + 360) % 360
    h_val[mask_g] = (60 * ((b[mask_g] - r[mask_g]) / diff[mask_g]) + 120) % 360
    h_val[mask_b] = (60 * ((r[mask_b] - g[mask_b]) / diff[mask_b]) + 240) % 360

    h_val = (h_val + hue_shift) % 360
    s = np.clip(s * saturation_mult, 0, 1)
    l = np.clip(l * lightness_mult, 0, 1)

    c_val = (1 - np.abs(2 * l - 1)) * s
    x = c_val * (1 - np.abs((h_val / 60) % 2 - 1))
    m = l - c_val / 2

    r_new, g_new, b_new = np.zeros_like(h_val), np.zeros_like(h_val), np.zeros_like(h_val)

    mask1 = (h_val >= 0) & (h_val < 60)
    mask2 = (h_val >= 60) & (h_val < 120)
    mask3 = (h_val >= 120) & (h_val < 180)
    mask4 = (h_val >= 180) & (h_val < 240)
    mask5 = (h_val >= 240) & (h_val < 300)
    mask6 = (h_val >= 300) & (h_val < 360)

    r_new[mask1], g_new[mask1], b_new[mask1] = c_val[mask1], x[mask1], 0
    r_new[mask2], g_new[mask2], b_new[mask2] = x[mask2], c_val[mask2], 0
    r_new[mask3], g_new[mask3], b_new[mask3] = 0, c_val[mask3], x[mask3]
    r_new[mask4], g_new[mask4], b_new[mask4] = 0, x[mask4], c_val[mask4]
    r_new[mask5], g_new[mask5], b_new[mask5] = x[mask5], 0, c_val[mask5]
    r_new[mask6], g_new[mask6], b_new[mask6] = c_val[mask6], 0, x[mask6]

    r_new = (r_new + m) * 255
    g_new = (g_new + m) * 255
    b_new = (b_new + m) * 255

    new_arr = np.stack([r_new, g_new, b_new], axis=2).astype(np.uint8)
    new_surface = pygame.surfarray.make_surface(new_arr)

    if surface.get_flags() & pygame.SRCALPHA:
        new_surface = new_surface.convert_alpha()
        alpha_arr = pygame.surfarray.array_alpha(surface)
        pygame.surfarray.pixels_alpha(new_surface)[:] = alpha_arr

    return new_surface


def apply_advanced_filter(surface, contrast=1.0, brightness=0, saturation=1.0, hue_shift=0, gamma=1.0):
    """Erweiterte Filter-Funktion mit mehreren Parametern"""
    try:
        arr = pygame.surfarray.array3d(surface).astype(float)

        if gamma != 1.0:
            arr = np.power(arr / 255.0, gamma) * 255.0

        arr = arr * contrast + brightness
        arr = np.clip(arr, 0, 255)

        new_surface = pygame.surfarray.make_surface(arr.astype(np.uint8))

        if saturation != 1.0 or hue_shift != 0:
            new_surface = apply_hsl_filter(new_surface, hue_shift, saturation, 1.0)

        if surface.get_flags() & pygame.SRCALPHA:
            new_surface = new_surface.convert_alpha()
            try:
                alpha_arr = pygame.surfarray.array_alpha(surface)
                pygame.surfarray.pixels_alpha(new_surface)[:] = alpha_arr
            except:
                new_surface.set_alpha(surface.get_alpha())

        return new_surface
    except Exception:
        return surface.copy()


def apply_night_filter(surface):
    """Nacht-Filter: dunkler, bläulich, hoher Kontrast"""
    return apply_advanced_filter(
        surface,
        contrast=1.3,
        brightness=-30,
        saturation=0.7,
        hue_shift=180,
        gamma=0.8
    )


def apply_desert_filter(surface):
    """Wüsten-Filter: wärmer, orange/gelb, heller"""
    return apply_advanced_filter(
        surface,
        contrast=1.1,
        brightness=20,
        saturation=1.3,
        hue_shift=30,
        gamma=1.2
    )


def apply_retro_filter(surface):
    """Retro-Filter: grünlich, niedriger Kontrast, dunkel"""
    return apply_advanced_filter(
        surface,
        contrast=0.8,
        brightness=-10,
        saturation=0.6,
        hue_shift=120,
        gamma=0.9
    )


def apply_neon_filter(surface):
    """Neon-Filter: hohe Sättigung, hoher Kontrast, psychedelisch"""
    return apply_advanced_filter(
        surface,
        contrast=1.5,
        brightness=10,
        saturation=2.0,
        hue_shift=280,
        gamma=1.1
    )


def apply_vintage_filter(surface):
    """Vintage-Filter: Sepia-ähnlich, weicher Kontrast"""
    return apply_advanced_filter(
        surface,
        contrast=0.9,
        brightness=-5,
        saturation=0.4,
        hue_shift=40,
        gamma=1.1
    )


def apply_monochrome_filter(surface):
    """Schwarz-Weiß Filter mit leichtem Blauton"""
    return apply_advanced_filter(
        surface,
        contrast=1.2,
        brightness=0,
        saturation=0.0,
        hue_shift=0,
        gamma=1.0
    )


def draw_modern_button(surface, rect, text, font, color, hover=False, pressed=False):
    """Zeichnet einen modernen Button mit subtilen Effekten"""
    shadow_rect = rect.copy()
    shadow_rect.x += 2
    shadow_rect.y += 2
    pygame.draw.rect(surface, (0, 0, 0, 30), shadow_rect, border_radius=8)

    if pressed:
        button_color = tuple(max(0, c - 20) for c in color)
    elif hover:
        button_color = tuple(min(255, c + 15) for c in color)
    else:
        button_color = color

    pygame.draw.rect(surface, button_color, rect, border_radius=8)

    border_color = tuple(max(0, c - 40) for c in button_color)
    pygame.draw.rect(surface, border_color, rect, width=2, border_radius=8)

    text_color = (255, 255, 255) if sum(color) < 400 else (0, 0, 0)
    text_surface = font.render(text, True, text_color)
    text_rect = text_surface.get_rect(center=rect.center)
    if pressed:
        text_rect.x += 1
        text_rect.y += 1

    surface.blit(text_surface, text_rect)


def draw_card(surface, rect, title, content, theme_colors):
    """Zeichnet eine moderne Karte mit Titel und Inhalt"""
    shadow_rect = rect.copy()
    shadow_rect.x += 3
    shadow_rect.y += 3
    pygame.draw.rect(surface, (0, 0, 0, 20), shadow_rect, border_radius=12)

    card_color = (240, 240, 245) if sum(theme_colors["bg_color"]) > 400 else (40, 40, 50)
    pygame.draw.rect(surface, card_color, rect, border_radius=12)

    border_color = theme_colors["highlight_color"]
    pygame.draw.rect(surface, border_color, rect, width=2, border_radius=12)

    if title:
        title_color = theme_colors["text_color"]
        title_surface = font_small.render(title, True, title_color)
        title_pos = (rect.x + 20, rect.y + 15)
        surface.blit(title_surface, title_pos)


# Initialize Game
pygame.init()

# Global Variables - Extended
game_state = 1
score = 0
has_moved = False
HighScore = 0
window_focused = True
upload_status = ""
fullscreen = False
user_id = None

# NEW: Extended game variables
player_coins = 0
achievement_display_timer = 0
current_achievement_message = None
music_enabled = True
current_music = None

# Game area constants
GAME_WIDTH, GAME_HEIGHT = 400, 600
game_area = pygame.Rect(0, 0, GAME_WIDTH, GAME_HEIGHT)

GROUND_HEIGHT = 64
ACTUAL_PLAY_HEIGHT = GAME_HEIGHT - GROUND_HEIGHT

# Difficulty variables
base_pipe_velocity = 2.4
base_gap = 220
difficulty_level = 0
last_difficulty_update = 0

difficulty_presets = {
    "Normal": {
        "pipe_spacing": 200,
        "difficulty_increase_interval": 3,
        "velocity_multiplier": 0.05,
        "gap_decrease": 5,
        "spacing_decrease": 10,
        "min_gap": 120,
        "min_spacing": 250
    },
    "Schwer": {
        "pipe_spacing": 350,
        "difficulty_increase_interval": 2,
        "velocity_multiplier": 0.07,
        "gap_decrease": 7,
        "spacing_decrease": 15,
        "min_gap": 100,
        "min_spacing": 200
    },
    "Hardcore": {
        "pipe_spacing": 300,
        "difficulty_increase_interval": 1,
        "velocity_multiplier": 0.1,
        "gap_decrease": 10,
        "spacing_decrease": 20,
        "min_gap": 130,
        "min_spacing": 170
    }
}

current_difficulty_preset = "Normal"

# Extended Themes with shop prices and unlock requirements
themes = {
    "Classic": {
        "bg_color": (113, 197, 207),
        "text_color": (0, 0, 0),
        "highlight_color": (255, 215, 0),
        "accent_color": (255, 165, 0),
        "filter": None,
        "price": 0,
        "unlock_requirement": None
    },
    "Night": {
        "bg_color": (15, 15, 35),
        "text_color": (220, 230, 255),
        "highlight_color": (100, 150, 255),
        "accent_color": (50, 100, 200),
        "filter": apply_night_filter,
        "price": 50,
        "unlock_requirement": {"type": "score", "value": 10}
    },
    "Desert": {
        "bg_color": (245, 210, 150),
        "text_color": (80, 40, 0),
        "highlight_color": (255, 140, 0),
        "accent_color": (200, 100, 50),
        "filter": apply_desert_filter,
        "price": 75,
        "unlock_requirement": {"type": "score", "value": 20}
    },
    "Retro": {
        "bg_color": (30, 50, 30),
        "text_color": (100, 255, 100),
        "highlight_color": (150, 255, 150),
        "accent_color": (50, 200, 50),
        "filter": apply_retro_filter,
        "price": 100,
        "unlock_requirement": {"type": "achievement", "value": "retro_lover"}
    },
    "Neon": {
        "bg_color": (10, 5, 25),
        "text_color": (255, 100, 255),
        "highlight_color": (0, 255, 255),
        "accent_color": (255, 0, 255),
        "filter": apply_neon_filter,
        "price": 150,
        "unlock_requirement": {"type": "coins", "value": 100}
    },
    "Vintage": {
        "bg_color": (200, 180, 140),
        "text_color": (60, 40, 20),
        "highlight_color": (180, 120, 60),
        "accent_color": (150, 100, 50),
        "filter": apply_vintage_filter,
        "price": 125,
        "unlock_requirement": {"type": "games", "value": 50}
    },
    "Mono": {
        "bg_color": (80, 80, 80),
        "text_color": (255, 255, 255),
        "highlight_color": (200, 200, 200),
        "accent_color": (150, 150, 150),
        "filter": apply_monochrome_filter,
        "price": 200,
        "unlock_requirement": {"type": "score", "value": 100}
    }
}

current_theme = "Classic"

# NEW: Player Statistics
player_stats = {
    "games_played": 0,
    "total_score": 0,
    "best_streak": 0,
    "theme_usage": {theme: 0 for theme in themes},
    "difficulty_usage": {diff: 0 for diff in difficulty_presets},
    "total_playtime": 0,
    "total_jumps": 0,
    "total_coins_collected": 0,
    "coins_earned": 0
}

# NEW: Achievement System
achievements = {
    "first_flight": {
        "name": "First Flight",
        "description": "Score your first point",
        "unlocked": False,
        "reward": 10,
        "icon": "🎯"
    },
    "high_flyer": {
        "name": "High Flyer",
        "description": "Reach 25 points",
        "unlocked": False,
        "reward": 25,
        "icon": "🚀"
    },
    "theme_collector": {
        "name": "Style Master",
        "description": "Unlock 3 different themes",
        "unlocked": False,
        "reward": 50,
        "icon": "🎨"
    },
    "speed_demon": {
        "name": "Speed Demon",
        "description": "Survive 50 points on Hardcore difficulty",
        "unlocked": False,
        "reward": 100,
        "icon": "⚡"
    },
    "coin_collector": {
        "name": "Coin Collector",
        "description": "Collect 100 coins total",
        "unlocked": False,
        "reward": 30,
        "icon": "💰"
    },
    "persistent": {
        "name": "Persistent",
        "description": "Play 100 games",
        "unlocked": False,
        "reward": 75,
        "icon": "🏆"
    },
    "retro_lover": {
        "name": "Retro Lover",
        "description": "Play 10 games in Night theme",
        "unlocked": False,
        "reward": 40,
        "icon": "🌙"
    }
}

# NEW: Unlocked themes (starts with Classic only)
unlocked_themes = ["Classic"]

# Base images
base_images = {
    "background": "images/background.png",
    "ground": "images/ground.png",
    "player": "images/player.png",
    "pipe_up": "images/pipe_up.png",
    "pipe_down": "images/pipe_down.png"
}

# Initialize Firebase settings and extended data
load_settings()

try:
    requests.get("https://www.google.com", timeout=3)
    print("Network available - Firebase sync enabled")
    sync_status_cache["status"] = "connected"
    # Load extended data after basic settings
    load_extended_data_from_firebase()
except:
    print("No network - using local storage only")
    sync_status_cache["status"] = "offline"

# Window Setup
if fullscreen:
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    window_w, window_h = screen.get_size()
    game_area.x = (window_w - GAME_WIDTH) // 2
    game_area.y = (window_h - GAME_HEIGHT) // 2
else:
    window_w, window_h = 800, 600
    screen = pygame.display.set_mode((window_w, window_h))
    game_area.x = (window_w - GAME_WIDTH) // 2
    game_area.y = (window_h - GAME_HEIGHT) // 2

pygame.display.set_caption("Flappy Bird Enhanced")

# Icon loading
try:
    icon_url = "https://flappy-bird.nsce.fr/game/icon.png"
    response = requests.get(icon_url, timeout=5)
    response.raise_for_status()
    icon_data = io.BytesIO(response.content)
    icon = pygame.image.load(icon_data)
    pygame.display.set_icon(icon)
except:
    pass

clock = pygame.time.Clock()
fps = 60

# Load Fonts
font = pygame.font.Font(resource_path("fonts/BaiJamjuree-Bold.ttf"), 80)
font_large = pygame.font.Font(resource_path("fonts/BaiJamjuree-Bold.ttf"), 64)
font_small = pygame.font.Font(resource_path("fonts/BaiJamjuree-Bold.ttf"), 32)
font_medium = pygame.font.Font(resource_path("fonts/BaiJamjuree-Bold.ttf"), 48)
font_tiny = pygame.font.Font(resource_path("fonts/BaiJamjuree-Bold.ttf"), 24)

# Load Sounds
slap_sfx = pygame.mixer.Sound(resource_path("sounds/slap.wav"))
woosh_sfx = pygame.mixer.Sound(resource_path("sounds/woosh.wav"))
score_sfx = pygame.mixer.Sound(resource_path("sounds/score.wav"))
select_sfx = pygame.mixer.Sound(resource_path("sounds/select.wav"))

# NEW: Additional sounds (create placeholder or use existing)
try:
    coin_sfx = pygame.mixer.Sound(resource_path("sounds/coin.wav"))
    achievement_sfx = pygame.mixer.Sound(resource_path("sounds/achievement.wav"))
except:
    # Use existing sounds as fallback
    coin_sfx = score_sfx
    achievement_sfx = select_sfx

# Base images loading
base_loaded_images = {}
for key, path in base_images.items():
    base_loaded_images[key] = pygame.image.load(resource_path(path)).convert_alpha()

# NEW: Create coin image from existing resources (or load if available)
try:
    coin_img = pygame.image.load(resource_path("images/coin.png")).convert_alpha()
except:
    # Create a simple coin from existing images
    coin_img = pygame.Surface((20, 20), pygame.SRCALPHA)
    pygame.draw.circle(coin_img, (255, 215, 0), (10, 10), 8)
    pygame.draw.circle(coin_img, (255, 165, 0), (10, 10), 8, 2)


# NEW: Particle System Class
class ParticleSystem:
    def __init__(self):
        self.particles = []

    def add_death_particles(self, x, y):
        """Add death particles (feathers)"""
        for _ in range(8):
            self.particles.append({
                'x': x + random.randint(-10, 10),
                'y': y + random.randint(-10, 10),
                'vx': random.uniform(-3, 3),
                'vy': random.uniform(-8, -2),
                'life': random.randint(30, 60),
                'max_life': 60,
                'color': themes[current_theme]["highlight_color"],
                'size': random.randint(3, 6),
                'type': 'feather'
            })

    def add_score_particles(self, x, y):
        """Add score particles (sparkles)"""
        for _ in range(5):
            self.particles.append({
                'x': x + random.randint(-15, 15),
                'y': y + random.randint(-15, 15),
                'vx': random.uniform(-2, 2),
                'vy': random.uniform(-3, -1),
                'life': random.randint(20, 40),
                'max_life': 40,
                'color': themes[current_theme]["accent_color"],
                'size': random.randint(2, 4),
                'type': 'sparkle'
            })

    def add_coin_particles(self, x, y):
        """Add coin collection particles"""
        for _ in range(6):
            self.particles.append({
                'x': x,
                'y': y,
                'vx': random.uniform(-2, 2),
                'vy': random.uniform(-4, -1),
                'life': random.randint(15, 30),
                'max_life': 30,
                'color': (255, 215, 0),
                'size': random.randint(3, 5),
                'type': 'coin'
            })

    def update(self):
        """Update all particles"""
        for particle in self.particles[:]:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['vy'] += 0.2  # Gravity
            particle['life'] -= 1

            if particle['life'] <= 0:
                self.particles.remove(particle)

    def draw(self, surface):
        """Draw all particles"""
        for particle in self.particles:
            alpha = int((particle['life'] / particle['max_life']) * 255)
            color = (*particle['color'][:3], alpha)

            # Create surface with per-pixel alpha
            particle_surface = pygame.Surface((particle['size'] * 2, particle['size'] * 2), pygame.SRCALPHA)

            if particle['type'] == 'feather':
                pygame.draw.ellipse(particle_surface, color,
                                    (0, 0, particle['size'] * 2, particle['size']))
            elif particle['type'] == 'sparkle':
                pygame.draw.circle(particle_surface, color,
                                   (particle['size'], particle['size']), particle['size'])
            else:  # coin
                pygame.draw.circle(particle_surface, color,
                                   (particle['size'], particle['size']), particle['size'])

            # Draw to game area
            surface.blit(particle_surface, (game_area.x + particle['x'] - particle['size'],
                                            game_area.y + particle['y'] - particle['size']))


# NEW: Ghost Recorder Class
class GhostRecorder:
    def __init__(self):
        self.best_run_positions = []
        self.current_run = []
        self.best_score = 0
        self.recording = False

    def start_recording(self):
        """Start recording a new run"""
        self.current_run = []
        self.recording = True

    def record_position(self, x, y):
        """Record player position"""
        if self.recording:
            self.current_run.append((x, y))

    def finish_recording(self, final_score):
        """Finish recording and save if it's the best run"""
        self.recording = False
        if final_score > self.best_score:
            self.best_score = final_score
            self.best_run_positions = self.current_run.copy()
            print(f"New ghost recorded! Score: {final_score}")
            save_extended_data_async()

    def get_ghost_position(self, frame):
        """Get ghost position for given frame"""
        if frame < len(self.best_run_positions):
            return self.best_run_positions[frame]
        return None

    def draw_ghost(self, surface, frame):
        """Draw ghost player"""
        ghost_pos = self.get_ghost_position(frame)
        if ghost_pos and self.best_score > 0:
            # Create semi-transparent ghost
            ghost_surface = player_img.copy()
            ghost_surface.set_alpha(80)  # Semi-transparent

            # Tint ghost with theme color
            tint_surface = pygame.Surface(ghost_surface.get_size(), pygame.SRCALPHA)
            tint_surface.fill((*themes[current_theme]["highlight_color"], 60))
            ghost_surface.blit(tint_surface, (0, 0), special_flags=pygame.BLEND_ALPHA_SDL2)

            surface.blit(ghost_surface, (game_area.x + ghost_pos[0], game_area.y + ghost_pos[1]))


# NEW: Coin Class
class Coin:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.collected = False
        self.animation_frame = 0
        self.bobbing = 0

    def update(self):
        """Update coin animation"""
        if not self.collected:
            self.animation_frame += 0.2
            self.bobbing = math.sin(self.animation_frame) * 2

    def draw(self, surface):
        """Draw animated coin"""
        if not self.collected:
            # Apply current theme filter to coin
            filtered_coin = get_cached_filtered_image(coin_img,
                                                      themes[current_theme]["filter"],
                                                      f"{current_theme}_coin")

            draw_y = self.y + self.bobbing
            surface.blit(filtered_coin, (game_area.x + self.x, game_area.y + draw_y))

    def get_rect(self):
        """Get collision rect"""
        return pygame.Rect(self.x, self.y + self.bobbing, coin_img.get_width(), coin_img.get_height())


# NEW: Achievement Functions
def check_achievements():
    """Check for newly unlocked achievements"""
    global player_coins

    newly_unlocked = []

    # First Flight
    if score >= 1 and not achievements["first_flight"]["unlocked"]:
        achievements["first_flight"]["unlocked"] = True
        newly_unlocked.append("first_flight")

    # High Flyer
    if score >= 25 and not achievements["high_flyer"]["unlocked"]:
        achievements["high_flyer"]["unlocked"] = True
        newly_unlocked.append("high_flyer")

    # Theme Collector
    unlocked_count = len([t for t in themes if t in unlocked_themes])
    if unlocked_count >= 3 and not achievements["theme_collector"]["unlocked"]:
        achievements["theme_collector"]["unlocked"] = True
        newly_unlocked.append("theme_collector")

    # Speed Demon
    if (score >= 50 and current_difficulty_preset == "Hardcore" and
            not achievements["speed_demon"]["unlocked"]):
        achievements["speed_demon"]["unlocked"] = True
        newly_unlocked.append("speed_demon")

    # Coin Collector
    if (player_stats["total_coins_collected"] >= 100 and
            not achievements["coin_collector"]["unlocked"]):
        achievements["coin_collector"]["unlocked"] = True
        newly_unlocked.append("coin_collector")

    # Persistent
    if (player_stats["games_played"] >= 100 and
            not achievements["persistent"]["unlocked"]):
        achievements["persistent"]["unlocked"] = True
        newly_unlocked.append("persistent")

    # Retro Lover
    if (player_stats["theme_usage"].get("Night", 0) >= 10 and
            not achievements["retro_lover"]["unlocked"]):
        achievements["retro_lover"]["unlocked"] = True
        newly_unlocked.append("retro_lover")

    # Award coins for newly unlocked achievements
    for achievement_id in newly_unlocked:
        reward = achievements[achievement_id]["reward"]
        player_coins += reward
        player_stats["coins_earned"] += reward
        show_achievement(achievement_id)
        pygame.mixer.Sound.play(achievement_sfx)

    if newly_unlocked:
        save_extended_data_async()


def show_achievement(achievement_id):
    """Show achievement notification"""
    global current_achievement_message, achievement_display_timer

    achievement = achievements[achievement_id]
    current_achievement_message = {
        "title": f"{achievement['icon']} {achievement['name']}",
        "description": achievement["description"],
        "reward": achievement["reward"]
    }
    achievement_display_timer = 180  # 3 seconds at 60 FPS


def draw_achievement_notification():
    """Draw achievement notification popup"""
    global achievement_display_timer

    if current_achievement_message and achievement_display_timer > 0:
        # Calculate animation
        fade_in_time = 30
        fade_out_time = 30
        if achievement_display_timer > 180 - fade_in_time:
            alpha = int((fade_in_time - (180 - achievement_display_timer)) / fade_in_time * 255)
        elif achievement_display_timer < fade_out_time:
            alpha = int(achievement_display_timer / fade_out_time * 255)
        else:
            alpha = 255

        # Draw notification card
        card_rect = pygame.Rect(window_w // 2 - 200, 50, 400, 100)

        # Create surface with alpha
        notification_surface = pygame.Surface((400, 100), pygame.SRCALPHA)

        # Draw card on notification surface
        pygame.draw.rect(notification_surface, (*themes[current_theme]["highlight_color"], alpha // 2),
                         (0, 0, 400, 100), border_radius=15)
        pygame.draw.rect(notification_surface, (*themes[current_theme]["accent_color"], alpha),
                         (0, 0, 400, 100), 3, border_radius=15)

        # Draw text with alpha
        title_surface = font_small.render(current_achievement_message["title"], True,
                                          (*themes[current_theme]["text_color"], alpha))
        desc_surface = font_tiny.render(current_achievement_message["description"], True,
                                        (*themes[current_theme]["text_color"], alpha))
        reward_surface = font_tiny.render(f"+{current_achievement_message['reward']} coins!", True,
                                          (255, 215, 0, alpha))

        notification_surface.blit(title_surface, (20, 15))
        notification_surface.blit(desc_surface, (20, 45))
        notification_surface.blit(reward_surface, (20, 70))

        screen.blit(notification_surface, card_rect)

        achievement_display_timer -= 1
        if achievement_display_timer <= 0:
            current_achievement_message = None


# NEW: Daily Challenge System
def generate_daily_challenge():
    """Generate daily challenge based on current date"""
    today = datetime.now().strftime("%Y-%m-%d")

    # Use date as seed for consistent daily challenges
    random.seed(hash(today))

    challenges = [
        {"type": "score", "target": 15, "description": "Reach 15 points", "reward": 25},
        {"type": "theme", "theme": "Night", "target": 5, "description": "Play 5 games in Night theme", "reward": 30},
        {"type": "difficulty", "difficulty": "Schwer", "target": 10, "description": "Survive 10 points on Hard",
         "reward": 40},
        {"type": "coins", "target": 20, "description": "Collect 20 coins", "reward": 35},
        {"type": "no_death", "target": 3, "description": "Survive 3 consecutive games with score > 5", "reward": 50}
    ]

    challenge = random.choice(challenges)
    challenge["date"] = today
    challenge["progress"] = 0
    challenge["completed"] = False

    # Reset random seed
    random.seed()

    return challenge


# NEW: Shop Functions
def can_unlock_theme(theme_name):
    """Check if theme can be unlocked"""
    if theme_name in unlocked_themes:
        return False, "Already unlocked"

    theme = themes[theme_name]

    # Check unlock requirement
    req = theme.get("unlock_requirement")
    if req:
        if req["type"] == "score" and HighScore < req["value"]:
            return False, f"Need high score of {req['value']}"
        elif req["type"] == "achievement" and not achievements[req["value"]]["unlocked"]:
            return False, f"Need achievement: {achievements[req['value']]['name']}"
        elif req["type"] == "coins" and player_coins < req["value"]:
            return False, f"Need {req['value']} coins"
        elif req["type"] == "games" and player_stats["games_played"] < req["value"]:
            return False, f"Need to play {req['value']} games"

    # Check if player has enough coins
    if player_coins < theme["price"]:
        return False, f"Need {theme['price']} coins"

    return True, "Can unlock"


def unlock_theme(theme_name):
    """Unlock theme with coins"""
    can_unlock, reason = can_unlock_theme(theme_name)

    if can_unlock:
        theme = themes[theme_name]
        player_coins -= theme["price"]
        unlocked_themes.append(theme_name)
        save_extended_data_async()
        return True

    return False


# Theme-based images and masks loading (existing function)
def load_theme_images(theme_name):
    theme = themes[theme_name]
    filter_func = theme["filter"]

    images = {}
    masks = {}

    for key, base_image in base_loaded_images.items():
        cache_key = f"{theme_name}_{key}"
        filtered_image = get_cached_filtered_image(base_image, filter_func, cache_key)
        images[key] = filtered_image
        masks[f"{key}_mask"] = pygame.mask.from_surface(filtered_image)

    return images, masks


# Load initial theme images
theme_images, theme_masks = load_theme_images(current_theme)
player_img = theme_images["player"]
pipe_up_img = theme_images["pipe_up"]
pipe_down_img = theme_images["pipe_down"]
ground_img = theme_images["ground"]
bg_img = theme_images["background"]

pipe_up_mask = theme_masks["pipe_up_mask"]
pipe_down_mask = theme_masks["pipe_down_mask"]

bg_width = bg_img.get_width()

# Variable Setup
bg_scroll_spd = 1
ground_scroll_spd = 2

# NEW: Initialize extended game objects
particle_system = ParticleSystem()
ghost_recorder = GhostRecorder()
coins = []
game_frame_counter = 0
current_daily_challenge = generate_daily_challenge()


# Player class (enhanced)
class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.velocity = 0
        self.rotated_image = player_img
        self.rect = self.rotated_image.get_rect(topleft=(self.x, self.y))
        self.mask = pygame.mask.from_surface(self.rotated_image)

    def jump(self):
        self.velocity = -10
        # NEW: Track jumps
        player_stats["total_jumps"] += 1

    def update(self):
        self.velocity += 0.75 * dt * 60
        self.y += self.velocity * dt * 60

        if self.y < 0:
            self.y = 0
            self.velocity = 0
        elif self.y > ACTUAL_PLAY_HEIGHT - player_img.get_height():
            self.y = ACTUAL_PLAY_HEIGHT - player_img.get_height()
            self.velocity = 0

        angle = max(-30, min(30, -self.velocity * 3))
        self.rotated_image = pygame.transform.rotate(player_img, angle)
        self.mask = pygame.mask.from_surface(self.rotated_image)

        center_x = self.x + player_img.get_width() // 2
        center_y = self.y + player_img.get_height() // 2
        self.rect = self.rotated_image.get_rect(center=(center_x, center_y))

    def draw(self):
        draw_x = game_area.x + self.rect.x
        draw_y = game_area.y + self.rect.y

        if (draw_x + self.rotated_image.get_width() > game_area.x and
                draw_x < game_area.x + GAME_WIDTH and
                draw_y + self.rotated_image.get_height() > game_area.y and
                draw_y < game_area.y + GAME_HEIGHT):
            screen.blit(self.rotated_image, (draw_x, draw_y))


# Enhanced scoreboard
def scoreboard():
    # Score
    show_score = font.render(str(score), True, themes[current_theme]["text_color"])
    score_rect = show_score.get_rect(center=(game_area.x + GAME_WIDTH // 2, game_area.y + 485))
    screen.blit(show_score, score_rect)

    # High Score
    show_HighScore = font_small.render(f"Best: {HighScore}", True, themes[current_theme]["text_color"])
    HighScore_rect = show_HighScore.get_rect(center=(game_area.x + GAME_WIDTH // 4, game_area.y + 30))
    screen.blit(show_HighScore, HighScore_rect)

    # NEW: Coins display
    coin_text = font_tiny.render(f"Coins: {player_coins}", True, (255, 215, 0))
    screen.blit(coin_text, (game_area.x + 10, game_area.y + 60))

    # NEW: Ghost score display
    if ghost_recorder.best_score > 0:
        ghost_text = font_tiny.render(f"Ghost: {ghost_recorder.best_score}", True,
                                      themes[current_theme]["accent_color"])
        screen.blit(ghost_text, (game_area.x + GAME_WIDTH - 120, game_area.y + 30))


# Enhanced death screen with new features
def draw_death_screen():
    """Modern Game Over Menu with stats"""
    overlay = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    screen.blit(overlay, (0, 0))

    # Main card
    card_rect = pygame.Rect(window_w // 2 - 250, window_h // 2 - 200, 500, 400)
    draw_card(screen, card_rect, None, None, themes[current_theme])

    # Game Over title
    title_text = font_large.render("GAME OVER", True, themes[current_theme]["highlight_color"])
    title_rect = title_text.get_rect(center=(window_w // 2, window_h // 2 - 120))
    screen.blit(title_text, title_rect)

    # Score display
    score_text = font_medium.render(f"Score: {score}", True, themes[current_theme]["text_color"])
    score_rect = score_text.get_rect(center=(window_w // 2, window_h // 2 - 60))
    screen.blit(score_text, score_rect)

    # High Score with new record indicator
    is_new_record = score >= HighScore and score > 0
    if is_new_record:
        hs_text = font_small.render(f"🏆 NEW RECORD: {HighScore}!", True, (255, 100, 100))
    else:
        hs_text = font_small.render(f"Best: {HighScore}", True, themes[current_theme]["text_color"])
    hs_rect = hs_text.get_rect(center=(window_w // 2, window_h // 2 - 20))
    screen.blit(hs_text, hs_rect)

    # NEW: Coins earned this game
    coins_earned = player_stats.get("coins_this_game", 0)
    if coins_earned > 0:
        coin_text = font_tiny.render(f"💰 +{coins_earned} coins earned!", True, (255, 215, 0))
        coin_rect = coin_text.get_rect(center=(window_w // 2, window_h // 2 + 10))
        screen.blit(coin_text, coin_rect)

    # Modern buttons
    button_y = window_h // 2 + 50
    restart_rect = pygame.Rect(window_w // 2 - 180, button_y, 120, 40)
    menu_rect = pygame.Rect(window_w // 2 - 50, button_y, 120, 40)
    stats_rect = pygame.Rect(window_w // 2 + 80, button_y, 120, 40)

    draw_modern_button(screen, restart_rect, "PLAY AGAIN", font_tiny, themes[current_theme]["highlight_color"])
    draw_modern_button(screen, menu_rect, "MAIN MENU", font_tiny, themes[current_theme]["accent_color"])
    draw_modern_button(screen, stats_rect, "STATS", font_tiny, (100, 100, 100))

    # Instructions
    instruction_text = font_tiny.render("SPACE: restart, B: menu, S: stats", True,
                                        themes[current_theme]["text_color"])
    instruction_rect = instruction_text.get_rect(center=(window_w // 2, window_h // 2 + 120))
    screen.blit(instruction_text, instruction_rect)

    return restart_rect, menu_rect, stats_rect


# Enhanced main menu
def draw_main_menu():
    """Modern Main Menu with enhanced features"""
    overlay = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 120))
    screen.blit(overlay, (0, 0))

    # Title with shadow effect
    title_text = font_large.render("FLAPPY BIRD", True, themes[current_theme]["highlight_color"])
    shadow_text = font_large.render("FLAPPY BIRD", True, (0, 0, 0, 100))

    title_rect = title_text.get_rect(center=(window_w // 2, 80))
    shadow_rect = title_rect.copy()
    shadow_rect.x += 3
    shadow_rect.y += 3

    screen.blit(shadow_text, shadow_rect)
    screen.blit(title_text, title_rect)

    # Subtitle
    subtitle_text = font_small.render("Enhanced Edition", True, themes[current_theme]["accent_color"])
    subtitle_rect = subtitle_text.get_rect(center=(window_w // 2, 120))
    screen.blit(subtitle_text, subtitle_rect)

    # Main buttons
    button_width = 200
    button_height = 45
    button_spacing = 15
    start_y = 180

    buttons = [
        ("START GAME", themes[current_theme]["highlight_color"]),
        ("SHOP", (255, 215, 0)),
        ("ACHIEVEMENTS", themes[current_theme]["accent_color"]),
        ("STATISTICS", (100, 150, 255)),
        ("SETTINGS", (150, 150, 150))
    ]

    button_rects = []
    for i, (text, color) in enumerate(buttons):
        button_rect = pygame.Rect(window_w // 2 - button_width // 2,
                                  start_y + i * (button_height + button_spacing),
                                  button_width, button_height)
        draw_modern_button(screen, button_rect, text, font_small, color)
        button_rects.append(button_rect)

    # Info panel
    info_y = start_y + len(buttons) * (button_height + button_spacing) + 20
    info_rect = pygame.Rect(50, info_y, window_w - 100, 120)
    draw_card(screen, info_rect, None, None, themes[current_theme])

    # High score and stats in info panel
    if HighScore > 0:
        hs_text = font_small.render(f"🏆 Best Score: {HighScore}", True, themes[current_theme]["text_color"])
        screen.blit(hs_text, (70, info_y + 20))

    # Coins
    coins_text = font_small.render(f"💰 Coins: {player_coins}", True, (255, 215, 0))
    screen.blit(coins_text, (70, info_y + 50))

    # Games played
    games_text = font_tiny.render(f"Games played: {player_stats['games_played']}", True,
                                  themes[current_theme]["text_color"])
    screen.blit(games_text, (70, info_y + 80))

    # Upload option
    if HighScore > 0:
        upload_text = font_tiny.render("Press U to upload score", True, themes[current_theme]["accent_color"])
        screen.blit(upload_text, (window_w - 200, info_y + 20))

    # Upload status
    if upload_status:
        status_card = pygame.Rect(window_w // 2 - 200, window_h - 60, 400, 40)
        draw_card(screen, status_card, None, None, themes[current_theme])
        status_text = font_tiny.render(upload_status, True, themes[current_theme]["text_color"])
        status_rect = status_text.get_rect(center=status_card.center)
        screen.blit(status_text, status_rect)

    return button_rects


# NEW: Shop screen
def draw_shop_screen():
    """Shop interface for themes and upgrades"""
    overlay = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    screen.blit(overlay, (0, 0))

    # Title
    title_text = font_large.render("THEME SHOP", True, themes[current_theme]["highlight_color"])
    title_rect = title_text.get_rect(center=(window_w // 2, 40))
    screen.blit(title_text, title_rect)

    # Coins display
    coins_text = font_medium.render(f"💰 {player_coins} Coins", True, (255, 215, 0))
    coins_rect = coins_text.get_rect(center=(window_w // 2, 80))
    screen.blit(coins_text, coins_rect)

    # Back button
    back_button = pygame.Rect(30, 20, 100, 35)
    draw_modern_button(screen, back_button, "← BACK", font_tiny, themes[current_theme]["accent_color"])

    # Theme grid
    theme_buttons = {}
    theme_names = list(themes.keys())
    themes_per_row = 3
    card_width = 200
    card_height = 150

    for i, theme_name in enumerate(theme_names):
        row = i // themes_per_row
        col = i % themes_per_row
        x_pos = window_w // 2 - 300 + col * 220
        y_pos = 120 + row * 170

        # Theme card
        card_rect = pygame.Rect(x_pos, y_pos, card_width, card_height)

        # Card color based on availability
        is_unlocked = theme_name in unlocked_themes
        is_current = theme_name == current_theme
        can_unlock, reason = can_unlock_theme(theme_name)

        if is_current:
            card_color = themes[current_theme]["highlight_color"]
        elif is_unlocked:
            card_color = themes[theme_name]["accent_color"]
        elif can_unlock:
            card_color = (100, 255, 100)
        else:
            card_color = (100, 100, 100)

        pygame.draw.rect(screen, themes[theme_name]["bg_color"], card_rect, border_radius=10)
        pygame.draw.rect(screen, card_color, card_rect, 3, border_radius=10)

        # Theme name
        name_text = font_small.render(theme_name, True, themes[theme_name]["text_color"])
        name_rect = name_text.get_rect(center=(x_pos + card_width // 2, y_pos + 20))
        screen.blit(name_text, name_rect)

        # Status text
        if is_current:
            status_text = font_tiny.render("EQUIPPED", True, (0, 255, 0))
        elif is_unlocked:
            status_text = font_tiny.render("OWNED", True, (100, 255, 100))
        elif can_unlock:
            price = themes[theme_name]["price"]
            status_text = font_tiny.render(f"BUY: {price} coins", True, (255, 255, 255))
        else:
            status_text = font_tiny.render("LOCKED", True, (255, 100, 100))

        status_rect = status_text.get_rect(center=(x_pos + card_width // 2, y_pos + 50))
        screen.blit(status_text, status_rect)

        # Requirement text for locked themes
        if not is_unlocked and not can_unlock:
            req_text = font_tiny.render(reason, True, (200, 200, 200))
            req_rect = req_text.get_rect(center=(x_pos + card_width // 2, y_pos + 80))
            screen.blit(req_text, req_rect)

        # Action button
        button_rect = pygame.Rect(x_pos + 25, y_pos + 100, card_width - 50, 30)

        if is_current:
            draw_modern_button(screen, button_rect, "EQUIPPED", font_tiny, (100, 100, 100))
        elif is_unlocked:
            draw_modern_button(screen, button_rect, "EQUIP", font_tiny, themes[theme_name]["highlight_color"])
        elif can_unlock:
            draw_modern_button(screen, button_rect, "PURCHASE", font_tiny, (100, 255, 100))
        else:
            draw_modern_button(screen, button_rect, "LOCKED", font_tiny, (100, 100, 100))

        theme_buttons[theme_name] = {
            'card': card_rect,
            'button': button_rect,
            'can_unlock': can_unlock,
            'is_unlocked': is_unlocked,
            'is_current': is_current
        }

    return back_button, theme_buttons


# NEW: Statistics screen
def draw_statistics_screen():
    """Statistics and achievements screen"""
    overlay = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    screen.blit(overlay, (0, 0))

    # Title
    title_text = font_large.render("STATISTICS", True, themes[current_theme]["highlight_color"])
    title_rect = title_text.get_rect(center=(window_w // 2, 30))
    screen.blit(title_text, title_rect)

    # Back button
    back_button = pygame.Rect(30, 20, 100, 35)
    draw_modern_button(screen, back_button, "← BACK", font_tiny, themes[current_theme]["accent_color"])

    # Stats cards
    card_width = 350
    card_height = 80

    # General stats
    stats_data = [
        ("Games Played", str(player_stats["games_played"])),
        ("Total Score", str(player_stats["total_score"])),
        ("Average Score", str(int(player_stats["total_score"] / max(1, player_stats["games_played"])))),
        ("Total Jumps", str(player_stats["total_jumps"])),
        ("Coins Collected", str(player_stats["total_coins_collected"])),
        ("Coins Earned", str(player_stats["coins_earned"]))
    ]

    for i, (stat_name, stat_value) in enumerate(stats_data):
        x_pos = 50 + (i % 2) * (card_width + 20)
        y_pos = 80 + (i // 2) * (card_height + 10)

        card_rect = pygame.Rect(x_pos, y_pos, card_width, card_height)
        draw_card(screen, card_rect, None, None, themes[current_theme])

        name_text = font_small.render(stat_name, True, themes[current_theme]["text_color"])
        screen.blit(name_text, (x_pos + 20, y_pos + 15))

        value_text = font_medium.render(stat_value, True, themes[current_theme]["highlight_color"])
        value_rect = value_text.get_rect(right=x_pos + card_width - 20, centery=y_pos + card_height // 2)
        screen.blit(value_text, value_rect)

    # Achievement section
    achievement_y = 350
    achievement_title = font_medium.render("ACHIEVEMENTS", True, themes[current_theme]["highlight_color"])
    screen.blit(achievement_title, (50, achievement_y))

    # Achievement grid
    unlocked_achievements = [k for k, v in achievements.items() if v["unlocked"]]
    total_achievements = len(achievements)

    progress_text = font_small.render(f"{len(unlocked_achievements)}/{total_achievements} Unlocked",
                                      True, themes[current_theme]["text_color"])
    screen.blit(progress_text, (50, achievement_y + 40))

    # Show some achievements
    y_offset = achievement_y + 80
    for i, (ach_id, ach_data) in enumerate(list(achievements.items())[:4]):
        if i >= 4:  # Show only first 4
            break

        ach_rect = pygame.Rect(50, y_offset + i * 40, window_w - 100, 35)

        if ach_data["unlocked"]:
            color = themes[current_theme]["highlight_color"]
            status = "✓"
        else:
            color = (100, 100, 100)
            status = "○"

        pygame.draw.rect(screen, color, ach_rect, 2, border_radius=5)

        ach_text = font_tiny.render(f"{status} {ach_data['icon']} {ach_data['name']}: {ach_data['description']}",
                                    True, themes[current_theme]["text_color"])
        screen.blit(ach_text, (ach_rect.x + 10, ach_rect.y + 8))

    return back_button


# Existing functions with enhancements
def draw_pause_screen():
    """Modern Pause Menu"""
    overlay = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    screen.blit(overlay, (0, 0))

    card_rect = pygame.Rect(window_w // 2 - 150, window_h // 2 - 100, 300, 200)
    draw_card(screen, card_rect, None, None, themes[current_theme])

    pause_text = font_large.render("PAUSED", True, themes[current_theme]["highlight_color"])
    pause_rect = pause_text.get_rect(center=(window_w // 2, window_h // 2 - 40))
    screen.blit(pause_text, pause_rect)

    continue_rect = pygame.Rect(window_w // 2 - 100, window_h // 2 + 10, 200, 40)
    menu_rect = pygame.Rect(window_w // 2 - 100, window_h // 2 + 60, 200, 40)

    draw_modern_button(screen, continue_rect, "CONTINUE", font_tiny, themes[current_theme]["highlight_color"])
    draw_modern_button(screen, menu_rect, "MAIN MENU", font_tiny, themes[current_theme]["accent_color"])

    return continue_rect, menu_rect


def draw_settings_screen():
    """Enhanced Settings Menu"""
    overlay = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    screen.blit(overlay, (0, 0))

    title_text = font_large.render("SETTINGS", True, themes[current_theme]["highlight_color"])
    title_rect = title_text.get_rect(center=(window_w // 2, 50))
    screen.blit(title_text, title_rect)

    back_button = pygame.Rect(50, 30, 120, 40)
    draw_modern_button(screen, back_button, "← BACK", font_tiny, themes[current_theme]["accent_color"])

    # Difficulty settings
    card_y = 120
    diff_card = pygame.Rect(50, card_y, window_w - 100, 100)
    draw_card(screen, diff_card, "Difficulty", None, themes[current_theme])

    diff_label = font_small.render("Difficulty:", True, themes[current_theme]["text_color"])
    screen.blit(diff_label, (70, card_y + 20))

    diff_buttons = []
    difficulties = [("NORMAL", "Normal"), ("HARD", "Schwer"), ("HARDCORE", "Hardcore")]
    for i, (display, value) in enumerate(difficulties):
        btn_rect = pygame.Rect(70 + i * 150, card_y + 50, 140, 35)
        color = themes[current_theme]["highlight_color"] if current_difficulty_preset == value else (100, 100, 100)
        draw_modern_button(screen, btn_rect, display, font_tiny, color)
        diff_buttons.append((btn_rect, value))

    # Display settings
    display_y = card_y + 120
    display_card = pygame.Rect(50, display_y, window_w - 100, 100)
    draw_card(screen, display_card, "Display", None, themes[current_theme])

    fs_label = font_small.render("Fullscreen:", True, themes[current_theme]["text_color"])
    screen.blit(fs_label, (70, display_y + 20))

    fs_button = pygame.Rect(70, display_y + 50, 140, 35)
    fs_color = themes[current_theme]["highlight_color"] if fullscreen else (100, 100, 100)
    draw_modern_button(screen, fs_button, "ON" if fullscreen else "OFF", font_tiny, fs_color)

    # Audio settings (NEW)
    audio_label = font_small.render("Music:", True, themes[current_theme]["text_color"])
    screen.blit(audio_label, (250, display_y + 20))

    music_button = pygame.Rect(250, display_y + 50, 140, 35)
    music_color = themes[current_theme]["highlight_color"] if music_enabled else (100, 100, 100)
    draw_modern_button(screen, music_button, "ON" if music_enabled else "OFF", font_tiny, music_color)

    return back_button, diff_buttons, fs_button, music_button


# Password dialog and admin functions (keeping existing)
def show_password_dialog():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    password = simpledialog.askstring("Admin Login", "Enter password:", show='*', parent=root)
    root.destroy()
    return password == "ndnet-asAdmin"


def show_admin_editor():
    """Enhanced admin editor with new features"""
    root = tk.Tk()
    root.title("Enhanced Admin Editor")
    root.geometry("600x700")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    # Variables for all settings
    score_var = tk.StringVar(value=str(score))
    highscore_var = tk.StringVar(value=str(HighScore))
    coins_var = tk.StringVar(value=str(player_coins))
    preset_var = tk.StringVar(value=current_difficulty_preset)

    # Achievement variables
    achievement_vars = {}
    for ach_id in achievements:
        achievement_vars[ach_id] = tk.BooleanVar(value=achievements[ach_id]["unlocked"])

    def save_values():
        global score, HighScore, player_coins, current_difficulty_preset

        try:
            score = max(0, int(score_var.get()))
            HighScore = max(0, int(highscore_var.get()))
            player_coins = max(0, int(coins_var.get()))
            current_difficulty_preset = preset_var.get()

            # Update achievements
            for ach_id, var in achievement_vars.items():
                achievements[ach_id]["unlocked"] = var.get()

            # Save to Firebase
            save_settings_async()
            save_extended_data_async()

            messagebox.showinfo("Success", "All values updated successfully!")
            root.destroy()
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers!")

    # UI Layout
    row = 0

    # Basic stats
    tk.Label(root, text="=== BASIC STATS ===", font=("Arial", 12, "bold")).grid(row=row, column=0, columnspan=2,
                                                                                pady=10)
    row += 1

    for label, var in [("Score:", score_var), ("High Score:", highscore_var), ("Coins:", coins_var)]:
        tk.Label(root, text=label).grid(row=row, column=0, padx=10, pady=5, sticky="e")
        tk.Entry(root, textvariable=var).grid(row=row, column=1, padx=10, pady=5)
        row += 1

    # Difficulty
    tk.Label(root, text="Difficulty:").grid(row=row, column=0, padx=10, pady=5, sticky="e")
    tk.OptionMenu(root, preset_var, *difficulty_presets.keys()).grid(row=row, column=1, padx=10, pady=5)
    row += 1

    # Achievements section
    tk.Label(root, text="=== ACHIEVEMENTS ===", font=("Arial", 12, "bold")).grid(row=row, column=0, columnspan=2,
                                                                                 pady=(20, 10))
    row += 1

    for ach_id, ach_data in achievements.items():
        tk.Checkbutton(root, text=f"{ach_data['name']} - {ach_data['description']}",
                       variable=achievement_vars[ach_id]).grid(row=row, column=0, columnspan=2, sticky="w", padx=10,
                                                               pady=2)
        row += 1

    # Save button
    tk.Button(root, text="Save All Changes", command=save_values,
              bg="#4CAF50", fg="white", font=("Arial", 12, "bold")).grid(row=row, column=0, columnspan=2, pady=20)

    # Center window
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f'+{x}+{y}')

    root.mainloop()


# Enhanced Pipe class
class Pipe:
    def __init__(self, x, height, gap, velocity):
        self.x = x
        self.height = height
        self.gap = gap
        self.velocity = velocity
        self.scored = False
        self.coin = None

        # NEW: Sometimes add a coin
        if random.random() < 0.3:  # 30% chance
            coin_x = x + pipe_up_img.get_width() // 2 - coin_img.get_width() // 2
            coin_y = height + gap // 2 - coin_img.get_height() // 2
            self.coin = Coin(coin_x, coin_y)

        self.top_rect = pygame.Rect(
            max(0, min(self.x, GAME_WIDTH - pipe_down_img.get_width())),
            0 - pipe_down_img.get_height() + self.height,
            pipe_down_img.get_width(),
            pipe_down_img.get_height()
        )
        self.bottom_rect = pygame.Rect(
            max(0, min(self.x, GAME_WIDTH - pipe_up_img.get_width())),
            self.height + self.gap,
            pipe_up_img.get_width(),
            pipe_up_img.get_height()
        )

    def update(self):
        self.x -= self.velocity
        self.top_rect.x = max(0, min(self.x, GAME_WIDTH - pipe_down_img.get_width()))
        self.bottom_rect.x = max(0, min(self.x, GAME_WIDTH - pipe_up_img.get_width()))

        # Update coin if present
        if self.coin:
            self.coin.x = self.x + pipe_up_img.get_width() // 2 - coin_img.get_width() // 2
            self.coin.update()

    def draw(self):
        if self.x + pipe_up_img.get_width() > 0 and self.x < GAME_WIDTH:
            top_y = game_area.y + 0 - pipe_down_img.get_height() + self.height
            screen.blit(pipe_down_img, (game_area.x + self.x, top_y))

            bottom_y = game_area.y + self.height + self.gap
            screen.blit(pipe_up_img, (game_area.x + self.x, bottom_y))

            # Draw coin if present
            if self.coin and not self.coin.collected:
                self.coin.draw(screen)


def check_collision(player, pipes):
    """Enhanced collision detection with coins"""
    global player_coins, player_stats

    if player.rect.top <= 0:
        return True

    if player.rect.bottom >= ACTUAL_PLAY_HEIGHT:
        return True

    for pipe in pipes:
        if pipe.x + pipe_up_img.get_width() > 0 and pipe.x < GAME_WIDTH:
            # Check coin collection
            if pipe.coin and not pipe.coin.collected:
                coin_rect = pipe.coin.get_rect()
                if player.rect.colliderect(coin_rect):
                    pipe.coin.collected = True
                    player_coins += 1
                    player_stats["total_coins_collected"] += 1
                    player_stats["coins_this_game"] = player_stats.get("coins_this_game", 0) + 1
                    pygame.mixer.Sound.play(coin_sfx)
                    particle_system.add_coin_particles(pipe.coin.x + coin_img.get_width() // 2,
                                                       pipe.coin.y + coin_img.get_height() // 2)

            # Pipe collision
            offset_top_x = pipe.top_rect.left - player.rect.left
            offset_top_y = pipe.top_rect.top - player.rect.top
            offset_bottom_x = pipe.bottom_rect.left - player.rect.left
            offset_bottom_y = pipe.bottom_rect.top - player.rect.top

            if player.mask.overlap(pipe_down_mask, (offset_top_x, offset_top_y)):
                return True
            if player.mask.overlap(pipe_up_mask, (offset_bottom_x, offset_bottom_y)):
                return True

    return False


def update_difficulty():
    global difficulty_level, last_difficulty_update

    preset = difficulty_presets[current_difficulty_preset]

    if score >= last_difficulty_update + preset["difficulty_increase_interval"]:
        difficulty_level += 1
        last_difficulty_update = score

    current_velocity = base_pipe_velocity * (1 + preset["velocity_multiplier"] * difficulty_level)
    current_gap = max(preset["min_gap"], base_gap - (preset["gap_decrease"] * difficulty_level))
    current_spacing = max(preset["min_spacing"],
                          preset["pipe_spacing"] - (preset["spacing_decrease"] * difficulty_level))

    return current_velocity, current_gap, current_spacing


def reset_game():
    """Enhanced game reset with new features"""
    global score, has_moved, difficulty_level, last_difficulty_update, coins, game_frame_counter

    score = 0
    has_moved = False
    difficulty_level = 0
    last_difficulty_update = 0
    coins.clear()
    game_frame_counter = 0

    # Reset coins earned this game
    player_stats["coins_this_game"] = 0

    # Update stats
    player_stats["games_played"] += 1
    player_stats["theme_usage"][current_theme] = player_stats["theme_usage"].get(current_theme, 0) + 1
    player_stats["difficulty_usage"][current_difficulty_preset] = player_stats["difficulty_usage"].get(
        current_difficulty_preset, 0) + 1

    # Start ghost recording
    ghost_recorder.start_recording()

    preset = difficulty_presets[current_difficulty_preset]
    pipe_spacing = preset["pipe_spacing"]

    player = Player(GAME_WIDTH // 4, GAME_HEIGHT // 2)

    pipes = []
    for i in range(3):
        x_pos = GAME_WIDTH + (i * pipe_spacing)
        min_height = 50
        max_height = ACTUAL_PLAY_HEIGHT - base_gap - 50
        random_height = random.randint(min_height, max_height)
        pipes.append(Pipe(x_pos, random_height, base_gap, base_pipe_velocity))

    return player, pipes


def toggle_fullscreen():
    global fullscreen, window_w, window_h, screen, game_area

    fullscreen = not fullscreen
    if fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        window_w, window_h = screen.get_size()
        game_area.x = (window_w - GAME_WIDTH) // 2
        game_area.y = (window_h - GAME_HEIGHT) // 2
    else:
        window_w, window_h = 800, 600
        screen = pygame.display.set_mode((window_w, window_h))
        game_area.x = (window_w - GAME_WIDTH) // 2
        game_area.y = (window_h - GAME_HEIGHT) // 2

    save_settings_async()


def handle_game_over():
    """Handle end of game with all new features"""
    global player_stats

    # Update stats
    player_stats["total_score"] += score
    if score > player_stats.get("best_streak", 0):
        player_stats["best_streak"] = score

    # Check for new high score
    if score > HighScore:
        update_high_score(score)

    # Finish ghost recording
    ghost_recorder.finish_recording(score)

    # Add death particles
    particle_system.add_death_particles(player.x + player_img.get_width() // 2, player.y + player_img.get_height() // 2)

    # Award coins based on score
    coins_earned = max(1, score // 5)  # 1 coin per 5 points
    player_coins += coins_earned
    player_stats["coins_earned"] += coins_earned
    player_stats["coins_this_game"] += coins_earned

    # Check achievements
    check_achievements()

    # Save extended data
    save_extended_data_async()


def game():
    """Enhanced main game loop"""
    global game_state, HighScore, score, has_moved, window_focused, upload_status, dt
    global player_img, pipe_up_img, pipe_down_img, ground_img, bg_img, current_theme
    global pipe_up_mask, pipe_down_mask, theme_images, theme_masks, game_frame_counter
    global music_enabled, current_music

    bg_x_pos = 0
    ground_x_pos = 0

    player, pipes = reset_game()

    # UI button variables
    main_menu_buttons = None
    death_screen_buttons = None
    pause_screen_buttons = None
    settings_buttons = None
    shop_buttons = None
    stats_back_button = None

    # Game timing
    last_update_time = time.time()

    while True:
        current_time = time.time()
        dt = clock.tick(fps) / 1000.0
        mouse_pos = pygame.mouse.get_pos()
        game_frame_counter += 1

        # Update playtime
        player_stats["total_playtime"] += dt

        current_velocity, current_gap, current_spacing = update_difficulty()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.ACTIVEEVENT:
                if event.gain == 0:
                    window_focused = False
                    if game_state == 2:
                        game_state = 4
                else:
                    window_focused = True

            if event.type == pygame.KEYDOWN:
                # Admin panel
                if event.key == pygame.K_F12:
                    if show_password_dialog():
                        show_admin_editor()

                # Main menu
                if game_state == 1:
                    if event.key == pygame.K_SPACE:
                        player, pipes = reset_game()
                        game_state = 2
                    elif event.key == pygame.K_s:
                        game_state = 6  # Settings
                    elif event.key == pygame.K_a:
                        game_state = 8  # Achievements/Stats
                    elif event.key == pygame.K_h:
                        game_state = 9  # Shop
                    elif event.key == pygame.K_u and HighScore > 0:
                        if show_upload_dialog():
                            game_state = 5

                # Game state
                elif game_state == 2:
                    has_moved = True
                    if event.key == pygame.K_SPACE:
                        pygame.mixer.Sound.play(woosh_sfx)
                        player.jump()
                    elif event.key == pygame.K_p:
                        game_state = 4
                    elif event.key == pygame.K_ESCAPE or event.key == pygame.K_b:
                        game_state = 1

                # Death screen
                elif game_state == 3:
                    if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        player, pipes = reset_game()
                        game_state = 2
                    elif event.key == pygame.K_b:
                        game_state = 1
                    elif event.key == pygame.K_s:
                        game_state = 8  # Stats

                # Pause screen
                elif game_state == 4:
                    if event.key == pygame.K_SPACE or event.key == pygame.K_p:
                        game_state = 2
                    elif event.key == pygame.K_b:
                        game_state = 1

                # Upload confirmation
                elif game_state == 5:
                    if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                        game_state = 1

                # Settings
                elif game_state == 6:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_b:
                        game_state = 1

                # Stats screen
                elif game_state == 8:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_b:
                        game_state = 1

                # Shop screen
                elif game_state == 9:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_b:
                        game_state = 1

            # Mouse clicks
            if event.type == pygame.MOUSEBUTTONDOWN:
                # Main menu
                if game_state == 1 and main_menu_buttons:
                    start_rect, shop_rect, achievements_rect, stats_rect, settings_rect = main_menu_buttons
                    if start_rect.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        player, pipes = reset_game()
                        game_state = 2
                        has_moved = True
                    elif shop_rect.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        game_state = 9
                    elif achievements_rect.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        game_state = 8
                    elif stats_rect.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        game_state = 8
                    elif settings_rect.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        game_state = 6

                # Game
                elif game_state == 2:
                    pygame.mixer.Sound.play(woosh_sfx)
                    player.jump()

                # Death screen
                elif game_state == 3 and death_screen_buttons:
                    restart_rect, menu_rect, stats_rect = death_screen_buttons
                    if restart_rect.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        player, pipes = reset_game()
                        game_state = 2
                        has_moved = True
                    elif menu_rect.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        game_state = 1
                    elif stats_rect.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        game_state = 8

                # Pause screen
                elif game_state == 4 and pause_screen_buttons:
                    continue_rect, menu_rect = pause_screen_buttons
                    if continue_rect.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        game_state = 2
                    elif menu_rect.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        game_state = 1

                # Settings screen
                elif game_state == 6 and settings_buttons:
                    back_button, diff_buttons, fs_button, music_button = settings_buttons

                    if back_button.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        game_state = 1

                    # Difficulty buttons
                    for btn_rect, value in diff_buttons:
                        if btn_rect.collidepoint(mouse_pos):
                            pygame.mixer.Sound.play(select_sfx)
                            change_difficulty(value)

                    # Fullscreen button
                    if fs_button.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        toggle_fullscreen()

                    # Music button
                    if music_button.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        music_enabled = not music_enabled
                        save_settings_async()

                # Stats screen
                elif game_state == 8 and stats_back_button:
                    if stats_back_button.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        game_state = 1

                # Shop screen
                elif game_state == 9 and shop_buttons:
                    back_button, theme_buttons = shop_buttons

                    if back_button.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        game_state = 1
                    else:
                        for theme_name, button_data in theme_buttons.items():
                            if button_data['button'].collidepoint(mouse_pos):
                                pygame.mixer.Sound.play(select_sfx)

                                if button_data['is_current']:
                                    continue  # Already equipped
                                elif button_data['is_unlocked']:
                                    # Equip theme
                                    change_theme(theme_name)
                                    # Update theme images
                                    clear_filter_cache()
                                    theme_images, theme_masks = load_theme_images(current_theme)
                                    player_img = theme_images["player"]
                                    pipe_up_img = theme_images["pipe_up"]
                                    pipe_down_img = theme_images["pipe_down"]
                                    ground_img = theme_images["ground"]
                                    bg_img = theme_images["background"]
                                    pipe_up_mask = theme_masks["pipe_up_mask"]
                                    pipe_down_mask = theme_masks["pipe_down_mask"]
                                    player.rotated_image = player_img
                                    player.mask = pygame.mask.from_surface(player_img)
                                elif button_data['can_unlock']:
                                    # Purchase theme
                                    if unlock_theme(theme_name):
                                        # Successfully purchased
                                        pass

        # Game Logic
        if game_state == 2 and has_moved:
            player.update()

            # Record ghost position
            ghost_recorder.record_position(player.x, player.y)

            # Check collision
            if check_collision(player, pipes):
                handle_game_over()
                pygame.mixer.Sound.play(slap_sfx)
                game_state = 3

            # Update pipes
            for pipe in pipes:
                pipe.velocity = current_velocity
                pipe.update()

            # Remove old pipes and add new ones
            if pipes and pipes[0].x < -pipe_up_img.get_width():
                pipes.pop(0)
                last_pipe_x = pipes[-1].x if pipes else GAME_WIDTH
                min_height = 50
                max_height = ACTUAL_PLAY_HEIGHT - current_gap - 50
                random_height = random.randint(min_height, max_height)
                pipes.append(Pipe(last_pipe_x + current_spacing, random_height, current_gap, current_velocity))

            # Score pipes
            for pipe in pipes:
                if not pipe.scored and pipe.x + pipe_up_img.get_width() < player.x:
                    score += 1
                    pygame.mixer.Sound.play(score_sfx)
                    pipe.scored = True

                    # Add score particles
                    particle_system.add_score_particles(pipe.x + pipe_up_img.get_width(),
                                                        pipe.height + pipe.gap // 2)

                    # Check achievements on score
                    check_achievements()

            # Update background
            bg_x_pos -= bg_scroll_spd
            ground_x_pos -= ground_scroll_spd

            if bg_x_pos <= -bg_width:
                bg_x_pos = 0
            if ground_x_pos <= -bg_width:
                ground_x_pos = 0

        # Update particles
        particle_system.update()

        # Drawing
        screen.fill(themes[current_theme]["bg_color"])

        # Draw game area (only during gameplay)
        if game_state == 2:
            pygame.draw.rect(screen, (50, 50, 50), game_area, 2)

            screen.set_clip(game_area)
            screen.blit(bg_img, (game_area.x + bg_x_pos, game_area.y))
            screen.blit(bg_img, (game_area.x + bg_x_pos + bg_width, game_area.y))
            screen.blit(ground_img, (game_area.x + ground_x_pos, game_area.y + ACTUAL_PLAY_HEIGHT))
            screen.blit(ground_img, (game_area.x + ground_x_pos + bg_width, game_area.y + ACTUAL_PLAY_HEIGHT))

            # Draw ghost
            ghost_recorder.draw_ghost(screen, game_frame_counter)

            # Draw pipes
            for pipe in pipes:
                pipe.draw()

            # Draw player
            player.draw()

            # Draw particles
            particle_system.draw(screen)

            screen.set_clip(None)
            scoreboard()

        # Draw sync status
        draw_sync_status()

        # Draw achievement notification
        draw_achievement_notification()

        # Menu overlays
        if game_state == 1:
            main_menu_buttons = draw_main_menu()
        elif game_state == 3:
            death_screen_buttons = draw_death_screen()
        elif game_state == 4:
            pause_screen_buttons = draw_pause_screen()
        elif game_state == 5:
            # Upload confirmation
            overlay = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))

            card_rect = pygame.Rect(window_w // 2 - 200, window_h // 2 - 50, 400, 100)
            draw_card(screen, card_rect, None, None, themes[current_theme])

            status_text = font_small.render(upload_status, True, themes[current_theme]["text_color"])
            status_rect = status_text.get_rect(center=(window_w // 2, window_h // 2 - 10))
            screen.blit(status_text, status_rect)

            continue_text = font_tiny.render("Press SPACE to continue", True, themes[current_theme]["text_color"])
            continue_rect = continue_text.get_rect(center=(window_w // 2, window_h // 2 + 20))
            screen.blit(continue_text, continue_rect)

        elif game_state == 6:
            settings_buttons = draw_settings_screen()
        elif game_state == 8:
            stats_back_button = draw_statistics_screen()
        elif game_state == 9:
            shop_buttons = draw_shop_screen()

        pygame.display.flip()


if __name__ == "__main__":
    game()