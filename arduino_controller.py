import glob
import platform
import threading
import time
import logging
import sys
from dataclasses import dataclass
from typing import Optional

import serial

def setup_logger(name: str = "arduino") -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        logger.handlers.clear()

    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger


log = setup_logger()

@dataclass
class ArduinoConfig:
    port: str = ""
    baudrate: int = 9600
    timeout: float = 3.0
    retry_attempts: int = 3
    retry_delay: float = 0.5


def find_arduino_port() -> Optional[str]:
    system = platform.system()

    try:
        if system == "Darwin":
            patterns   = ["/dev/cu.*", "/dev/tty.*"]
            keywords   = ["usbserial", "usbmodem", "SLAB_USBtoUART", "CH34"]
        elif system == "Linux":
            patterns   = ["/dev/ttyUSB*", "/dev/ttyACM*"]
            keywords   = [""]
        elif system == "Windows":
            return None
        else:
            return None

        for pattern in patterns:
            for port in glob.glob(pattern):
                if any(kw in port for kw in keywords):
                    log.info(f"Auto-detected Arduino port: {port}")
                    return port

    except Exception as e:
        log.warning(f"Port auto-detection failed: {e}")

    return None

class ArduinoController:
    def __init__(self, config: Optional[ArduinoConfig] = None):
        self.config = config or ArduinoConfig()
        self.port: Optional[serial.Serial] = None
        self.connected = False
        self._lock = threading.Lock()

        self._connect()

    def _connect(self) -> None:
        target_port = self.config.port or find_arduino_port()

        if not target_port:
            log.warning("No Arduino port found — running without hardware.")
            return

        for attempt in range(1, self.config.retry_attempts + 1):
            try:
                self.port = serial.Serial(
                    port     = target_port,
                    baudrate = self.config.baudrate,
                    timeout  = self.config.timeout,
                )

                time.sleep(1.5)
                self.port.reset_input_buffer()
                self.port.reset_output_buffer()

                if self._send("STATUS"):
                    self.connected = True
                    log.info(f"Arduino connected on {target_port}")

                    return

            except (serial.SerialException, FileNotFoundError) as e:
                log.warning(f"Connection attempt {attempt}/{self.config.retry_attempts}: {e}")
                time.sleep(self.config.retry_delay)

        log.error(f"Could not connect to Arduino on {target_port}.")


    def _send(self, command: str) -> bool:
        if not self.port or not self.port.is_open:
            return False
        try:
            with self._lock:
                self.port.write(f"{command}\n".encode("utf-8"))
                response = self.port.readline().decode("utf-8").strip()
                log.debug(f"→ {command}  ← {response}")

                return response.startswith("OK")
        except Exception as e:
            log.error(f"Serial error on '{command}': {e}")
            self.connected = False

            return False

    def open_gate(self) -> bool:
        return self._send("GATE_OPEN")

    def close_gate(self) -> bool:
        return self._send("GATE_CLOSE")

    def idle(self) -> bool:
        return self._send("IDLE")

    def status(self) -> bool:
        return self._send("STATUS")

    def disconnect(self) -> None:
        try:
            with self._lock:
                if self.port and self.port.is_open:
                    self.port.close()
            self.connected = False
            log.info("Arduino disconnected.")
        except Exception as e:
            log.warning(f"Disconnect error: {e}")

    def __del__(self):
        self.disconnect()