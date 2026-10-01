"""
Generates demo crisis assets (images and audio files) for live hackathon judging.
"""

import os
import cv2
import numpy as np
import wave
import struct
import math
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "demo_assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

def create_demo_wav(path, duration=2.5, freq=300):
    sample_rate = 16000
    total = int(sample_rate * duration)
    with wave.open(str(path), 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for i in range(total):
            f = freq + 80.0 * math.sin(2 * math.pi * 3 * (i / sample_rate))
            val = int(8000.0 * math.sin(2 * math.pi * f * (i / sample_rate)))
            frames.extend(struct.pack('<h', val))
        wf.writeframes(frames)
    print(f"Created audio: {path.name}")

def create_demo_images():
    # 1. Fire Crisis Image
    fire_img = np.zeros((400, 600, 3), dtype=np.uint8)
    # Background dark smoke
    fire_img[:] = (30, 30, 35)
    # Flames gradient (BGR: red/orange/yellow)
    for y in range(150, 400):
        intensity = (y - 150) / 250.0
        fire_img[y, :] = (int(10 + 20 * intensity), int(80 + 100 * intensity), int(220 + 35 * intensity))
    cv2.putText(fire_img, "EMERGENCY: INDUSTRIAL FIRE SECTOR 7", (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.imwrite(str(ASSETS_DIR / "fire_crisis.jpg"), fire_img)

    # 2. Flood Disaster Image
    flood_img = np.zeros((400, 600, 3), dtype=np.uint8)
    flood_img[:] = (160, 110, 45) # Murky flood water
    cv2.putText(flood_img, "CRISIS: SECTOR 18 RIVER BASIN FLOOD", (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.imwrite(str(ASSETS_DIR / "flood_crisis.jpg"), flood_img)

    # 3. Collapse Hazard Image
    collapse_img = np.zeros((400, 600, 3), dtype=np.uint8)
    # Rubble noise
    noise = np.random.randint(40, 180, (400, 600, 3), dtype=np.uint8)
    collapse_img = cv2.addWeighted(collapse_img, 0.5, noise, 0.5, 0)
    cv2.putText(collapse_img, "HAZARD: STRUCTURAL COLLAPSE", (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.imwrite(str(ASSETS_DIR / "collapse_hazard.jpg"), collapse_img)

    print("Created demo crisis images.")

if __name__ == "__main__":
    create_demo_wav(ASSETS_DIR / "flood_voice_alert.wav", duration=2.0, freq=340)
    create_demo_wav(ASSETS_DIR / "medical_voice_alert.wav", duration=2.0, freq=440)
    create_demo_wav(ASSETS_DIR / "fire_voice_alert.wav", duration=2.0, freq=520)
    create_demo_images()
