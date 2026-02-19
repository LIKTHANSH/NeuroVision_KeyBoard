"""
NeuroVision - Virtual Keyboard
Upgraded from dlib to MediaPipe FaceMesh.
Same logic: gaze selects left/right keyboard, blink types the highlighted letter.
Author: Likthansh Anisetti
"""

import cv2
import numpy as np
import mediapipe as mp
import time
from math import hypot

# ─── Sound (optional - comment out if no sound files) ────────────────────────
try:
    import pyglet
    sound       = pyglet.media.load("sound.wav",  streaming=False)
    left_sound  = pyglet.media.load("left.wav",   streaming=False)
    right_sound = pyglet.media.load("right.wav",  streaming=False)
    SOUND_ON = True
except Exception:
    SOUND_ON = False
    print("[INFO] Sound files not found. Running without audio.")

# ─── MediaPipe Setup ──────────────────────────────────────────────────────────
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True, max_num_faces=1)

cap = cv2.VideoCapture(0)

cv2.namedWindow("NeuroVision Keyboard", cv2.WINDOW_NORMAL)
cv2.namedWindow("Frame",                cv2.WINDOW_NORMAL)
cv2.namedWindow("Board",                cv2.WINDOW_NORMAL)
cv2.resizeWindow("NeuroVision Keyboard", 1000, 600)
cv2.resizeWindow("Frame",               400,  300)
cv2.resizeWindow("Board",               1000, 150)

# ─── Color Palette (elegant dark theme) ──────────────────────────────────────
BG          = (30,  30,  30)   # dark background
KEY_COLOR   = (50,  50,  60)   # default key
KEY_ACTIVE  = (100, 180, 255)  # highlighted key (light blue)
KEY_BORDER  = (80,  80, 100)   # key border
TEXT_COLOR  = (230, 230, 230)  # key text
TEXT_ACTIVE = (10,  10,  10)   # text on highlighted key
BOARD_BG    = (20,  20,  20)
BOARD_TEXT  = (100, 220, 100)  # green typed text

# ─── Keyboard Layout ──────────────────────────────────────────────────────────
keys_set_1 = {0:"Q",1:"W",2:"E",3:"R",4:"T",
              5:"A",6:"S",7:"D",8:"F",9:"G",
              10:"Z",11:"X",12:"C",13:"V",14:"<"}

keys_set_2 = {0:"Y",1:"U",2:"I",3:"O",4:"P",
              5:"H",6:"J",7:"K",8:"L",9:"_",
              10:"V",11:"B",12:"N",13:"M",14:"<"}

keyboard = np.zeros((600, 1000, 3), np.uint8)
board    = np.zeros((150, 1000,  3), np.uint8)

COLS, ROWS = 5, 3
KEY_W, KEY_H = 1000 // COLS, 600 // ROWS

def draw_keyboard(keys_set, letter_index):
    keyboard[:] = BG
    for i in range(15):
        col = i % COLS
        row = i // COLS
        x, y = col * KEY_W, row * KEY_H
        pad = 8

        is_active = (i == letter_index)
        bg    = KEY_ACTIVE if is_active else KEY_COLOR
        fg    = TEXT_ACTIVE if is_active else TEXT_COLOR

        # Rounded-look rectangle
        cv2.rectangle(keyboard, (x+pad, y+pad), (x+KEY_W-pad, y+KEY_H-pad), KEY_BORDER, -1)
        cv2.rectangle(keyboard, (x+pad+2, y+pad+2), (x+KEY_W-pad-2, y+KEY_H-pad-2), bg, -1)

        text = keys_set[i]
        font_scale = 5 if text != "<" else 3.5
        thickness  = 4
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
        tx = x + (KEY_W - tw) // 2
        ty = y + (KEY_H + th) // 2
        cv2.putText(keyboard, text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, font_scale, fg, thickness, cv2.LINE_AA)

def draw_menu(keyboard_selected):
    keyboard[:] = BG
    w, h = 1000, 600

    # Left panel
    l_bg = (70, 130, 200) if keyboard_selected == "left"  else (50, 50, 60)
    r_bg = (70, 130, 200) if keyboard_selected == "right" else (50, 50, 60)
    l_fg = (10, 10, 10)   if keyboard_selected == "left"  else (200, 200, 200)
    r_fg = (10, 10, 10)   if keyboard_selected == "right" else (200, 200, 200)

    cv2.rectangle(keyboard, (10, 10),       (w//2-10, h-10), l_bg, -1)
    cv2.rectangle(keyboard, (w//2+10, 10),  (w-10,    h-10), r_bg, -1)

    for text, fg, cx in [("LEFT", l_fg, w//4), ("RIGHT", r_fg, 3*w//4)]:
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 6, 8)
        cv2.putText(keyboard, text, (cx - tw//2, h//2 + th//2),
                    cv2.FONT_HERSHEY_SIMPLEX, 6, fg, 8, cv2.LINE_AA)

    # Subtitle
    hint = "Look LEFT or RIGHT for 1 second to choose keyboard"
    (tw, _), _ = cv2.getTextSize(hint, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
    cv2.putText(keyboard, hint, ((w-tw)//2, h-20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (150, 150, 150), 2, cv2.LINE_AA)

    time.sleep(0.05)

def draw_board(text):
    board[:] = BOARD_BG
    cv2.rectangle(board, (0, 0), (999, 149), (50, 50, 60), 2)
    display = text if len(text) <= 40 else "..." + text[-40:]
    cv2.putText(board, display, (20, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 2, BOARD_TEXT, 3, cv2.LINE_AA)

# ─── MediaPipe Landmark Indices ───────────────────────────────────────────────
# EAR (blink): using same 6-point outline approach
LEFT_EYE_EAR  = [33,  160, 158, 133, 153, 144]
RIGHT_EYE_EAR = [362, 385, 387, 263, 373, 380]

# Gaze: iris center vs eye corners
LEFT_IRIS   = 468   # MediaPipe refined iris center
RIGHT_IRIS  = 473
LEFT_CORNER_L,  LEFT_CORNER_R  = 33,  133
RIGHT_CORNER_L, RIGHT_CORNER_R = 362, 263

def get_ear(landmarks, eye_idxs, w, h):
    pts = [(int(landmarks[i].x * w), int(landmarks[i].y * h)) for i in eye_idxs]
    A = hypot(pts[1][0]-pts[5][0], pts[1][1]-pts[5][1])
    B = hypot(pts[2][0]-pts[4][0], pts[2][1]-pts[4][1])
    C = hypot(pts[0][0]-pts[3][0], pts[0][1]-pts[3][1])
    return (A + B) / (2.0 * C + 1e-6)

def get_gaze_ratio(landmarks, iris_idx, corner_l, corner_r, w, h):
    """Returns ratio of iris position: <1 means looking right, >1 means looking left."""
    ix = landmarks[iris_idx].x * w
    lx = landmarks[corner_l].x * w
    rx = landmarks[corner_r].x * w
    eye_width = rx - lx + 1e-6
    ratio = (ix - lx) / eye_width  # 0=far left, 1=far right
    return ratio

# ─── State ────────────────────────────────────────────────────────────────────
frames                = 0
letter_index          = 0
blinking_frames       = 0
frames_to_blink       = 6
frame_active_letter   = 9
text                  = ""
keyboard_selected     = "left"
last_keyboard_selected= "left"
select_keyboard_menu  = True
keyboard_selection_frames = 0

EAR_BLINK_THRESH = 0.20   # below this = blink

print("[RUNNING] NeuroVision Virtual Keyboard. Press ESC to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)

    frames += 1
    blink_detected_this_frame = False

    if results.multi_face_landmarks:
        lm = results.multi_face_landmarks[0].landmark

        # ── Blink detection ──
        left_ear  = get_ear(lm, LEFT_EYE_EAR,  w, h)
        right_ear = get_ear(lm, RIGHT_EYE_EAR, w, h)
        ear = (left_ear + right_ear) / 2.0

        if ear < EAR_BLINK_THRESH:
            blinking_frames += 1
            frames -= 1
            cv2.putText(frame, "BLINK", (50, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 255, 100), 5, cv2.LINE_AA)
        else:
            blinking_frames = 0

        # ── Gaze detection ──
        left_gaze  = get_gaze_ratio(lm, LEFT_IRIS,  LEFT_CORNER_L,  LEFT_CORNER_R,  w, h)
        right_gaze = get_gaze_ratio(lm, RIGHT_IRIS, RIGHT_CORNER_L, RIGHT_CORNER_R, w, h)
        gaze = (left_gaze + right_gaze) / 2.0
        # gaze < 0.45 → looking right, gaze > 0.55 → looking left
        if gaze < 0.45:
            current_gaze = "right"
        elif gaze > 0.55:
            current_gaze = "left"
        else:
            current_gaze = keyboard_selected  # hold

        # Draw gaze indicator on frame
        label = f"Gaze: {current_gaze.upper()}  EAR:{ear:.2f}"
        cv2.putText(frame, label, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 200, 255), 2, cv2.LINE_AA)

        # ── Menu selection logic ──
        if select_keyboard_menu:
            if current_gaze != keyboard_selected:
                keyboard_selected = current_gaze
                keyboard_selection_frames = 0
            else:
                keyboard_selection_frames += 1

            if keyboard_selection_frames >= 15:
                select_keyboard_menu = False
                if SOUND_ON:
                    (right_sound if keyboard_selected == "right" else left_sound).play()
                frames = 0
                keyboard_selection_frames = 0

        else:
            # ── Typing logic (blink selects key) ──
            if blinking_frames == frames_to_blink:
                active_letter = (keys_set_1 if keyboard_selected == "left" else keys_set_2)[letter_index]
                if active_letter == "<":
                    text = text[:-1]
                elif active_letter == "_":
                    text += " "
                else:
                    text += active_letter
                if SOUND_ON:
                    sound.play()
                select_keyboard_menu = True
                blinking_frames = 0

    # ── Draw keyboard ──
    keys_set = keys_set_1 if keyboard_selected == "left" else keys_set_2

    if select_keyboard_menu:
        draw_menu(keyboard_selected)
    else:
        if frames == frame_active_letter:
            letter_index = (letter_index + 1) % 15
            frames = 0
        draw_keyboard(keys_set, letter_index)
        time.sleep(0.05)

    # ── Board and loading bar ──
    draw_board(text)

    pct = blinking_frames / frames_to_blink
    bar_x = int(w * pct)
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, h-40), (bar_x, h), (100, 180, 255), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
    cv2.putText(frame, "Hold blink to type", (10, h-10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)

    cv2.imshow("NeuroVision Keyboard", keyboard)
    cv2.imshow("Frame",                frame)
    cv2.imshow("Board",                board)

    cv2.moveWindow("NeuroVision Keyboard", 0,    0)
    cv2.moveWindow("Frame",               1010,  0)
    cv2.moveWindow("Board",               0,     610)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
