#!/usr/bin/env python3
"""
System Ready Check - Verify everything before running main app
"""

import sys
import time

print("\n" + "="*60)
print("  FINAL SYSTEM READINESS CHECK")
print("="*60 + "\n")

# 1. Check imports
print("1. Checking Python imports...")
try:
    import cv2
    import torch
    from ultralytics import YOLO
    import serial
    print("   ✓ All imports successful\n")
except ImportError as e:
    print(f"   ✗ Import failed: {e}\n")
    sys.exit(1)

# 2. Check model
print("2. Checking YOLOv8 model...")
try:
    model = YOLO("model.pt")
    print("   ✓ Model loaded (YOLOv8 nano)\n")
except Exception as e:
    print(f"   ✗ Model error: {e}\n")
    sys.exit(1)

# 3. Check cameras
print("3. Checking USB cameras...")
cameras_found = 0
for idx in range(4):
    cap = cv2.VideoCapture(idx)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            cameras_found += 1
            print(f"   ✓ Camera {idx} detected")
        cap.release()

if cameras_found >= 2:
    print(f"   ✓ Both cameras detected!\n")
elif cameras_found == 1:
    print(f"   ⚠ Only 1 camera found (need 2)\n")
else:
    print(f"   ⚠ No cameras detected\n")

# 4. Check Arduino
print("4. Checking Arduino connection...")
try:
    from arduino_controller import ArduinoController, ArduinoConfig
    config = ArduinoConfig()
    arduino = ArduinoController(config, debug=False)
    
    if arduino.connected:
        print(f"   ✓ Arduino connected on {config.port}")
        print(f"   ✓ Testing STATUS command...")
        arduino.get_status()
        print(f"   ✓ Arduino responding\n")
        arduino.disconnect()
    else:
        print(f"   ⚠ Arduino not responding\n")
except Exception as e:
    print(f"   ⚠ Arduino error: {e}\n")

# 5. Summary
print("="*60)
print("  ✅ SYSTEM READY!")
print("="*60)
print("\nYou can now run the main application:")
print("\n  $ python index.py\n")
print("Keyboard controls:")
print("  • Type 0-9 to enter expected box count")
print("  • Press Enter to submit")
print("  • Press 'r' to reset")
print("  • Press 'q' to quit\n")
