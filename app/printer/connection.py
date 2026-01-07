"""Printer connection handlers for Network, Serial, and USB interfaces."""
import socket
from abc import ABC, abstractmethod
from typing import Optional

# Serial support (optional)
try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

# USB support (optional)
try:
    import usb.core
    import usb.util
    USB_AVAILABLE = True
except ImportError:
    USB_AVAILABLE = False


class PrinterConnection(ABC):
    """Abstract base class for printer connections."""

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the printer."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the printer."""
        pass

    @abstractmethod
    def write(self, data: bytes) -> bool:
        """Send data to the printer."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if printer is connected."""
        pass

    def print_data(self, data: bytes) -> bool:
        """Connect, send data, and disconnect."""
        if not self.connect():
            return False
        try:
            return self.write(data)
        finally:
            self.disconnect()


class NetworkPrinter(PrinterConnection):
    """TCP/IP network printer connection."""

    def __init__(self, ip: str, port: int = 9100, timeout: float = 5.0):
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self._socket: Optional[socket.socket] = None

    def connect(self) -> bool:
        """Connect to network printer."""
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self.timeout)
            self._socket.connect((self.ip, self.port))
            return True
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            self._socket = None
            raise ConnectionError(f"Failed to connect to {self.ip}:{self.port}: {e}")

    def disconnect(self) -> None:
        """Close network connection."""
        if self._socket:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None

    def write(self, data: bytes) -> bool:
        """Send data to network printer."""
        if not self._socket:
            raise ConnectionError("Not connected")
        try:
            self._socket.sendall(data)
            return True
        except OSError as e:
            raise ConnectionError(f"Failed to send data: {e}")

    def is_connected(self) -> bool:
        """Check if socket is connected."""
        return self._socket is not None

    def __repr__(self):
        return f"NetworkPrinter({self.ip}:{self.port})"


class SerialPrinter(PrinterConnection):
    """Serial port printer connection."""

    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 3.0):
        if not SERIAL_AVAILABLE:
            raise ImportError("pyserial not installed. Run: pip install pyserial")
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._serial: Optional[serial.Serial] = None

    def connect(self) -> bool:
        """Connect to serial printer."""
        try:
            self._serial = serial.Serial(
                self.port,
                self.baudrate,
                timeout=self.timeout
            )
            return True
        except serial.SerialException as e:
            self._serial = None
            raise ConnectionError(f"Failed to connect to {self.port}: {e}")

    def disconnect(self) -> None:
        """Close serial connection."""
        if self._serial:
            try:
                self._serial.close()
            except serial.SerialException:
                pass
            self._serial = None

    def write(self, data: bytes) -> bool:
        """Send data to serial printer."""
        if not self._serial:
            raise ConnectionError("Not connected")
        try:
            self._serial.write(data)
            return True
        except serial.SerialException as e:
            raise ConnectionError(f"Failed to send data: {e}")

    def is_connected(self) -> bool:
        """Check if serial port is open."""
        return self._serial is not None and self._serial.is_open

    def __repr__(self):
        return f"SerialPrinter({self.port}@{self.baudrate})"


class USBPrinter(PrinterConnection):
    """USB printer connection."""

    # Common thermal printer vendor IDs
    KNOWN_VENDORS = {
        0x04b8: "Epson",
        0x0519: "Star Micronics",
        0x0dd4: "Custom",
        0x0fe6: "Bixolon",
        0x1504: "Sewoo",
        0x0493: "MAG-TEK",
        0x1a86: "QinHeng (CH340)",
    }

    def __init__(self, vendor_id: int, product_id: int):
        if not USB_AVAILABLE:
            raise ImportError("pyusb not installed. Run: pip install pyusb")
        self.vendor_id = vendor_id
        self.product_id = product_id
        self._device = None
        self._endpoint_out = None

    def connect(self) -> bool:
        """Connect to USB printer."""
        self._device = usb.core.find(idVendor=self.vendor_id, idProduct=self.product_id)
        if not self._device:
            raise ConnectionError(
                f"USB device {self.vendor_id:04x}:{self.product_id:04x} not found"
            )

        # Detach kernel driver if active
        try:
            if self._device.is_kernel_driver_active(0):
                self._device.detach_kernel_driver(0)
        except (usb.core.USBError, NotImplementedError):
            pass

        # Set configuration
        try:
            self._device.set_configuration()
        except usb.core.USBError:
            pass  # May already be configured

        # Find OUT endpoint
        cfg = self._device.get_active_configuration()
        intf = cfg[(0, 0)]
        self._endpoint_out = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
        )

        if not self._endpoint_out:
            raise ConnectionError("Could not find USB OUT endpoint")

        return True

    def disconnect(self) -> None:
        """Release USB device."""
        if self._device:
            try:
                usb.util.dispose_resources(self._device)
            except usb.core.USBError:
                pass
            self._device = None
            self._endpoint_out = None

    def write(self, data: bytes) -> bool:
        """Send data to USB printer."""
        if not self._endpoint_out:
            raise ConnectionError("Not connected")
        try:
            self._endpoint_out.write(data)
            return True
        except usb.core.USBError as e:
            raise ConnectionError(f"Failed to send data: {e}")

    def is_connected(self) -> bool:
        """Check if USB device is connected."""
        return self._device is not None and self._endpoint_out is not None

    @classmethod
    def scan_devices(cls) -> list:
        """Scan for known USB printers."""
        if not USB_AVAILABLE:
            return []

        found = []
        devices = usb.core.find(find_all=True)
        for dev in devices:
            if dev.idVendor in cls.KNOWN_VENDORS:
                found.append({
                    "vendor_id": dev.idVendor,
                    "product_id": dev.idProduct,
                    "vendor_name": cls.KNOWN_VENDORS[dev.idVendor],
                    "vendor_id_hex": f"{dev.idVendor:04x}",
                    "product_id_hex": f"{dev.idProduct:04x}",
                })
        return found

    def __repr__(self):
        return f"USBPrinter({self.vendor_id:04x}:{self.product_id:04x})"


def create_printer(config: dict) -> PrinterConnection:
    """Factory function to create printer connection from config dict.

    Args:
        config: Dictionary with 'type' and connection parameters.
            - Network: {"type": "network", "ip": "192.168.1.100", "port": 9100}
            - Serial: {"type": "serial", "port": "/dev/ttyUSB0", "baudrate": 9600}
            - USB: {"type": "usb", "vendor_id": "04b8", "product_id": "0e15"}

    Returns:
        PrinterConnection instance.
    """
    printer_type = config.get("type", "").lower()

    if printer_type == "network":
        return NetworkPrinter(
            ip=config["ip"],
            port=config.get("port", 9100),
            timeout=config.get("timeout", 5.0)
        )
    elif printer_type == "serial":
        return SerialPrinter(
            port=config["port"],
            baudrate=config.get("baudrate", 9600),
            timeout=config.get("timeout", 3.0)
        )
    elif printer_type == "usb":
        # Handle hex string or int for vendor/product IDs
        vendor_id = config["vendor_id"]
        product_id = config["product_id"]
        if isinstance(vendor_id, str):
            vendor_id = int(vendor_id, 16)
        if isinstance(product_id, str):
            product_id = int(product_id, 16)
        return USBPrinter(vendor_id=vendor_id, product_id=product_id)
    else:
        raise ValueError(f"Unknown printer type: {printer_type}")
