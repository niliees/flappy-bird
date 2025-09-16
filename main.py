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

from pygame import rect


# Funktion für Ressourcenpfade (wichtig für PyInstaller)
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    path = os.path.join(base_path, relative_path)

    if not os.path.exists(path):
        # Versuche, die Datei im aktuellen Verzeichnis zu finden
        current_dir_path = os.path.join(os.path.abspath("."), relative_path)
        if os.path.exists(current_dir_path):
            return current_dir_path

        # Wenn die Datei nirgends gefunden wurde, gib eine aussagekräftige Fehlermeldung aus
        raise FileNotFoundError(f"Datei '{relative_path}' konnte nicht gefunden werden.")

    return path


# Verbesserte Filter-Funktionen mit präziser Pixel-Manipulation
def apply_hsl_filter(surface, hue_shift=0, saturation_mult=1.0, lightness_mult=1.0):
    """Erweiterte HSL-Filter-Funktion für präzise Farbmanipulation"""
    # Konvertiere Surface zu Pixel-Array
    arr = pygame.surfarray.array3d(surface).astype(float)
    h, w, c = arr.shape

    # RGB zu HSL konvertieren
    r, g, b = arr[:, :, 0] / 255.0, arr[:, :, 1] / 255.0, arr[:, :, 2] / 255.0

    max_val = np.maximum(np.maximum(r, g), b)
    min_val = np.minimum(np.minimum(r, g), b)
    diff = max_val - min_val

    # Lightness
    l = (max_val + min_val) / 2.0

    # Saturation
    s = np.where(diff == 0, 0, np.where(l < 0.5, diff / (max_val + min_val), diff / (2.0 - max_val - min_val)))

    # Hue
    h_val = np.zeros_like(r)
    mask_r = (max_val == r) & (diff != 0)
    mask_g = (max_val == g) & (diff != 0)
    mask_b = (max_val == b) & (diff != 0)

    h_val[mask_r] = (60 * ((g[mask_r] - b[mask_r]) / diff[mask_r]) + 360) % 360
    h_val[mask_g] = (60 * ((b[mask_g] - r[mask_g]) / diff[mask_g]) + 120) % 360
    h_val[mask_b] = (60 * ((r[mask_b] - g[mask_b]) / diff[mask_b]) + 240) % 360

    # Filter anwenden
    h_val = (h_val + hue_shift) % 360
    s = np.clip(s * saturation_mult, 0, 1)
    l = np.clip(l * lightness_mult, 0, 1)

    # HSL zurück zu RGB
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

    # Zurück zur Surface
    new_arr = np.stack([r_new, g_new, b_new], axis=2).astype(np.uint8)
    new_surface = pygame.surfarray.make_surface(new_arr)

    # Alpha-Kanal beibehalten
    if surface.get_flags() & pygame.SRCALPHA:
        new_surface = new_surface.convert_alpha()
        alpha_arr = pygame.surfarray.array_alpha(surface)
        pygame.surfarray.pixels_alpha(new_surface)[:] = alpha_arr

    return new_surface


def apply_advanced_filter(surface, contrast=1.0, brightness=0, saturation=1.0, hue_shift=0, gamma=1.0):
    """Erweiterte Filter-Funktion mit mehreren Parametern"""
    try:
        # Pixel-Array erstellen
        arr = pygame.surfarray.array3d(surface).astype(float)

        # Gamma-Korrektur
        if gamma != 1.0:
            arr = np.power(arr / 255.0, gamma) * 255.0

        # Kontrast und Helligkeit
        arr = arr * contrast + brightness
        arr = np.clip(arr, 0, 255)

        # Zu Surface zurück konvertieren
        new_surface = pygame.surfarray.make_surface(arr.astype(np.uint8))

        # HSL-Filter anwenden wenn nötig
        if saturation != 1.0 or hue_shift != 0:
            new_surface = apply_hsl_filter(new_surface, hue_shift, saturation, 1.0)

        # Alpha-Kanal beibehalten
        if surface.get_flags() & pygame.SRCALPHA:
            new_surface = new_surface.convert_alpha()
            try:
                alpha_arr = pygame.surfarray.array_alpha(surface)
                pygame.surfarray.pixels_alpha(new_surface)[:] = alpha_arr
            except:
                # Fallback wenn Alpha-Handling fehlschlägt
                new_surface.set_alpha(surface.get_alpha())

        return new_surface
    except Exception:
        # Fallback zu einfacher Kopie wenn Filter fehlschlägt
        return surface.copy()


# Spezifische Theme-Filter
def apply_night_filter(surface):
    """Nacht-Filter: dunkler, bläulich, hoher Kontrast"""
    return apply_advanced_filter(
        surface,
        contrast=1.3,
        brightness=-30,
        saturation=0.7,
        hue_shift=180,  # Richtung Blau
        gamma=0.8
    )


def apply_desert_filter(surface):
    """Wüsten-Filter: wärmer, orange/gelb, heller"""
    return apply_advanced_filter(
        surface,
        contrast=1.1,
        brightness=20,
        saturation=1.3,
        hue_shift=30,  # Richtung Orange/Gelb
        gamma=1.2
    )


def apply_retro_filter(surface):
    """Retro-Filter: grünlich, niedriger Kontrast, dunkel"""
    return apply_advanced_filter(
        surface,
        contrast=0.8,
        brightness=-10,
        saturation=0.6,
        hue_shift=120,  # Richtung Grün
        gamma=0.9
    )


def apply_neon_filter(surface):
    """Neon-Filter: hohe Sättigung, hoher Kontrast, psychedelisch"""
    return apply_advanced_filter(
        surface,
        contrast=1.5,
        brightness=10,
        saturation=2.0,
        hue_shift=280,  # Richtung Magenta
        gamma=1.1
    )


def apply_vintage_filter(surface):
    """Vintage-Filter: Sepia-ähnlich, weicher Kontrast"""
    return apply_advanced_filter(
        surface,
        contrast=0.9,
        brightness=-5,
        saturation=0.4,
        hue_shift=40,  # Warme Töne
        gamma=1.1
    )


def apply_monochrome_filter(surface):
    """Schwarz-Weiß Filter mit leichtem Blauton"""
    return apply_advanced_filter(
        surface,
        contrast=1.2,
        brightness=0,
        saturation=0.0,  # Keine Sättigung = Graustufen
        hue_shift=0,
        gamma=1.0
    )


# Moderne UI Helper-Funktionen (subtiler)
def draw_modern_button(surface, rect, text, font, color, hover=False, pressed=False):
    """Zeichnet einen modernen Button mit subtilen Effekten"""
    # Schatten
    shadow_rect = rect.copy()
    shadow_rect.x += 2
    shadow_rect.y += 2
    pygame.draw.rect(surface, (0, 0, 0, 30), shadow_rect, border_radius=8)

    # Button-Farben
    if pressed:
        button_color = tuple(max(0, c - 20) for c in color)
    elif hover:
        button_color = tuple(min(255, c + 15) for c in color)
    else:
        button_color = color

    # Hauptbutton
    pygame.draw.rect(surface, button_color, rect, border_radius=8)

    # Dezenter Rand
    border_color = tuple(max(0, c - 40) for c in button_color)
    pygame.draw.rect(surface, border_color, rect, width=2, border_radius=8)

    # Text
    text_color = (255, 255, 255) if sum(color) < 400 else (0, 0, 0)
    text_surface = font.render(text, True, text_color)
    text_rect = text_surface.get_rect(center=rect.center)
    if pressed:
        text_rect.x += 1
        text_rect.y += 1

    surface.blit(text_surface, text_rect)


def draw_card(surface, rect, title, content, theme_colors):
    """Zeichnet eine moderne Karte mit Titel und Inhalt"""
    # Schatten
    shadow_rect = rect.copy()
    shadow_rect.x += 3
    shadow_rect.y += 3
    pygame.draw.rect(surface, (0, 0, 0, 20), shadow_rect, border_radius=12)

    # Karten-Hintergrund
    card_color = (240, 240, 245) if sum(theme_colors["bg_color"]) > 400 else (40, 40, 50)
    pygame.draw.rect(surface, card_color, rect, border_radius=12)

    # Dezenter Rand
    border_color = theme_colors["highlight_color"]
    pygame.draw.rect(surface, border_color, rect, width=2, border_radius=12)

    # Titel
    if title:
        title_color = theme_colors["text_color"]
        title_surface = font_small.render(title, True, title_color)
        title_pos = (rect.x + 20, rect.y + 15)
        surface.blit(title_surface, title_pos)


# Initialize Game
pygame.init()

# Globale Variablen
game_state = 1  # Starte direkt im Hauptmenü
score = 0
has_moved = False
HighScore = 0
window_focused = True
upload_status = ""

# Fester Spielbereich (400x600) - NUR für Gameplay
GAME_WIDTH, GAME_HEIGHT = 400, 600
game_area = pygame.Rect(0, 0, GAME_WIDTH, GAME_HEIGHT)

# Boden-Höhe für präzise Kollisionserkennung
GROUND_HEIGHT = 64
ACTUAL_PLAY_HEIGHT = GAME_HEIGHT - GROUND_HEIGHT

# Schwierigkeits-Variablen
base_pipe_velocity = 2.4
base_gap = 220
difficulty_level = 0
last_difficulty_update = 0

# Globale Variablen für Schwierigkeitsparameter
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

# Erweiterte Themes
themes = {
    "Classic": {
        "bg_color": (113, 197, 207),
        "text_color": (0, 0, 0),
        "highlight_color": (255, 215, 0),
        "accent_color": (255, 165, 0),
        "filter": None
    },
    "Night": {
        "bg_color": (15, 15, 35),
        "text_color": (220, 230, 255),
        "highlight_color": (100, 150, 255),
        "accent_color": (50, 100, 200),
        "filter": apply_night_filter
    },
    "Desert": {
        "bg_color": (245, 210, 150),
        "text_color": (80, 40, 0),
        "highlight_color": (255, 140, 0),
        "accent_color": (200, 100, 50),
        "filter": apply_desert_filter
    },
    "Retro": {
        "bg_color": (30, 50, 30),
        "text_color": (100, 255, 100),
        "highlight_color": (150, 255, 150),
        "accent_color": (50, 200, 50),
        "filter": apply_retro_filter
    },
    "Neon": {
        "bg_color": (10, 5, 25),
        "text_color": (255, 100, 255),
        "highlight_color": (0, 255, 255),
        "accent_color": (255, 0, 255),
        "filter": apply_neon_filter
    },
    "Vintage": {
        "bg_color": (200, 180, 140),
        "text_color": (60, 40, 20),
        "highlight_color": (180, 120, 60),
        "accent_color": (150, 100, 50),
        "filter": apply_vintage_filter
    },
    "Mono": {
        "bg_color": (80, 80, 80),
        "text_color": (255, 255, 255),
        "highlight_color": (200, 200, 200),
        "accent_color": (150, 150, 150),
        "filter": apply_monochrome_filter
    }
}

current_theme = "Classic"

# Basis-Bildpfade
base_images = {
    "background": "images/background.png",
    "ground": "images/ground.png",
    "player": "images/player.png",
    "pipe_up": "images/pipe_up.png",
    "pipe_down": "images/pipe_down.png"
}


# Einstellungen laden
def load_settings():
    global current_theme, current_difficulty_preset, fullscreen, HighScore
    try:
        with open(resource_path("settings.json"), "r") as f:
            settings = json.load(f)
            current_theme = settings.get("theme", "Classic")
            current_difficulty_preset = settings.get("difficulty", "Normal")
            fullscreen = settings.get("fullscreen", False)
            HighScore = settings.get("highscore", 0)
    except (FileNotFoundError, json.JSONDecodeError):
        pass


def save_settings():
    settings = {
        "theme": current_theme,
        "difficulty": current_difficulty_preset,
        "fullscreen": fullscreen,
        "highscore": HighScore
    }
    with open(resource_path("settings.json"), "w") as f:
        json.dump(settings, f)


load_settings()

# Window Setup - KORRIGIERT auf 800x600
if fullscreen:
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    window_w, window_h = screen.get_size()
    # Zentriere das Spielbereich
    game_area.x = (window_w - GAME_WIDTH) // 2
    game_area.y = (window_h - GAME_HEIGHT) // 2
else:
    window_w, window_h = 800, 600  # KORRIGIERTE Fenstergröße
    screen = pygame.display.set_mode((window_w, window_h))
    # Zentriere das Spielbereich
    game_area.x = (window_w - GAME_WIDTH) // 2
    game_area.y = (window_h - GAME_HEIGHT) // 2

pygame.display.set_caption("Flappy Bird")

# Icon laden
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

# Basis-Bilder laden
base_loaded_images = {}
for key, path in base_images.items():
    base_loaded_images[key] = pygame.image.load(resource_path(path))


# Theme-basierte Bilder UND Masken laden mit Filtern
def load_theme_images(theme_name):
    theme = themes[theme_name]
    filter_func = theme["filter"]

    images = {}
    masks = {}

    for key, base_image in base_loaded_images.items():
        if filter_func:
            filtered_image = filter_func(base_image)
            images[f"{key}_img"] = filtered_image
            masks[f"{key}_mask"] = pygame.mask.from_surface(filtered_image)
        else:
            images[f"{key}_img"] = base_image.copy()
            masks[f"{key}_mask"] = pygame.mask.from_surface(base_image)

    return images, masks


# Initiale Bilder und Masken laden
theme_images, theme_masks = load_theme_images(current_theme)
player_img = theme_images["player_img"]
pipe_up_img = theme_images["pipe_up_img"]
pipe_down_img = theme_images["pipe_down_img"]
ground_img = theme_images["ground_img"]
bg_img = theme_images["background_img"]

# Masken für die Rohre (jetzt theme-spezifisch)
pipe_up_mask = theme_masks["pipe_up_mask"]
pipe_down_mask = theme_masks["pipe_down_mask"]

bg_width = bg_img.get_width()

# Variable Setup
bg_scroll_spd = 1
ground_scroll_spd = 2


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


def scoreboard():
    show_score = font.render(str(score), True, themes[current_theme]["text_color"])
    score_rect = show_score.get_rect(center=(game_area.x + GAME_WIDTH // 2, game_area.y + 485))
    screen.blit(show_score, score_rect)

    show_HighScore = font_small.render(f"Highscore: {HighScore}", True, themes[current_theme]["text_color"])
    HighScore_rect = show_HighScore.get_rect(center=(game_area.x + GAME_WIDTH // 4, game_area.y + 30))
    screen.blit(show_HighScore, HighScore_rect)


def draw_death_screen():
    """Modernes Game Over Menü - nutzt VOLLBILD (800x600)"""
    # Halbtransparenter Overlay
    overlay = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    screen.blit(overlay, (0, 0))

    # Hauptkarte zentriert
    card_rect = pygame.Rect(window_w // 2 - 200, window_h // 2 - 150, 400, 300)
    draw_card(screen, card_rect, None, None, themes[current_theme])

    # Game Over Titel
    title_text = font_large.render("GAME OVER", True, themes[current_theme]["highlight_color"])
    title_rect = title_text.get_rect(center=(window_w // 2, window_h // 2 - 80))
    screen.blit(title_text, title_rect)

    # Score Anzeige
    score_text = font_medium.render(f"Score: {score}", True, themes[current_theme]["text_color"])
    score_rect = score_text.get_rect(center=(window_w // 2, window_h // 2 - 20))
    screen.blit(score_text, score_rect)

    # High Score mit New Record Indikator
    is_new_record = score >= HighScore and score > 0
    if is_new_record:
        hs_text = font_small.render(f"NEW RECORD: {HighScore}!", True, (255, 100, 100))
    else:
        hs_text = font_small.render(f"Best: {HighScore}", True, themes[current_theme]["text_color"])
    hs_rect = hs_text.get_rect(center=(window_w // 2, window_h // 2 + 20))
    screen.blit(hs_text, hs_rect)

    # Moderne Buttons
    restart_rect = pygame.Rect(window_w // 2 - 160, window_h // 2 + 70, 150, 45)
    menu_rect = pygame.Rect(window_w // 2 + 10, window_h // 2 + 70, 150, 45)

    draw_modern_button(screen, restart_rect, "PLAY AGAIN", font_tiny, themes[current_theme]["highlight_color"])
    draw_modern_button(screen, menu_rect, "MAIN MENU", font_tiny, themes[current_theme]["accent_color"])

    # Instruktionen
    instruction_text = font_tiny.render("Click buttons, SPACE to restart, B for menu", True,
                                        themes[current_theme]["text_color"])
    instruction_rect = instruction_text.get_rect(center=(window_w // 2, window_h // 2 + 140))
    screen.blit(instruction_text, instruction_rect)

    return restart_rect, menu_rect


def draw_main_menu():
    """Modernes Hauptmenü - nutzt VOLLBILD (800x600)"""
    # Hintergrund-Overlay
    overlay = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 120))
    screen.blit(overlay, (0, 0))

    # Titel
    title_text = font_large.render("FLAPPY BIRD", True, themes[current_theme]["highlight_color"])
    title_rect = title_text.get_rect(center=(window_w // 2, 100))
    screen.blit(title_text, title_rect)

    # Hauptbuttons zentriert
    button_width = 250
    button_height = 50
    button_spacing = 20
    start_y = window_h // 2 - 50

    buttons = [
        ("START GAME", themes[current_theme]["highlight_color"]),
        ("SETTINGS", themes[current_theme]["accent_color"]),
        ("THEMES", tuple(max(0, c - 30) for c in themes[current_theme]["highlight_color"]))
    ]

    button_rects = []
    for i, (text, color) in enumerate(buttons):
        button_rect = pygame.Rect(window_w // 2 - button_width // 2, start_y + i * (button_height + button_spacing),
                                  button_width, button_height)
        draw_modern_button(screen, button_rect, text, font_small, color)
        button_rects.append(button_rect)

    # High Score Anzeige
    if HighScore > 0:
        hs_card = pygame.Rect(window_w // 2 - 150, start_y + len(buttons) * (button_height + button_spacing) + 30, 300,
                              60)
        draw_card(screen, hs_card, None, None, themes[current_theme])

        highscore_text = font_small.render(f"Best Score: {HighScore}", True, themes[current_theme]["text_color"])
        hs_rect = highscore_text.get_rect(center=hs_card.center)
        screen.blit(highscore_text, hs_rect)

        # Upload-Option
        upload_text = font_tiny.render("Press U to upload score", True, themes[current_theme]["text_color"])
        upload_rect = upload_text.get_rect(center=(window_w // 2, hs_card.bottom + 20))
        screen.blit(upload_text, upload_rect)

    # Upload-Status
    if upload_status:
        status_card = pygame.Rect(window_w // 2 - 200, window_h - 80, 400, 40)
        draw_card(screen, status_card, None, None, themes[current_theme])
        status_text = font_tiny.render(upload_status, True, themes[current_theme]["text_color"])
        status_rect = status_text.get_rect(center=status_card.center)
        screen.blit(status_text, status_rect)

    return button_rects


def draw_pause_screen():
    """Modernes Pause Menü"""
    overlay = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    screen.blit(overlay, (0, 0))

    # Pause Karte
    card_rect = pygame.Rect(window_w // 2 - 150, window_h // 2 - 100, 300, 200)
    draw_card(screen, card_rect, None, None, themes[current_theme])

    # Pause Text
    pause_text = font_large.render("PAUSED", True, themes[current_theme]["highlight_color"])
    pause_rect = pause_text.get_rect(center=(window_w // 2, window_h // 2 - 40))
    screen.blit(pause_text, pause_rect)

    # Buttons
    continue_rect = pygame.Rect(window_w // 2 - 100, window_h // 2 + 10, 200, 40)
    menu_rect = pygame.Rect(window_w // 2 - 100, window_h // 2 + 60, 200, 40)

    draw_modern_button(screen, continue_rect, "CONTINUE", font_tiny, themes[current_theme]["highlight_color"])
    draw_modern_button(screen, menu_rect, "MAIN MENU", font_tiny, themes[current_theme]["accent_color"])

    return continue_rect, menu_rect


def draw_settings_screen():
    """Modernes Einstellungsmenü - nutzt VOLLBILD"""
    overlay = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    screen.blit(overlay, (0, 0))

    # Titel
    title_text = font_large.render("SETTINGS", True, themes[current_theme]["highlight_color"])
    title_rect = title_text.get_rect(center=(window_w // 2, 50))
    screen.blit(title_text, title_rect)

    # Zurück-Button
    back_button = pygame.Rect(50, 30, 120, 40)
    draw_modern_button(screen, back_button, "← BACK", font_tiny, themes[current_theme]["accent_color"])

    # Einstellungskarten
    card_y = 120
    card_height = 120
    card_spacing = 20

    # Difficulty Card
    diff_card = pygame.Rect(50, card_y, window_w - 100, card_height)
    draw_card(screen, diff_card, "Difficulty", None, themes[current_theme])

    diff_label = font_small.render("Difficulty:", True, themes[current_theme]["text_color"])
    screen.blit(diff_label, (70, card_y + 20))

    # Difficulty Buttons
    diff_buttons = []
    difficulties = [("NORMAL", "Normal"), ("HARD", "Schwer"), ("HARDCORE", "Hardcore")]
    for i, (display, value) in enumerate(difficulties):
        btn_rect = pygame.Rect(70 + i * 150, card_y + 60, 140, 35)
        color = themes[current_theme]["highlight_color"] if current_difficulty_preset == value else (100, 100, 100)
        draw_modern_button(screen, btn_rect, display, font_tiny, color)
        diff_buttons.append((btn_rect, value))

    # Fullscreen Card
    fs_card = pygame.Rect(50, card_y + card_height + card_spacing, window_w - 100, card_height)
    draw_card(screen, fs_card, "Display", None, themes[current_theme])

    fs_label = font_small.render("Fullscreen:", True, themes[current_theme]["text_color"])
    screen.blit(fs_label, (70, fs_card.y + 20))

    fs_button = pygame.Rect(70, fs_card.y + 60, 140, 35)
    fs_color = themes[current_theme]["highlight_color"] if fullscreen else (100, 100, 100)
    draw_modern_button(screen, fs_button, "ON" if fullscreen else "OFF", font_tiny, fs_color)

    # Themes Card
    theme_card_y = fs_card.y + card_height + card_spacing
    theme_card = pygame.Rect(50, theme_card_y, window_w - 100, 180)
    draw_card(screen, theme_card, "Themes", None, themes[current_theme])

    theme_label = font_small.render("Theme:", True, themes[current_theme]["text_color"])
    screen.blit(theme_label, (70, theme_card_y + 20))

    # Theme Buttons Grid
    theme_buttons = []
    theme_names = list(themes.keys())
    themes_per_row = 4
    for i, theme_name in enumerate(theme_names):
        row = i // themes_per_row
        col = i % themes_per_row
        btn_x = 70 + col * 160
        btn_y = theme_card_y + 60 + row * 45
        btn_rect = pygame.Rect(btn_x, btn_y, 150, 35)

        color = themes[current_theme]["highlight_color"] if current_theme == theme_name else (80, 80, 80)
        draw_modern_button(screen, btn_rect, theme_name, font_tiny, color)
        theme_buttons.append((btn_rect, theme_name))

    return back_button, diff_buttons, fs_button, theme_buttons


def draw_theme_selection():
    """Modernes Theme-Auswahl Menü"""
    overlay = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    screen.blit(overlay, (0, 0))

    # Titel
    title_text = font_large.render("SELECT THEME", True, themes[current_theme]["highlight_color"])
    title_rect = title_text.get_rect(center=(window_w // 2, 50))
    screen.blit(title_text, title_rect)

    # Zurück-Button
    back_button = pygame.Rect(50, 30, 120, 40)
    draw_modern_button(screen, back_button, "← BACK", font_tiny, themes[current_theme]["accent_color"])

    # Theme-Grid
    theme_buttons = {}
    theme_names = list(themes.keys())
    themes_per_row = 3

    for i, theme_name in enumerate(theme_names):
        row = i // themes_per_row
        col = i % themes_per_row
        x_pos = window_w // 2 - 300 + col * 200
        y_pos = 120 + row * 120

        # Theme-Vorschau Karte
        preview_rect = pygame.Rect(x_pos, y_pos, 180, 80)
        pygame.draw.rect(screen, themes[theme_name]["bg_color"], preview_rect, border_radius=8)
        pygame.draw.rect(screen, themes[theme_name]["highlight_color"], preview_rect, 2, border_radius=8)

        # Theme-Name Button
        name_rect = pygame.Rect(x_pos, y_pos + 90, 180, 30)
        color = themes[current_theme]["highlight_color"] if current_theme == theme_name else themes[theme_name][
            "accent_color"]
        draw_modern_button(screen, name_rect, theme_name, font_tiny, color)

        theme_buttons[theme_name] = pygame.Rect(x_pos, y_pos, 180, 120)

    return back_button, theme_buttons


def show_password_dialog():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    password = simpledialog.askstring("Admin Login", "Enter password:", show='*', parent=root)
    root.destroy()
    return password == "ndnet-asAdmin"


def show_admin_editor():
    root = tk.Tk()
    root.title("Admin Editor")
    root.geometry("500x600")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    score_var = tk.StringVar(value=str(score))
    highscore_var = tk.StringVar(value=str(HighScore))
    preset_var = tk.StringVar(value=current_difficulty_preset)

    preset = difficulty_presets[current_difficulty_preset]
    pipe_spacing_var = tk.StringVar(value=str(preset["pipe_spacing"]))
    difficulty_interval_var = tk.StringVar(value=str(preset["difficulty_increase_interval"]))
    velocity_multiplier_var = tk.StringVar(value=str(preset["velocity_multiplier"]))
    gap_decrease_var = tk.StringVar(value=str(preset["gap_decrease"]))
    spacing_decrease_var = tk.StringVar(value=str(preset["spacing_decrease"]))
    min_gap_var = tk.StringVar(value=str(preset["min_gap"]))
    min_spacing_var = tk.StringVar(value=str(preset["min_spacing"]))

    def update_preset_parameters(*args):
        preset_name = preset_var.get()
        if preset_name in difficulty_presets:
            preset = difficulty_presets[preset_name]
            pipe_spacing_var.set(str(preset["pipe_spacing"]))
            difficulty_interval_var.set(str(preset["difficulty_increase_interval"]))
            velocity_multiplier_var.set(str(preset["velocity_multiplier"]))
            gap_decrease_var.set(str(preset["gap_decrease"]))
            spacing_decrease_var.set(str(preset["spacing_decrease"]))
            min_gap_var.set(str(preset["min_gap"]))
            min_spacing_var.set(str(preset["min_spacing"]))

    def save_values():
        global score, HighScore, current_difficulty_preset, difficulty_presets

        try:
            new_score = int(score_var.get())
            new_highscore = int(highscore_var.get())

            if new_score < 0 or new_highscore < 0:
                messagebox.showerror("Error", "Values cannot be negative!")
                return

            score = new_score
            HighScore = new_highscore

            preset_name = preset_var.get()
            if preset_name in difficulty_presets:
                current_difficulty_preset = preset_name

                difficulty_presets[preset_name] = {
                    "pipe_spacing": int(pipe_spacing_var.get()),
                    "difficulty_increase_interval": int(difficulty_interval_var.get()),
                    "velocity_multiplier": float(velocity_multiplier_var.get()),
                    "gap_decrease": int(gap_decrease_var.get()),
                    "spacing_decrease": int(spacing_decrease_var.get()),
                    "min_gap": int(min_gap_var.get()),
                    "min_spacing": int(min_spacing_var.get())
                }

            messagebox.showinfo("Success", "Values updated successfully!")
            root.destroy()
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers!")

    row = 0
    tk.Label(root, text="Score:").grid(row=row, column=0, padx=10, pady=5, sticky="e")
    score_entry = tk.Entry(root, textvariable=score_var)
    score_entry.grid(row=row, column=1, padx=10, pady=5)
    row += 1

    tk.Label(root, text="High Score:").grid(row=row, column=0, padx=10, pady=5, sticky="e")
    highscore_entry = tk.Entry(root, textvariable=highscore_var)
    highscore_entry.grid(row=row, column=1, padx=10, pady=5)
    row += 1

    tk.Label(root, text="──────────────── Schwierigkeit ────────────────").grid(row=row, column=0, columnspan=2,
                                                                                pady=10)
    row += 1

    tk.Label(root, text="Schwierigkeitsstufe:").grid(row=row, column=0, padx=10, pady=5, sticky="e")
    preset_dropdown = tk.OptionMenu(root, preset_var, *difficulty_presets.keys(), command=update_preset_parameters)
    preset_dropdown.grid(row=row, column=1, padx=10, pady=5, sticky="w")
    row += 1

    tk.Label(root, text="Start-Rohrabstand:").grid(row=row, column=0, padx=10, pady=5, sticky="e")
    tk.Entry(root, textvariable=pipe_spacing_var).grid(row=row, column=1, padx=10, pady=5)
    row += 1

    tk.Label(root, text="Schwierigkeits-Intervall:").grid(row=row, column=0, padx=10, pady=5, sticky="e")
    tk.Entry(root, textvariable=difficulty_interval_var).grid(row=row, column=1, padx=10, pady=5)
    row += 1

    tk.Label(root, text="Geschwindigkeits-Multiplikator:").grid(row=row, column=0, padx=10, pady=5, sticky="e")
    tk.Entry(root, textvariable=velocity_multiplier_var).grid(row=row, column=1, padx=10, pady=5)
    row += 1

    tk.Label(root, text="Lücken-Verringerung:").grid(row=row, column=0, padx=10, pady=5, sticky="e")
    tk.Entry(root, textvariable=gap_decrease_var).grid(row=row, column=1, padx=10, pady=5)
    row += 1

    tk.Label(root, text="Abstands-Verringerung:").grid(row=row, column=0, padx=10, pady=5, sticky="e")
    tk.Entry(root, textvariable=spacing_decrease_var).grid(row=row, column=1, padx=10, pady=5)
    row += 1

    tk.Label(root, text="Minimale Lücke:").grid(row=row, column=0, padx=10, pady=5, sticky="e")
    tk.Entry(root, textvariable=min_gap_var).grid(row=row, column=1, padx=10, pady=5)
    row += 1

    tk.Label(root, text="Minimaler Abstand:").grid(row=row, column=0, padx=10, pady=5, sticky="e")
    tk.Entry(root, textvariable=min_spacing_var).grid(row=row, column=1, padx=10, pady=5)
    row += 1

    save_btn = tk.Button(root, text="Save", command=save_values, width=10)
    save_btn.grid(row=row, column=0, columnspan=2, pady=20)

    score_entry.focus_set()
    root.bind('<Return>', lambda event: save_values())

    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry('+{}+{}'.format(x, y))

    root.mainloop()


def upload_highscore(name):
    global upload_status
    try:
        url = "https://flappy-bird.nsce.fr/api/upload_score"
        data = {
            "name": name,
            "score": HighScore
        }
        response = requests.post(url, json=data, timeout=10)

        if response.status_code == 200:
            result = response.json()
            upload_status = result.get("message", "Erfolgreich hochgeladen!")
        else:
            upload_status = f"Fehler beim Hochladen: {response.status_code}"
    except Exception as e:
        upload_status = f"Verbindungsfehler: {str(e)}"


def show_upload_dialog():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    name = simpledialog.askstring("Highscore upload",
                                  "Gib deinen Namen ein um deinen Highscore zu teilen:",
                                  parent=root)
    root.destroy()

    if name and name.strip():
        upload_thread = threading.Thread(target=upload_highscore, args=(name.strip(),))
        upload_thread.daemon = True
        upload_thread.start()
        return True
    return False


class Pipe:
    def __init__(self, x, height, gap, velocity):
        self.x = x
        self.height = height
        self.gap = gap
        self.velocity = velocity
        self.scored = False
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

    def draw(self):
        if self.x + pipe_up_img.get_width() > 0 and self.x < GAME_WIDTH:
            top_y = game_area.y + 0 - pipe_down_img.get_height() + self.height
            screen.blit(pipe_down_img, (game_area.x + self.x, top_y))

            bottom_y = game_area.y + self.height + self.gap
            screen.blit(pipe_up_img, (game_area.x + self.x, bottom_y))


def check_collision(player, pipes):
    if player.rect.top <= 0:
        return True

    if player.rect.bottom >= ACTUAL_PLAY_HEIGHT:
        return True

    for pipe in pipes:
        if pipe.x + pipe_up_img.get_width() > 0 and pipe.x < GAME_WIDTH:
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
    global score, has_moved, difficulty_level, last_difficulty_update

    score = 0
    has_moved = False
    difficulty_level = 0
    last_difficulty_update = 0

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

    save_settings()


def game():
    global game_state, HighScore, score, has_moved, window_focused, upload_status, dt
    global player_img, pipe_up_img, pipe_down_img, ground_img, bg_img, current_theme, current_difficulty_preset
    global pipe_up_mask, pipe_down_mask, theme_images, theme_masks

    bg_x_pos = 0
    ground_x_pos = 0

    player, pipes = reset_game()

    # UI-Button-Variablen
    main_menu_buttons = None
    death_screen_buttons = None
    pause_screen_buttons = None
    settings_buttons = None
    theme_buttons = None

    while True:
        dt = clock.tick(fps) / 1000.0
        mouse_pos = pygame.mouse.get_pos()

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
                if event.key == pygame.K_F12:
                    if show_password_dialog():
                        show_admin_editor()

                if game_state == 1:  # Hauptmenü
                    if event.key == pygame.K_SPACE:
                        player, pipes = reset_game()
                        game_state = 2
                    elif event.key == pygame.K_s:
                        game_state = 6
                    elif event.key == pygame.K_t:
                        game_state = 7
                    elif event.key == pygame.K_u and HighScore > 0:
                        if show_upload_dialog():
                            game_state = 5

                elif game_state == 2:  # Spielzustand
                    has_moved = True
                    if event.key == pygame.K_SPACE:
                        pygame.mixer.Sound.play(woosh_sfx)
                        player.jump()
                    if event.key == pygame.K_p:
                        game_state = 4
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_b:
                        game_state = 1

                elif game_state == 3:  # Death Screen
                    if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        player, pipes = reset_game()
                        game_state = 2
                    elif event.key == pygame.K_b:
                        game_state = 1

                elif game_state == 4:  # Pause Screen
                    if event.key == pygame.K_SPACE or event.key == pygame.K_p:
                        game_state = 2
                    elif event.key == pygame.K_b:
                        game_state = 1

                elif game_state == 5:  # Upload-Bestätigung
                    if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                        game_state = 1

            if event.type == pygame.MOUSEBUTTONDOWN:
                if game_state == 1 and main_menu_buttons:  # Hauptmenü
                    start_rect, settings_rect, themes_rect = main_menu_buttons
                    if start_rect.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        player, pipes = reset_game()
                        game_state = 2
                        has_moved = True
                    elif settings_rect.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        game_state = 6
                    elif themes_rect.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        game_state = 7

                elif game_state == 2:  # Spiel
                    pygame.mixer.Sound.play(woosh_sfx)
                    player.jump()

                elif game_state == 3 and death_screen_buttons:  # Tod
                    restart_rect, menu_rect = death_screen_buttons
                    if restart_rect.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        player, pipes = reset_game()
                        game_state = 2
                        has_moved = True
                    elif menu_rect.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        game_state = 1

                elif game_state == 4 and pause_screen_buttons:  # Pause
                    continue_rect, menu_rect = pause_screen_buttons
                    if continue_rect.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        game_state = 2
                    elif menu_rect.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        game_state = 1

                elif game_state == 6 and settings_buttons:  # Einstellungen
                    back_button, diff_buttons, fs_button, theme_buttons_list = settings_buttons

                    if back_button.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        game_state = 1

                    # Difficulty buttons
                    for btn_rect, value in diff_buttons:
                        if btn_rect.collidepoint(mouse_pos):
                            pygame.mixer.Sound.play(select_sfx)
                            current_difficulty_preset = value
                            save_settings()

                    # Fullscreen button
                    if fs_button.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        toggle_fullscreen()

                    # Theme buttons
                    for btn_rect, theme_name in theme_buttons_list:
                        if btn_rect.collidepoint(mouse_pos):
                            pygame.mixer.Sound.play(select_sfx)
                            current_theme = theme_name
                            # Theme-Bilder UND Masken mit Filter neu laden
                            theme_images, theme_masks = load_theme_images(current_theme)
                            player_img = theme_images["player_img"]
                            pipe_up_img = theme_images["pipe_up_img"]
                            pipe_down_img = theme_images["pipe_down_img"]
                            ground_img = theme_images["ground_img"]
                            bg_img = theme_images["background_img"]
                            pipe_up_mask = theme_masks["pipe_up_mask"]
                            pipe_down_mask = theme_masks["pipe_down_mask"]
                            player.rotated_image = player_img
                            player.mask = pygame.mask.from_surface(player_img)
                            save_settings()

                elif game_state == 7 and theme_buttons:  # Theme-Auswahl
                    back_button, theme_buttons_dict = theme_buttons

                    if back_button.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        game_state = 1
                    else:
                        for theme_name, button_rect in theme_buttons_dict.items():
                            if button_rect.collidepoint(mouse_pos):
                                pygame.mixer.Sound.play(select_sfx)
                                current_theme = theme_name
                                # Theme-Bilder UND Masken mit Filter neu laden
                                theme_images, theme_masks = load_theme_images(current_theme)
                                player_img = theme_images["player_img"]
                                pipe_up_img = theme_images["pipe_up_img"]
                                pipe_down_img = theme_images["pipe_down_img"]
                                ground_img = theme_images["ground_img"]
                                bg_img = theme_images["background_img"]
                                pipe_up_mask = theme_masks["pipe_up_mask"]
                                pipe_down_mask = theme_masks["pipe_down_mask"]
                                player.rotated_image = player_img
                                player.mask = pygame.mask.from_surface(player_img)
                                save_settings()
                                break

        # Spiel-Logik
        if game_state == 2 and has_moved:
            player.update()

            if check_collision(player, pipes):
                if score > HighScore:
                    HighScore = score
                    save_settings()
                pygame.mixer.Sound.play(slap_sfx)
                game_state = 3

            for pipe in pipes:
                pipe.velocity = current_velocity
                pipe.update()

            if pipes and pipes[0].x < -pipe_up_img.get_width():
                pipes.pop(0)
                last_pipe_x = pipes[-1].x if pipes else GAME_WIDTH
                min_height = 50
                max_height = ACTUAL_PLAY_HEIGHT - current_gap - 50
                random_height = random.randint(min_height, max_height)
                pipes.append(Pipe(last_pipe_x + current_spacing, random_height, current_gap, current_velocity))

            for pipe in pipes:
                if not pipe.scored and pipe.x + pipe_up_img.get_width() < player.x:
                    score += 1
                    pygame.mixer.Sound.play(score_sfx)
                    pipe.scored = True

            bg_x_pos -= bg_scroll_spd
            ground_x_pos -= ground_scroll_spd

            if bg_x_pos <= -bg_width:
                bg_x_pos = 0

            if ground_x_pos <= -bg_width:
                ground_x_pos = 0

        # Zeichnen
        screen.fill(themes[current_theme]["bg_color"])

        # Spielbereich-Rahmen (nur während Gameplay)
        if game_state == 2:
            pygame.draw.rect(screen, (50, 50, 50), game_area, 2)

        # Spielbereich-Inhalt (nur während Gameplay)
        if game_state == 2:
            screen.set_clip(game_area)
            screen.blit(bg_img, (game_area.x + bg_x_pos, game_area.y))
            screen.blit(bg_img, (game_area.x + bg_x_pos + bg_width, game_area.y))
            screen.blit(ground_img, (game_area.x + ground_x_pos, game_area.y + ACTUAL_PLAY_HEIGHT))
            screen.blit(ground_img, (game_area.x + ground_x_pos + bg_width, game_area.y + ACTUAL_PLAY_HEIGHT))

            for pipe in pipes:
                pipe.draw()
            player.draw()

            screen.set_clip(None)
            scoreboard()

        # Menü-Overlays (nutzen VOLLBILD)
        if game_state == 1:
            main_menu_buttons = draw_main_menu()
        elif game_state == 3:
            death_screen_buttons = draw_death_screen()
        elif game_state == 4:
            pause_screen_buttons = draw_pause_screen()
        elif game_state == 5:
            # Upload-Bestätigung
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
        elif game_state == 7:
            theme_buttons = draw_theme_selection()

        pygame.display.flip()
        clock.tick(fps)


game()