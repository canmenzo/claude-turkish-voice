"""
voicetr hotkey daemon — Ctrl+Alt+V → /voicetr komutunu yazar.
Arka planda çalışır, Windows başlangıcında otomatik başlatılabilir.
"""
import sys
import time
import keyboard
import pyautogui

pyautogui.PAUSE = 0

def trigger():
    time.sleep(0.08)          # tuşun bırakılmasını bekle
    pyautogui.write('/voicetr', interval=0.02)
    pyautogui.press('enter')

keyboard.add_hotkey('ctrl+alt+v', trigger, suppress=True)
keyboard.wait()               # arka planda bekle
