#!/usr/bin/env python3
"""
Arduino Hardware Troubleshooting Script
Diagnoses power, USB detection, and driver issues
"""

import subprocess
import sys

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def check_usb_devices():
    """Check if Arduino appears in USB devices"""
    print_header("Step 1: Check USB Device Detection")
    
    try:
        # Use system_profiler which is more reliable on macOS
        result = subprocess.run(
            ["system_profiler", "SPUSBDataType"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        output = result.stdout
        
        # Look for Arduino-related devices
        arduino_keywords = ["Arduino", "CH340", "FTDI", "FT232", "Uno", "ATmega", "Composite Device"]
        found_arduino = False
        
        for line in output.split('\n'):
            for keyword in arduino_keywords:
                if keyword.lower() in line.lower():
                    print(f"  ✓ Found: {line.strip()}")
                    found_arduino = True
        
        if not found_arduino:
            print("  ⚠ No Arduino-related devices detected in USB list")
            print("\n  This could mean:")
            print("    1. USB cable not connected")
            print("    2. Arduino not powered")
            print("    3. Driver not installed (CH340/FTDI)")
            print("    4. Arduino is damaged")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error checking USB devices: {e}")
        return False

def check_serial_ports():
    """Check available serial ports"""
    print_header("Step 2: Check Serial Ports (/dev/tty.*)")
    
    try:
        result = subprocess.run(
            "ls -la /dev/tty.*",
            capture_output=True,
            text=True,
            shell=True
        )
        
        if result.returncode == 0:
            ports = result.stdout.strip().split('\n')
            print(f"  Found {len(ports)} serial ports:\n")
            for port in ports:
                if port:
                    parts = port.split()
                    if parts:
                        print(f"    - {parts[-1]}")
            return True
        else:
            print("  ⚠ No serial ports found")
            print("    This suggests the Arduino driver is not installed")
            return False
            
    except Exception as e:
        print(f"  ✗ Error listing serial ports: {e}")
        return False

def check_usb_tty():
    """Specifically check /dev/tty.usbserial and /dev/tty.usbmodem*"""
    print_header("Step 3: Check Specific Arduino Ports")
    
    ports_to_check = [
        "/dev/tty.usbserial*",
        "/dev/tty.usbmodem*",
        "/dev/tty.SLAB_USBtoUART",
    ]
    
    found_any = False
    for port_pattern in ports_to_check:
        try:
            result = subprocess.run(
                f"ls -la {port_pattern} 2>/dev/null",
                capture_output=True,
                text=True,
                shell=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                ports = result.stdout.strip().split('\n')
                for port in ports:
                    if port:
                        parts = port.split()
                        port_name = parts[-1] if parts else ""
                        print(f"  ✓ Found Arduino port: {port_name}")
                        found_any = True
        except:
            pass
    
    if not found_any:
        print("  ⚠ No Arduino-specific ports found")
        print("\n  This indicates:")
        print("    - Driver issue (CH340/FTDI not installed)")
        print("    - USB connection problem")
        print("    - Arduino power issue")
    
    return found_any

def list_all_dev_tty():
    """List all /dev/tty devices"""
    print_header("Step 4: List ALL /dev/tty Devices")
    
    try:
        result = subprocess.run(
            "ls -1 /dev/tty.* 2>/dev/null || echo 'None'",
            capture_output=True,
            text=True,
            shell=True
        )
        
        ports = result.stdout.strip().split('\n')
        if ports and ports[0] != 'None':
            print(f"  Total devices: {len(ports)}\n")
            for port in ports:
                print(f"    {port}")
            return ports
        else:
            print("  ✗ No /dev/tty.* devices found")
            return []
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return []

def main():
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "  ARDUINO HARDWARE TROUBLESHOOTING".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")
    
    print("\n⚠️  If you see NO LIGHTS on Arduino, this typically means:")
    print("   1. Power issue (broken USB/cable)")
    print("   2. Driver missing (CH340/FTDI chip)")
    print("   3. Arduino is damaged")
    print("   4. USB port on Mac not working")
    
    # Run diagnostics
    usb_detected = check_usb_devices()
    serial_found = check_serial_ports()
    arduino_ports = check_usb_tty()
    all_ports = list_all_dev_tty()
    
    # Summary
    print_header("DIAGNOSIS SUMMARY")
    
    if usb_detected:
        print("✓ Arduino detected in USB devices")
    else:
        print("✗ Arduino NOT detected in USB devices")
    
    if serial_found or all_ports:
        print(f"✓ Serial ports available: {len(all_ports if all_ports else [])}")
    else:
        print("✗ No serial ports available")
    
    if arduino_ports:
        print("✓ Arduino-specific ports found")
    else:
        print("✗ Arduino-specific ports NOT found (driver issue likely)")
    
    print_header("RECOMMENDED NEXT STEPS")
    
    if not usb_detected:
        print("1. CHECK PHYSICAL CONNECTION:")
        print("   - Is USB cable plugged into Mac?")
        print("   - Is USB cable plugged into Arduino?")
        print("   - Try different USB port on Mac")
        print("   - Try different USB cable")
        print("\n2. CHECK POWER:")
        print("   - Should see LED light up on Arduino (usually red LED)")
        print("   - If no light: Arduino may be damaged")
        print("   - Try different USB cable (might be data-only)")
        
    if usb_detected and not arduino_ports:
        print("1. INSTALL DRIVER:")
        print("   - Arduino UNO uses CH340 or FTDI chip")
        print("   - Download driver: https://github.com/WCHSoftware/ch34x_install_macos")
        print("   - Or: https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers")
        print("   - After install, restart Mac")
        
    print("\n3. VERIFY IN ARDUINO IDE:")
    print("   - Open Arduino IDE")
    print("   - Tools → Port → Look for Arduino entry")
    print("   - This confirms driver is installed")

    print("\n4. TEST WITH SIMPLE BLINK:")
    print("   - Upload blink sketch to verify Arduino works")
    print("   - File → Examples → Basics → Blink")
    print("   - If blink works, Arduino is fine (driver was missing)")

    return 0 if (usb_detected and arduino_ports) else 1

if __name__ == "__main__":
    sys.exit(main())
