#!/usr/bin/env python3
"""
Direct LED hardware test - Tests if LEDs are receiving signals
"""

import serial
import time

PORT = '/dev/cu.usbserial-A5069RR4'
BAUD = 9600

def test_leds():
    try:
        print("🔌 Connecting to Arduino...")
        ser = serial.Serial(PORT, BAUD, timeout=3)
        time.sleep(2)  # Wait for Arduino to initialize
        
        print("✓ Connected!")
        print("\n" + "="*50)
        
        # Test 1: Just turn on green LED
        print("\n[TEST 1] Sending GATE_OPEN command...")
        print("→ Expecting: Green LED should light up for 1.5 seconds")
        ser.write(b'GATE_OPEN\n')
        response = ser.readline().decode('utf-8').strip()
        print(f"← Arduino responded: {response}")
        time.sleep(2)
        
        # Test 2: Just turn on red LED
        print("\n[TEST 2] Sending GATE_CLOSE command...")
        print("→ Expecting: Red LED should light up for 1.5 seconds")
        ser.write(b'GATE_CLOSE\n')
        response = ser.readline().decode('utf-8').strip()
        print(f"← Arduino responded: {response}")
        time.sleep(2)
        
        # Test 3: STATUS check
        print("\n[TEST 3] Sending STATUS command...")
        ser.write(b'STATUS\n')
        response = ser.readline().decode('utf-8').strip()
        print(f"← Arduino responded: {response}")
        
        print("\n" + "="*50)
        print("\n✓ Test complete!")
        print("\nDid you see the LEDs light up?")
        print("  - GREEN during GATE_OPEN?")
        print("  - RED during GATE_CLOSE?")
        
        ser.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_leds()
