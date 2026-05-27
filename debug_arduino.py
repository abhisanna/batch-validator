#!/usr/bin/env python3
"""
Debug Arduino Port Detection
"""

import glob
from arduino_controller import find_arduino_port, ArduinoConfig, ArduinoController

print("\n" + "="*60)
print("  DEBUG: Arduino Port Detection")
print("="*60 + "\n")

# Test glob approach
print("Step 1: Testing glob detection...")
for dev_pattern in ["/dev/cu.*", "/dev/tty.*"]:
    ports = glob.glob(dev_pattern)
    print(f"  Pattern '{dev_pattern}': {len(ports)} devices")
    for port in ports:
        if any(p in port for p in ['usbserial', 'usbmodem', 'SLAB', 'CH34']):
            print(f"    ✓ Found: {port}")

# Test find_arduino_port
print("\nStep 2: Testing find_arduino_port()...")
found_port = find_arduino_port()
if found_port:
    print(f"  ✓ Auto-detected: {found_port}")
else:
    print(f"  ✗ Not found via auto-detect")

# Test default config
print("\nStep 3: Testing default ArduinoConfig...")
config = ArduinoConfig()
print(f"  Port: {config.port}")

# Test connection with default port
print("\nStep 4: Testing connection with default port...")
try:
    arduino = ArduinoController(config, debug=True)
    if arduino.connected:
        print(f"  ✓ Connected!")
    else:
        print(f"  ✗ Not connected")
except Exception as e:
    print(f"  ✗ Exception: {e}")

# Test manual ports
print("\nStep 5: Testing manual ports...")
ports_to_try = ["/dev/cu.usbserial-A5069RR4", "/dev/tty.usbserial-A5069RR4"]
for port in ports_to_try:
    print(f"  Trying {port}...", end=" ")
    try:
        config = ArduinoConfig(port=port)
        arduino = ArduinoController(config, debug=False)
        if arduino.connected:
            print("✓")
        else:
            print("✗")
    except Exception as e:
        print(f"✗ ({type(e).__name__})")
