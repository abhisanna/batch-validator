#!/usr/bin/env python3
"""
Direct Arduino Port Test
Tests the specific Arduino port we found
"""

import serial
import time
import subprocess

# Auto-detect or use known port
def get_arduino_port():
    try:
        result = subprocess.run(["arduino-cli", "board", "list"], 
                              capture_output=True, text=True, timeout=5)
        for line in result.stdout.split('\n'):
            if 'usbserial' in line.lower() or 'usbmodem' in line.lower():
                parts = line.split()
                if parts:
                    return parts[0]
    except:
        pass
    
    # Fallback to known port
    return "/dev/cu.usbserial-A5069RR4"

ARDUINO_PORT = get_arduino_port()

print("\n" + "="*60)
print("  TESTING ARDUINO PORT: " + ARDUINO_PORT)
print("="*60 + "\n")

try:
    print("Step 1: Opening serial connection...")
    ser = serial.Serial(ARDUINO_PORT, 9600, timeout=2)
    time.sleep(0.5)
    print("  ✓ Connected!\n")
    
    print("Step 2: Sending STATUS command...")
    ser.write(b"STATUS\n")
    time.sleep(0.5)
    
    response = ser.readline().decode('utf-8').strip()
    print(f"  ✓ Response: {response}\n")
    
    if response:
        print("Step 3: Arduino is responding!")
        print("  ✓ All systems ready!\n")
        print("  You can now run: python index.py\n")
    else:
        print("Step 3: Arduino is connected but not responding")
        print("  ⚠ Need to upload the Arduino sketch first\n")
    
    ser.close()
    print("✓ Connection closed\n")
    
except Exception as e:
    print(f"✗ Error: {e}\n")
    print("Troubleshooting:")
    print("  - Make sure Arduino is connected")
    print("  - Check port is correct: " + ARDUINO_PORT)
    print("  - Try: arduino-cli board list")
