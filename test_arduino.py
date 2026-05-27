#!/usr/bin/env python3
"""
Arduino Connection Test - Verify Arduino communication
"""

import time
import sys
from arduino_controller import ArduinoController, ArduinoConfig, find_arduino_port

def test_arduino_connection():
    """Test Arduino connection and commands"""
    
    print("\n" + "="*60)
    print("  ARDUINO CONNECTION TEST")
    print("="*60 + "\n")
    
    # Step 1: Find Arduino port (check both /dev/tty.* and /dev/cu.*)
    print("Step 1: Detecting Arduino port...")
    port = find_arduino_port()
    
    if not port:
        print("  Could not auto-detect Arduino port")
        print("  Trying common ports manually...")
        
        # Try both tty and cu variants
        for base_port in ["/dev/tty.usbserial-A5069RR4", "/dev/cu.usbserial-A5069RR4",
                          "/dev/tty.usbserial", "/dev/cu.usbserial",
                          "/dev/tty.usbmodem14201", "/dev/cu.usbmodem14201", 
                          "/dev/ttyUSB0"]:
            print(f"    - {base_port}: ", end="")
            try:
                config = ArduinoConfig(port=base_port, timeout=1, retry_attempts=1)
                arduino = ArduinoController(config, debug=False)
                if arduino.connected:
                    print("✓ FOUND")
                    port = base_port
                    break
                else:
                    print("✗ No response")
                    arduino.disconnect()
            except Exception as e:
                print(f"✗ Error")
        
        if not port:
            print("\n  ✗ Failed to find Arduino")
            print("  Please check:")
            print("    1. USB cable is connected")
            print("    2. Arduino sketch is uploaded (arduino_sketch.ino)")
            print("    3. No other application is using the serial port")
            return False
    else:
        print(f"  ✓ Found Arduino on: {port}\n")
    
    # Step 2: Connect to Arduino
    print("Step 2: Connecting to Arduino...")
    try:
        config = ArduinoConfig(port=port)
        arduino = ArduinoController(config, debug=True)
        
        if not arduino.connected:
            print("  ✗ Failed to connect")
            return False
        print("  ✓ Connected\n")
    except Exception as e:
        print(f"  ✗ Connection error: {e}")
        return False
    
    # Step 3: Test commands
    print("Step 3: Testing commands...\n")
    
    commands = [
        ("STATUS", "Check Arduino status"),
        ("GATE_OPEN", "Open gate (Green LED should blink)"),
        ("GATE_CLOSE", "Close gate (Red LED should blink)"),
    ]
    
    for cmd, description in commands:
        print(f"  Command: {cmd}")
        print(f"  ({description})")
        print(f"  Sending...", end=" ")
        
        if arduino._send_command(cmd):
            print("✓ OK\n")
        else:
            print("✗ Failed\n")
    
    # Step 4: Self-test
    print("Step 4: Running Arduino self-test...")
    print("  Sending: TEST")
    print("  (Gate should open/close automatically)...", end=" ")
    
    if arduino._send_command("TEST"):
        print("✓ OK\n")
    else:
        print("✗ Failed\n")
    
    # Cleanup
    print("Step 5: Cleaning up...")
    arduino.close_gate()
    arduino.disconnect()
    print("  ✓ Disconnected\n")
    
    print("="*60)
    print("  ✓ Arduino Test Complete!")
    print("="*60 + "\n")
    
    return True

if __name__ == "__main__":
    success = test_arduino_connection()
    sys.exit(0 if success else 1)
