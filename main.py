import io
import pygame, sys, random
import os
from pathlib import Path
import tkinter as tk
from tkinter import simpledialog, messagebox
import requests
import threading
import json

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


# Initialize Game
pygame.init()

# Globale Variablen
game_state = 0  # 0: Start Screen, 1: Hauptmenü, 2: Spiel, 3: Tod, 4: Pause, 5: Upload-Bestätigung, 6: Einstellungen, 7: Theme-Auswahl
score = 0
has_moved = False
HighScore = 0
window_focused = True
upload_status = ""  # Status des Upload-Versuchs
fullscreen = False  # Vollbildmodus

# Fester Spielbereich (400x600) - UNVERÄNDERLICH
GAME_WIDTH, GAME_HEIGHT = 400, 600
game_area = pygame.Rect(0, 0, GAME_WIDTH, GAME_HEIGHT)

# Boden-Höhe für präzise Kollisionserkennung
GROUND_HEIGHT = 64  # Höhe des Bodens in Pixeln
ACTUAL_PLAY_HEIGHT = GAME_HEIGHT - GROUND_HEIGHT  # 536 Pixel spielbare Höhe

# Schwierigkeits-Variablen
base_pipe_velocity = 2.4  # Basisgeschwindigkeit der Rohre
base_gap = 220  # Basis-Lücke zwischen den Rohren
difficulty_level = 0  # Aktuelles Schwierigkeitslevel
last_difficulty_update = 0  # Score bei der letzten Schwierigkeitsanpassung

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

current_difficulty_preset = "Normal"  # Standard-Schwierigkeitsstufe

# Themes
themes = {
    "Classic": {
        "background": "images/background.png",
        "ground": "images/ground.png",
        "player": "images/player.png",
        "pipe_up": "images/pipe_up.png",
        "pipe_down": "images/pipe_down.png",
        "bg_color": (113, 197, 207),
        "text_color": (0, 0, 0),
        "highlight_color": (255, 215, 0)
    },
    "Night": {
        "background": "images/background_night.png",
        "ground": "images/ground_night.png",
        "player": "images/player_night.png",
        "pipe_up": "images/pipe_up_night.png",
        "pipe_down": "images/pipe_down_night.png",
        "bg_color": (20, 20, 40),
        "text_color": (220, 220, 220),
        "highlight_color": (100, 150, 255)
    },
    "Desert": {
        "background": "images/background_desert.png",
        "ground": "images/ground_desert.png",
        "player": "images/player_desert.png",
        "pipe_up": "images/pipe_up_desert.png",
        "pipe_down": "images/pipe_down_desert.png",
        "bg_color": (235, 200, 140),
        "text_color": (80, 40, 0),
        "highlight_color": (255, 100, 0)
    }
}

current_theme = "Classic"  # Standard-Theme


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
        # Standardwerte verwenden, falls Datei nicht existiert
        pass


# Einstellungen speichern
def save_settings():
    settings = {
        "theme": current_theme,
        "difficulty": current_difficulty_preset,
        "fullscreen": fullscreen,
        "highscore": HighScore
    }
    with open(resource_path("settings.json"), "w") as f:
        json.dump(settings, f)


# Einstellungen laden
load_settings()

# Window Setup
if fullscreen:
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    window_w, window_h = screen.get_size()
    # Zentriere das Spielbereich
    game_area.x = (window_w - GAME_WIDTH) // 2
    game_area.y = (window_h - GAME_HEIGHT) // 2
else:
    window_w, window_h = 1600, 600  # Größeres Fenster
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
    # Fallback, falls Icon nicht geladen werden kann
    pass

clock = pygame.time.Clock()
fps = 60

# Load Fonts mit resource_path
font = pygame.font.Font(resource_path("fonts/BaiJamjuree-Bold.ttf"), 80)
font_small = pygame.font.Font(resource_path("fonts/BaiJamjuree-Bold.ttf"), 32)
font_medium = pygame.font.Font(resource_path("fonts/BaiJamjuree-Bold.ttf"), 50)
font_tiny = pygame.font.Font(resource_path("fonts/BaiJamjuree-Bold.ttf"), 24)

# Load Sounds mit resource_path
slap_sfx = pygame.mixer.Sound(resource_path("sounds/slap.wav"))
woosh_sfx = pygame.mixer.Sound(resource_path("sounds/woosh.wav"))
score_sfx = pygame.mixer.Sound(resource_path("sounds/score.wav"))
select_sfx = pygame.mixer.Sound(resource_path("sounds/select.wav"))


# Theme-basierte Bilder laden
def load_theme_images(theme_name):
    theme = themes[theme_name]
    return {
        "player_img": pygame.image.load(resource_path(theme["player"])),
        "pipe_up_img": pygame.image.load(resource_path(theme["pipe_up"])),
        "pipe_down_img": pygame.image.load(resource_path(theme["pipe_down"])),
        "ground_img": pygame.image.load(resource_path(theme["ground"])),
        "bg_img": pygame.image.load(resource_path(theme["background"]))
    }


# Initiale Bilder laden
theme_images = load_theme_images(current_theme)
player_img = theme_images["player_img"]
pipe_up_img = theme_images["pipe_up_img"]
pipe_down_img = theme_images["pipe_down_img"]
ground_img = theme_images["ground_img"]
bg_img = theme_images["bg_img"]

# Erstelle Masken für die Rohre
pipe_up_mask = pygame.mask.from_surface(pipe_up_img)
pipe_down_mask = pygame.mask.from_surface(pipe_down_img)

bg_width = bg_img.get_width()

# Variable Setup
bg_scroll_spd = 1
ground_scroll_spd = 2


# Button-Klassen für bessere Mausinteraktion
class Button:
    def __init__(self, x, y, width, height, text, font, color, hover_color):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.color = color
        self.hover_color = hover_color
        self.is_hovered = False

    def draw(self, surface):
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(surface, color, self.rect, border_radius=10)
        text_surface = self.font.render(self.text, True, (0, 0, 0))
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)
        return self.is_hovered

    def check_click(self, pos, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(pos)
        return False


class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.velocity = 0
        # visuelle Attribute
        self.rotated_image = player_img
        self.rect = self.rotated_image.get_rect(topleft=(self.x, self.y))
        self.mask = pygame.mask.from_surface(self.rotated_image)

    def jump(self):
        self.velocity = -10

    def update(self):
        # dt muss pro Frame gesetzt werden (siehe weiter unten)
        self.velocity += 0.75 * dt * 60
        self.y += self.velocity * dt * 60

        # Begrenze den Spieler auf den Spielbereich
        if self.y < 0:
            self.y = 0
            self.velocity = 0
        elif self.y > ACTUAL_PLAY_HEIGHT - player_img.get_height():
            self.y = ACTUAL_PLAY_HEIGHT - player_img.get_height()
            self.velocity = 0

        # Winkel abhängig von Geschwindigkeit
        angle = max(-30, min(30, -self.velocity * 3))
        self.rotated_image = pygame.transform.rotate(player_img, angle)

        # Aktualisiere die Maske basierend auf dem rotierten Bild
        self.mask = pygame.mask.from_surface(self.rotated_image)

        # Rotation um das Zentrum: rect zentrieren
        center_x = self.x + player_img.get_width() // 2
        center_y = self.y + player_img.get_height() // 2
        self.rect = self.rotated_image.get_rect(center=(center_x, center_y))

    def draw(self):
        # Stelle sicher, dass der Spieler nur im Spielbereich gezeichnet wird
        draw_x = game_area.x + self.rect.x
        draw_y = game_area.y + self.rect.y

        # Überprüfe, ob der Spieler im sichtbaren Bereich ist
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
    # Halbtransparenten Overlay zeichnen
    overlay = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    # Texte für den Death Screen
    game_over_text = font_medium.render("GAME OVER", True, themes[current_theme]["highlight_color"])
    score_text = font_small.render(f"Score: {score}", True, themes[current_theme]["text_color"])
    highscore_text = font_small.render(f"High Score: {HighScore}", True, themes[current_theme]["text_color"])
    restart_text = font_small.render("Click to play again", True, themes[current_theme]["text_color"])
    menu_text = font_small.render("Press B for main menu", True, themes[current_theme]["text_color"])

    # Texte zentrieren
    screen.blit(game_over_text, (window_w // 2 - game_over_text.get_width() // 2, window_h // 2 - 100))
    screen.blit(score_text, (window_w // 2 - score_text.get_width() // 2, window_h // 2 - 20))
    screen.blit(highscore_text, (window_w // 2 - highscore_text.get_width() // 2, window_h // 2 + 20))
    screen.blit(restart_text, (window_w // 2 - restart_text.get_width() // 2, window_h // 2 + 70))
    screen.blit(menu_text, (window_w // 2 - menu_text.get_width() // 2, window_h // 2 + 120))


def draw_main_menu():
    # Halbtransparenten Overlay zeichnen
    overlay = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    # Texte für das Hauptmenü
    title_text = font_medium.render("FLAPPY BIRD", True, themes[current_theme]["highlight_color"])
    start_text = font_small.render("Click to start", True, themes[current_theme]["text_color"])
    settings_text = font_small.render("Press S for settings", True, themes[current_theme]["text_color"])
    highscore_text = font_small.render(f"High Score: {HighScore}", True, themes[current_theme]["text_color"])

    # Upload-Text, wenn ein Highscore vorhanden ist
    upload_prompt = None
    if HighScore > 0:
        upload_prompt = font_small.render("Press U to upload your score", True, (0, 255, 0))

    # Upload-Status anzeigen, falls vorhanden
    status_text = None
    if upload_status:
        status_text = font_small.render(upload_status, True, (255, 255, 0))

    # Texte zentrieren
    screen.blit(title_text, (window_w // 2 - title_text.get_width() // 2, window_h // 2 - 100))
    screen.blit(start_text, (window_w // 2 - start_text.get_width() // 2, window_h // 2))
    screen.blit(settings_text, (window_w // 2 - settings_text.get_width() // 2, window_h // 2 + 50))
    screen.blit(highscore_text, (window_w // 2 - highscore_text.get_width() // 2, window_h // 2 + 100))

    if upload_prompt:
        screen.blit(upload_prompt, (window_w // 2 - upload_prompt.get_width() // 2, window_h // 2 + 150))

    if status_text:
        screen.blit(status_text, (window_w // 2 - status_text.get_width() // 2, window_h // 2 + 200))


def draw_pause_screen():
    # Halbtransparenten Overlay zeichnen
    overlay = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    # Texte für den Pause Screen
    pause_text = font_medium.render("PAUSED", True, themes[current_theme]["highlight_color"])
    continue_text = font_small.render("Click to continue", True, themes[current_theme]["text_color"])
    menu_text = font_small.render("Press B for main menu", True, themes[current_theme]["text_color"])

    # Texte zentrieren
    screen.blit(pause_text, (window_w // 2 - pause_text.get_width() // 2, window_h // 2 - 50))
    screen.blit(continue_text, (window_w // 2 - continue_text.get_width() // 2, window_h // 2 + 20))
    screen.blit(menu_text, (window_w // 2 - menu_text.get_width() // 2, window_h // 2 + 70))


def draw_start_screen():
    # Hintergrund mit leichtem Overlay
    overlay = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 100))
    screen.blit(overlay, (0, 0))

    # Titel
    title_text = font_medium.render("FLAPPY BIRD", True, themes[current_theme]["highlight_color"])
    screen.blit(title_text, (window_w // 2 - title_text.get_width() // 2, window_h // 4))

    # Start-Button
    start_button = pygame.Rect(window_w // 2 - 150, window_h // 2, 300, 60)
    pygame.draw.rect(screen, themes[current_theme]["highlight_color"], start_button, border_radius=15)
    start_text = font_small.render("START GAME", True, (0, 0, 0))
    screen.blit(start_text, (window_w // 2 - start_text.get_width() // 2, window_h // 2 + 15))

    # Einstellungs-Button
    settings_button = pygame.Rect(window_w // 2 - 150, window_h // 2 + 80, 300, 60)
    pygame.draw.rect(screen, themes[current_theme]["highlight_color"], settings_button, border_radius=15)
    settings_text = font_small.render("SETTINGS", True, (0, 0, 0))
    screen.blit(settings_text, (window_w // 2 - settings_text.get_width() // 2, window_h // 2 + 95))

    # Theme-Button
    theme_button = pygame.Rect(window_w // 2 - 150, window_h // 2 + 160, 300, 60)
    pygame.draw.rect(screen, themes[current_theme]["highlight_color"], theme_button, border_radius=15)
    theme_text = font_small.render("THEMES", True, (0, 0, 0))
    screen.blit(theme_text, (window_w // 2 - theme_text.get_width() // 2, window_h // 2 + 175))

    # Copyright-Text
    copyright_text = font_tiny.render("© 2023 Flappy Bird", True, themes[current_theme]["text_color"])
    screen.blit(copyright_text, (window_w // 2 - copyright_text.get_width() // 2, window_h - 50))

    return start_button, settings_button, theme_button


def draw_settings_screen():
    # Halbtransparenten Overlay zeichnen
    overlay = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    screen.blit(overlay, (0, 0))

    # Titel
    title_text = font_medium.render("SETTINGS", True, themes[current_theme]["highlight_color"])
    screen.blit(title_text, (window_w // 2 - title_text.get_width() // 2, 100))

    # Schwierigkeitsauswahl
    diff_text = font_small.render("Difficulty:", True, themes[current_theme]["text_color"])
    screen.blit(diff_text, (window_w // 2 - 200, 200))

    # Vollbildmodus
    fullscreen_text = font_small.render("Fullscreen:", True, themes[current_theme]["text_color"])
    screen.blit(fullscreen_text, (window_w // 2 - 200, 280))

    # Zurück-Button
    back_button = pygame.Rect(50, 50, 150, 50)
    pygame.draw.rect(screen, themes[current_theme]["highlight_color"], back_button, border_radius=10)
    back_text = font_small.render("BACK", True, (0, 0, 0))
    screen.blit(back_text, (50 + 75 - back_text.get_width() // 2, 50 + 25 - back_text.get_height() // 2))

    # Schwierigkeits-Buttons
    normal_button = pygame.Rect(window_w // 2 + 50, 190, 150, 40)
    hard_button = pygame.Rect(window_w // 2 + 210, 190, 150, 40)
    hardcore_button = pygame.Rect(window_w // 2 + 370, 190, 150, 40)

    # Farben für aktive/inaktive Buttons
    normal_color = themes[current_theme]["highlight_color"] if current_difficulty_preset == "Normal" else (100, 100,
                                                                                                           100)
    hard_color = themes[current_theme]["highlight_color"] if current_difficulty_preset == "Schwer" else (100, 100, 100)
    hardcore_color = themes[current_theme]["highlight_color"] if current_difficulty_preset == "Hardcore" else (100, 100,
                                                                                                               100)

    pygame.draw.rect(screen, normal_color, normal_button, border_radius=10)
    pygame.draw.rect(screen, hard_color, hard_button, border_radius=10)
    pygame.draw.rect(screen, hardcore_color, hardcore_button, border_radius=10)

    normal_text = font_tiny.render("NORMAL", True, (255, 255, 255))
    hard_text = font_tiny.render("HARD", True, (255, 255, 255))
    hardcore_text = font_tiny.render("HARDCORE", True, (255, 255, 255))

    screen.blit(normal_text,
                (window_w // 2 + 50 + 75 - normal_text.get_width() // 2, 190 + 20 - normal_text.get_height() // 2))
    screen.blit(hard_text,
                (window_w // 2 + 210 + 75 - hard_text.get_width() // 2, 190 + 20 - hard_text.get_height() // 2))
    screen.blit(hardcore_text,
                (window_w // 2 + 370 + 75 - hardcore_text.get_width() // 2, 190 + 20 - hardcore_text.get_height() // 2))

    # Vollbildmodus-Button
    fullscreen_button = pygame.Rect(window_w // 2 + 50, 270, 150, 40)
    fullscreen_color = themes[current_theme]["highlight_color"] if fullscreen else (100, 100, 100)
    pygame.draw.rect(screen, fullscreen_color, fullscreen_button, border_radius=10)
    fullscreen_btn_text = font_tiny.render("ON" if fullscreen else "OFF", True, (255, 255, 255))
    screen.blit(fullscreen_btn_text, (window_w // 2 + 50 + 75 - fullscreen_btn_text.get_width() // 2,
                                      270 + 20 - fullscreen_btn_text.get_height() // 2))

    return back_button, normal_button, hard_button, hardcore_button, fullscreen_button


def draw_theme_selection():
    # Halbtransparenten Overlay zeichnen
    overlay = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    screen.blit(overlay, (0, 0))

    # Titel
    title_text = font_medium.render("SELECT THEME", True, themes[current_theme]["highlight_color"])
    screen.blit(title_text, (window_w // 2 - title_text.get_width() // 2, 100))

    # Zurück-Button
    back_button = pygame.Rect(50, 50, 150, 50)
    pygame.draw.rect(screen, themes[current_theme]["highlight_color"], back_button, border_radius=10)
    back_text = font_small.render("BACK", True, (0, 0, 0))
    screen.blit(back_text, (50 + 75 - back_text.get_width() // 2, 50 + 25 - back_text.get_height() // 2))

    # Theme-Buttons
    theme_buttons = {}
    theme_previews = {}
    theme_names = list(themes.keys())

    for i, theme_name in enumerate(theme_names):
        # Button position
        x_pos = window_w // 2 - 200 + (i % 3) * 200
        y_pos = 200 + (i // 3) * 200

        # Theme-Vorschau
        preview_rect = pygame.Rect(x_pos, y_pos, 180, 150)
        pygame.draw.rect(screen, themes[theme_name]["bg_color"], preview_rect)

        # Theme-Name
        name_text = font_tiny.render(theme_name, True, themes[theme_name]["text_color"])
        screen.blit(name_text, (x_pos + 90 - name_text.get_width() // 2, y_pos + 160))

        # Auswahlindikator
        if theme_name == current_theme:
            pygame.draw.rect(screen, themes[theme_name]["highlight_color"], preview_rect, 4)

        theme_buttons[theme_name] = preview_rect
        theme_previews[theme_name] = preview_rect

    return back_button, theme_buttons


def show_password_dialog():
    # Tkinter Passwort-Eingabefenster erstellen
    root = tk.Tk()
    root.withdraw()  # Hauptfenster verstecken
    root.attributes("-topmost", True)  # Immer im Vordergrund

    # Passwort abfragen
    password = simpledialog.askstring("Admin Login", "Enter password:", show='*', parent=root)

    root.destroy()
    return password == "ndnet-asAdmin"


def show_admin_editor():
    # Tkinter Admin-Editor-Fenster erstellen
    root = tk.Tk()
    root.title("Admin Editor")
    root.geometry("500x600")
    root.resizable(False, False)
    root.attributes("-topmost", True)  # Immer im Vordergrund

    # Variablen für die Eingabefelder
    score_var = tk.StringVar(value=str(score))
    highscore_var = tk.StringVar(value=str(HighScore))

    # Schwierigkeits-Preset Auswahl
    preset_var = tk.StringVar(value=current_difficulty_preset)

    # Schwierigkeitsparameter Variablen
    preset = difficulty_presets[current_difficulty_preset]
    pipe_spacing_var = tk.StringVar(value=str(preset["pipe_spacing"]))
    difficulty_interval_var = tk.StringVar(value=str(preset["difficulty_increase_interval"]))
    velocity_multiplier_var = tk.StringVar(value=str(preset["velocity_multiplier"]))
    gap_decrease_var = tk.StringVar(value=str(preset["gap_decrease"]))
    spacing_decrease_var = tk.StringVar(value=str(preset["spacing_decrease"]))
    min_gap_var = tk.StringVar(value=str(preset["min_gap"]))
    min_spacing_var = tk.StringVar(value=str(preset["min_spacing"]))

    # Funktion zum Aktualisieren der Parameter basierend auf dem ausgewählten Preset
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

    # Funktion zum Speichern der Werte
    def save_values():
        global score, HighScore, current_difficulty_preset, difficulty_presets

        try:
            # Score und Highscore speichern
            new_score = int(score_var.get())
            new_highscore = int(highscore_var.get())

            if new_score < 0 or new_highscore < 0:
                messagebox.showerror("Error", "Values cannot be negative!")
                return

            score = new_score
            HighScore = new_highscore

            # Schwierigkeits-Preset und Parameter speichern
            preset_name = preset_var.get()
            if preset_name in difficulty_presets:
                current_difficulty_preset = preset_name

                # Aktualisiere die Parameter des ausgewählten Presets
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

    # Widgets erstellen
    row = 0

    # Score und Highscore
    tk.Label(root, text="Score:").grid(row=row, column=0, padx=10, pady=5, sticky="e")
    score_entry = tk.Entry(root, textvariable=score_var)
    score_entry.grid(row=row, column=1, padx=10, pady=5)
    row += 1

    tk.Label(root, text="High Score:").grid(row=row, column=0, padx=10, pady=5, sticky="e")
    highscore_entry = tk.Entry(root, textvariable=highscore_var)
    highscore_entry.grid(row=row, column=1, padx=10, pady=5)
    row += 1

    # Trennlinie
    tk.Label(root, text="────────────── Schwierigkeit ──────────────").grid(row=row, column=0, columnspan=2, pady=10)
    row += 1

    # Schwierigkeits-Preset Auswahl
    tk.Label(root, text="Schwierigkeitsstufe:").grid(row=row, column=0, padx=10, pady=5, sticky="e")
    preset_dropdown = tk.OptionMenu(root, preset_var, *difficulty_presets.keys(), command=update_preset_parameters)
    preset_dropdown.grid(row=row, column=1, padx=10, pady=5, sticky="w")
    row += 1

    # Schwierigkeitsparameter
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

    # Buttons
    save_btn = tk.Button(root, text="Save", command=save_values, width=10)
    save_btn.grid(row=row, column=0, columnspan=2, pady=20)

    # Fokus auf das erste Eingabefeld setzen
    score_entry.focus_set()

    # Enter-Taste zum Speichern binden
    root.bind('<Return>', lambda event: save_values())

    # Fenster zentrieren
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry('+{}+{}'.format(x, y))

    root.mainloop()


# Neue Funktion zum Hochladen des Highscores
def upload_highscore(name):
    global upload_status
    try:
        # URL zu deinem Server-Endpoint
        url = "https://flappy-bird.nsce.fr/api/upload_score"
        data = {
            "name": name,
            "score": HighScore
        }
        response = requests.post(url, json=data, timeout=10)

        # Antwort verarbeiten
        if response.status_code == 200:
            result = response.json()
            upload_status = result.get("message", "Erfolgreich hochgeladen!")
        else:
            upload_status = f"Fehler beim Hochladen: {response.status_code}"
    except Exception as e:
        upload_status = f"Verbindungsfehler: {str(e)}"


# Neue Funktion für den Upload-Dialog
def show_upload_dialog():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    name = simpledialog.askstring("Highscore upload",
                                  "Gib deinen Namen ein um deinen Highscore zu teilen:",
                                  parent=root)
    root.destroy()

    if name and name.strip():
        # Hochladen in einem separaten Thread, um das Spiel nicht zu blockieren
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
        # Positionen für die Kollisionserkennung - auf Spielbereich beschränkt
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
        # Aktualisiere die Position der Rechtecke und begrenze sie auf den Spielbereich
        self.top_rect.x = max(0, min(self.x, GAME_WIDTH - pipe_down_img.get_width()))
        self.bottom_rect.x = max(0, min(self.x, GAME_WIDTH - pipe_up_img.get_width()))

    def draw(self):
        # Zeichne nur, wenn die Rohre im Spielbereich sind
        if self.x + pipe_up_img.get_width() > 0 and self.x < GAME_WIDTH:
            # Draw top pipe
            top_y = game_area.y + 0 - pipe_down_img.get_height() + self.height
            screen.blit(pipe_down_img, (game_area.x + self.x, top_y))

            # Draw bottom pipe
            bottom_y = game_area.y + self.height + self.gap
            screen.blit(pipe_up_img, (game_area.x + self.x, bottom_y))


def check_collision(player, pipes):
    # Verbesserte Kollision mit Boden und Decke
    # Kollision mit der Decke (oberer Spielfeldrand)
    if player.rect.top <= 0:
        return True

    # Kollision mit dem Boden - präziser
    # Der Vogel stirbt erst, wenn er wirklich den sichtbaren Boden berührt
    if player.rect.bottom >= ACTUAL_PLAY_HEIGHT:
        return True

    # Kollision mit Rohren (Masken-basiert)
    for pipe in pipes:
        # Nur prüfen, wenn das Rohr im Spielbereich ist
        if pipe.x + pipe_up_img.get_width() > 0 and pipe.x < GAME_WIDTH:
            # Berechne den Offset zwischen Spieler und Rohr
            offset_top_x = pipe.top_rect.left - player.rect.left
            offset_top_y = pipe.top_rect.top - player.rect.top
            offset_bottom_x = pipe.bottom_rect.left - player.rect.left
            offset_bottom_y = pipe.bottom_rect.top - player.rect.top

            # Überprüfe Kollision mit Masken
            if player.mask.overlap(pipe_down_mask, (offset_top_x, offset_top_y)):
                return True
            if player.mask.overlap(pipe_up_mask, (offset_bottom_x, offset_bottom_y)):
                return True

    return False


def update_difficulty():
    global difficulty_level, last_difficulty_update

    preset = difficulty_presets[current_difficulty_preset]

    # Erhöhe Schwierigkeit alle X Punkte (abhängig vom Preset)
    if score >= last_difficulty_update + preset["difficulty_increase_interval"]:
        difficulty_level += 1
        last_difficulty_update = score

    # Berechne aktuelle Werte basierend auf Schwierigkeitslevel und Preset
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

    # Verwende pipe_spacing aus dem aktuellen Preset
    preset = difficulty_presets[current_difficulty_preset]
    pipe_spacing = preset["pipe_spacing"]

    player = Player(GAME_WIDTH // 4, GAME_HEIGHT // 2)

    # Erstelle mehrere Rohre mit unterschiedlichen Abständen
    pipes = []
    for i in range(3):  # 3 Rohre gleichzeitig
        x_pos = GAME_WIDTH + (i * pipe_spacing)
        # Stelle sicher, dass die Rohre nicht zu nah am Boden oder der Decke sind
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
        # Zentriere das Spielbereich
        game_area.x = (window_w - GAME_WIDTH) // 2
        game_area.y = (window_h - GAME_HEIGHT) // 2
    else:
        window_w, window_h = 800, 600
        screen = pygame.display.set_mode((window_w, window_h))
        # Zentriere das Spielbereich
        game_area.x = (window_w - GAME_WIDTH) // 2
        game_area.y = (window_h - GAME_HEIGHT) // 2

    save_settings()


def game():
    global game_state, HighScore, score, has_moved, window_focused, upload_status, dt
    global player_img, pipe_up_img, pipe_down_img, ground_img, bg_img, current_theme, current_difficulty_preset, fullscreen

    bg_x_pos = 0
    ground_x_pos = 0

    player, pipes = reset_game()

    # Variablen für die Buttons
    start_screen_buttons = None
    settings_buttons = None
    theme_buttons = None

    while True:
        dt = clock.tick(fps) / 1000.0
        mouse_pos = pygame.mouse.get_pos()

        # Aktuelle Schwierigkeit berechnen
        current_velocity, current_gap, current_spacing = update_difficulty()

        # Event handling für alle Zustände
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # Überprüfen, ob das Fenster den Fokus verliert oder erhält
            if event.type == pygame.ACTIVEEVENT:
                if event.gain == 0:  # Fenster hat Fokus verloren
                    window_focused = False
                    if game_state == 2:  # Nur pausieren, wenn im Spiel
                        game_state = 4
                else:  # Fenster hat Fokus zurückerhalten
                    window_focused = True

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F12:
                    # Passwort abfragen
                    if show_password_dialog():
                        show_admin_editor()

                if game_state == 0:  # Start Screen
                    if event.key == pygame.K_SPACE:
                        game_state = 1  # Hauptmenü

                elif game_state == 1:  # Hauptmenü
                    if event.key == pygame.K_SPACE:
                        player, pipes = reset_game()
                        game_state = 2  # Spiel starten
                    elif event.key == pygame.K_s:  # Einstellungen
                        game_state = 6
                    elif event.key == pygame.K_t:  # Theme-Auswahl
                        game_state = 7
                    elif event.key == pygame.K_u and HighScore > 0:  # Upload mit U-Taste
                        if show_upload_dialog():
                            game_state = 5  # Upload-Bestätigungsbildschirm

                elif game_state == 2:  # Spielzustand
                    has_moved = True
                    if event.key == pygame.K_SPACE:
                        pygame.mixer.Sound.play(woosh_sfx)
                        player.jump()
                    if event.key == pygame.K_p:  # Pause with P key
                        game_state = 4
                    if event.key == pygame.K_ESCAPE:  # Zurück zum Hauptmenü
                        game_state = 1

                elif game_state == 3:  # Death Screen
                    if event.key == pygame.K_RETURN:
                        # Spiel zurücksetzen
                        player, pipes = reset_game()
                        game_state = 2
                    elif event.key == pygame.K_b:  # Zurück zum Hauptmenü
                        game_state = 1

                elif game_state == 4:  # Pause Screen
                    if event.key == pygame.K_SPACE or event.key == pygame.K_p:
                        game_state = 2  # Resume game
                    elif event.key == pygame.K_b:  # Zurück zum Hauptmenü
                        game_state = 1

                elif game_state == 5:  # Upload-Bestätigung
                    if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                        game_state = 1  # Zurück zum Hauptmenü

            if event.type == pygame.MOUSEBUTTONDOWN:
                if game_state == 0 and start_screen_buttons is not None:  # Start Screen
                    start_button, settings_button, theme_button = start_screen_buttons
                    if start_button.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        game_state = 1
                    elif settings_button.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        game_state = 6
                    elif theme_button.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        game_state = 7

                elif game_state == 1:  # Hauptmenü
                    # Klick irgendwo startet das Spiel
                    player, pipes = reset_game()
                    game_state = 2
                    has_moved = True

                elif game_state == 2:  # Spiel
                    # Klick lässt den Vogel springen
                    pygame.mixer.Sound.play(woosh_sfx)
                    player.jump()

                elif game_state == 3:  # Tod
                    # Klick startet das Spiel neu
                    player, pipes = reset_game()
                    game_state = 2
                    has_moved = True

                elif game_state == 4:  # Pause
                    # Klick setzt das Spiel fort
                    game_state = 2

                elif game_state == 6 and settings_buttons is not None:  # Einstellungen
                    back_button, normal_button, hard_button, hardcore_button, fullscreen_button = settings_buttons

                    if back_button.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        game_state = 1
                    elif normal_button.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        current_difficulty_preset = "Normal"
                        save_settings()
                    elif hard_button.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        current_difficulty_preset = "Schwer"
                        save_settings()
                    elif hardcore_button.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        current_difficulty_preset = "Hardcore"
                        save_settings()
                    elif fullscreen_button.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        toggle_fullscreen()

                elif game_state == 7 and theme_buttons is not None:  # Theme-Auswahl
                    back_button, theme_buttons_dict = theme_buttons

                    if back_button.collidepoint(mouse_pos):
                        pygame.mixer.Sound.play(select_sfx)
                        game_state = 1
                    else:
                        for theme_name, button_rect in theme_buttons_dict.items():
                            if button_rect.collidepoint(mouse_pos):
                                pygame.mixer.Sound.play(select_sfx)
                                current_theme = theme_name
                                # Theme-Bilder neu laden
                                theme_images = load_theme_images(current_theme)
                                player_img = theme_images["player_img"]
                                pipe_up_img = theme_images["pipe_up_img"]
                                pipe_down_img = theme_images["pipe_down_img"]
                                ground_img = theme_images["ground_img"]
                                bg_img = theme_images["bg_img"]
                                # Spieler-Image aktualisieren
                                player.rotated_image = player_img
                                player.mask = pygame.mask.from_surface(player_img)
                                save_settings()
                                break

        # Spiel-Logik
        if game_state == 2 and has_moved:
            player.update()

            # Kollisionserkennung mit Masken
            if check_collision(player, pipes):
                if score > HighScore:
                    HighScore = score
                    save_settings()
                pygame.mixer.Sound.play(slap_sfx)
                game_state = 3

            for pipe in pipes:
                pipe.velocity = current_velocity  # Aktualisiere Geschwindigkeit für alle Rohre
                pipe.update()

            # Entferne Rohre, die den Bildschirm verlassen haben
            if pipes and pipes[0].x < -pipe_up_img.get_width():
                pipes.pop(0)
                # Füge ein neues Rohr hinzu
                last_pipe_x = pipes[-1].x if pipes else GAME_WIDTH
                # Stelle sicher, dass die neuen Rohre korrekt positioniert sind
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
        # Zeichne den Spielbereich-Hintergrund
        screen.fill(themes[current_theme]["bg_color"])

        # Zeichne einen Rahmen um den Spielbereich (optional, zur Verdeutlichung)
        pygame.draw.rect(screen, (50, 50, 50), game_area, 2)

        # Zeichne den Hintergrund im Spielbereich
        # Clip-Bereich setzen, um sicherzustellen, dass nichts außerhalb gezeichnet wird
        screen.set_clip(game_area)

        screen.blit(bg_img, (game_area.x + bg_x_pos, game_area.y))
        screen.blit(bg_img, (game_area.x + bg_x_pos + bg_width, game_area.y))

        # Zeichne den Boden im Spielbereich
        screen.blit(ground_img, (game_area.x + ground_x_pos, game_area.y + ACTUAL_PLAY_HEIGHT))
        screen.blit(ground_img, (game_area.x + ground_x_pos + bg_width, game_area.y + ACTUAL_PLAY_HEIGHT))

        if game_state >= 2:  # Don't draw pipes in menus
            for pipe in pipes:
                pipe.draw()

        if game_state == 2:  # Only draw player during gameplay
            player.draw()

        # Clip-Bereich zurücksetzen
        screen.set_clip(None)

        if game_state >= 2:  # Don't show scoreboard in menus
            scoreboard()

        # Overlays zeichnen
        if game_state == 0:
            start_screen_buttons = draw_start_screen()
        elif game_state == 1:
            draw_main_menu()
        elif game_state == 3:
            draw_death_screen()
        elif game_state == 4:
            draw_pause_screen()
        elif game_state == 5:
            # Upload-Bestätigungsbildschirm
            overlay = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))

            status = font_small.render(upload_status, True, themes[current_theme]["text_color"])
            continue_text = font_small.render("Press SPACE to continue", True, themes[current_theme]["text_color"])

            screen.blit(status, (window_w // 2 - status.get_width() // 2, window_h // 2 - 20))
            screen.blit(continue_text, (window_w // 2 - continue_text.get_width() // 2, window_h // 2 + 20))
        elif game_state == 6:
            settings_buttons = draw_settings_screen()
        elif game_state == 7:
            theme_buttons = draw_theme_selection()

        pygame.display.flip()
        clock.tick(fps)


game()