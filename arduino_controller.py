"""
Arduino IoT Controller Module
Manages serial communication with Arduino UNO for gate control and LED feedback
"""

import serial
import time
import threading
from typing import Optional, Callable
from dataclasses import dataclass


@dataclass
class ArduinoConfig:
    """Arduino connection configuration"""
    port: str = "/dev/cu.usbserial-A5069RR4"  # macOS default, will auto-detect
    baudrate: int = 9600
    timeout: float = 3.0
    retry_attempts: int = 3
    retry_delay: float = 0.5


class ArduinoController:
    """Controls Arduino UNO for gate servo and LED indicators"""
    
    def __init__(self, config: Optional[ArduinoConfig] = None, debug: bool = False):
        """
        Initialize Arduino controller
        
        Args:
            config: Arduino connection configuration
            debug: Enable debug logging
        """
        self.config = config or ArduinoConfig()
        self.debug = debug
        self.serial_port: Optional[serial.Serial] = None
        self.connected = False
        self.lock = threading.Lock()
        self._connect()
    
    def _connect(self) -> bool:
        """Establish serial connection to Arduino"""
        for attempt in range(self.config.retry_attempts):
            try:
                self.serial_port = serial.Serial(
                    port=self.config.port,
                    baudrate=self.config.baudrate,
                    timeout=self.config.timeout
                )
                time.sleep(1.0)  # Give Arduino time to initialize after connection
                
                # Clear any leftover data
                self.serial_port.reset_input_buffer()
                self.serial_port.reset_output_buffer()
                
                # Test connection
                if self._send_command("STATUS"):
                    self.connected = True
                    if self.debug:
                        print(f"✓ Arduino connected on {self.config.port}")
                    return True
                    
            except (serial.SerialException, FileNotFoundError) as e:
                if self.debug:
                    print(f"Attempt {attempt + 1}: {e}")
                if attempt < self.config.retry_attempts - 1:
                    time.sleep(self.config.retry_delay)
        
        if self.debug:
            print(f"✗ Failed to connect to Arduino on {self.config.port}")
        return False
    
    def _send_command(self, command: str, wait_response: bool = True) -> bool:
        """
        Send command to Arduino
        
        Args:
            command: Command to send (e.g., "GATE_OPEN", "GATE_CLOSE")
            wait_response: Wait for Arduino response
            
        Returns:
            True if successful or no response expected
        """
        if not self.serial_port or not self.serial_port.is_open:
            if self.debug:
                print("✗ Arduino not connected")
            return False
        
        try:
            with self.lock:
                # Send command
                self.serial_port.write(f"{command}\n".encode('utf-8'))
                
                if wait_response:
                    # Read response
                    response = self.serial_port.readline().decode('utf-8').strip()
                    
                    if self.debug:
                        print(f"→ Sent: {command}")
                        print(f"← Received: {response}")
                    
                    return response.startswith("OK")
                else:
                    if self.debug:
                        print(f"→ Sent: {command} (no response expected)")
                    return True
                    
        except Exception as e:
            if self.debug:
                print(f"✗ Serial error: {e}")
            self.connected = False
            return False
    
    def open_gate(self) -> bool:
        """Open the gate and light green LED"""
        return self._send_command("GATE_OPEN")
    
    def close_gate(self) -> bool:
        """Close the gate and light red LED"""
        return self._send_command("GATE_CLOSE")
    
    def test_connection(self) -> bool:
        """Test Arduino connection and perform self-test"""
        return self._send_command("TEST")
    
    def get_status(self) -> bool:
        """Check Arduino status"""
        return self._send_command("STATUS")
    
    def disconnect(self) -> None:
        """Safely disconnect from Arduino"""
        try:
            with self.lock:
                if self.serial_port and self.serial_port.is_open:
                    self.serial_port.close()
                    self.connected = False
                    if self.debug:
                        print("✓ Arduino disconnected")
        except Exception as e:
            if self.debug:
                print(f"✗ Disconnect error: {e}")
    
    def __del__(self):
        """Ensure proper cleanup"""
        self.disconnect()


def find_arduino_port() -> Optional[str]:
    """
    Auto-detect Arduino serial port
    Works on macOS, Linux, and Windows
    
    Returns:
        Serial port string or None if not found
    """
    import platform
    import glob
    
    system = platform.system()
    
    try:
        if system == "Darwin":  # macOS
            # Check both /dev/tty.* and /dev/cu.* variants
            for dev_pattern in ["/dev/cu.*", "/dev/tty.*"]:
                ports = glob.glob(dev_pattern)
                for port in ports:
                    # Look for common Arduino serial patterns
                    for pattern in ['usbserial', 'usbmodem', 'SLAB_USBtoUART', 'CH34']:
                        if pattern in port:
                            return port
        
        elif system == "Linux":
            ports = glob.glob("/dev/ttyUSB*")
            if ports:
                return ports[0]
        
        elif system == "Windows":
            import winreg
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "HARDWARE\\DEVICEMAP\\SERIALCOMM")
                for i in range(winreg.QueryInfoKey(key)[1]):
                    name, value, _ = winreg.EnumValue(key, i)
                    if 'Arduino' in name:
                        return value
            except:
                pass
    
    except Exception as e:
        print(f"Error detecting Arduino port: {e}")
    
    return None
