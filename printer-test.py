#!/usr/bin/env python3
"""
Thermal Receipt Printer Connectivity Tester
Tests connection via Serial, USB, or Network interfaces
"""

import socket
import sys

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


def test_network_printer(ip: str, port: int = 9100, print_test: bool = True) -> bool:
    """Test TCP/IP connection to network printer (default port 9100)."""
    print(f"Testing network connection to {ip}:{port}...")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(5)
            sock.connect((ip, port))
            print(f"✓ Connected to {ip}:{port}")
            
            if print_test:
                print_test_page(sock, f"Network {ip}:{port}")
            
            return True
    except socket.timeout:
        print(f"✗ Connection timed out")
    except ConnectionRefusedError:
        print(f"✗ Connection refused - printer may be offline")
    except Exception as e:
        print(f"✗ Error: {e}")
    return False


def test_serial_printer(port: str, baudrate: int = 9600) -> bool:
    """Test serial connection to printer."""
    if not SERIAL_AVAILABLE:
        print("✗ pyserial not installed. Run: pip install pyserial")
        return False
    
    print(f"Testing serial connection on {port} at {baudrate} baud...")
    try:
        with serial.Serial(port, baudrate, timeout=3) as ser:
            # Send ESC/POS initialize command
            ser.write(b'\x1b\x40')  # ESC @
            print(f"✓ Connected to {port}")
            return True
    except serial.SerialException as e:
        print(f"✗ Serial error: {e}")
    except Exception as e:
        print(f"✗ Error: {e}")
    return False


def test_usb_printer(vendor_id: int = None, product_id: int = None, print_test: bool = True) -> bool:
    """Test USB connection. Lists devices if no IDs provided."""
    if not USB_AVAILABLE:
        print("✗ pyusb not installed. Run: pip install pyusb")
        return False
    
    print("Scanning for USB printers...")
    
    # Common thermal printer vendor IDs
    known_vendors = {
        0x04b8: "Epson",
        0x0519: "Star Micronics",
        0x0dd4: "Custom",
        0x0fe6: "Bixolon",
        0x1504: "Sewoo",
        0x0493: "MAG-TEK",
        0x1a86: "QinHeng (CH340)",
    }
    
    if vendor_id and product_id:
        dev = usb.core.find(idVendor=vendor_id, idProduct=product_id)
        if dev:
            print(f"✓ Found device {vendor_id:04x}:{product_id:04x}")
            
            if print_test:
                # Detach kernel driver if active
                try:
                    if dev.is_kernel_driver_active(0):
                        dev.detach_kernel_driver(0)
                except:
                    pass
                
                # Set configuration and find OUT endpoint
                dev.set_configuration()
                cfg = dev.get_active_configuration()
                intf = cfg[(0, 0)]
                ep_out = usb.util.find_descriptor(
                    intf,
                    custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
                )
                
                if ep_out:
                    test_data = (
                        b'\x1b\x40'           # Initialize
                        b'\x1b\x61\x01'       # Center align
                        b'=== PRINTER TEST ===\n\n'
                        b'\x1b\x61\x00'       # Left align
                        b'Connection: USB\n'
                        b'Status: OK\n'
                        b'\n\n\n\n\n\n'       # Feed paper past cutter
                        b'\x1d\x56\x00'       # Cut paper
                    )
                    ep_out.write(test_data)
                    print("✓ Test page sent")
                else:
                    print("✗ Could not find OUT endpoint")
            
            return True
        else:
            print(f"✗ Device {vendor_id:04x}:{product_id:04x} not found")
            return False
    
    # List all USB devices that might be printers
    devices = usb.core.find(find_all=True)
    found = False
    for dev in devices:
        vendor = known_vendors.get(dev.idVendor, "Unknown")
        if dev.idVendor in known_vendors:
            print(f"  Found: {vendor} - {dev.idVendor:04x}:{dev.idProduct:04x}")
            found = True
    
    if not found:
        print("  No known printer vendors detected")
    return found

def main():
    print("=" * 40)
    print("Thermal Printer Connectivity Tester")
    print("=" * 40 + "\n")
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Network:  python printer_test.py net <ip> [port]")
        print("  Serial:   python printer_test.py serial <port> [baudrate]")
        print("  USB:      python printer_test.py usb [vendor_id] [product_id]")
        print("\nExamples:")
        print("  python printer_test.py net 192.168.1.100")
        print("  python printer_test.py serial COM3")
        print("  python printer_test.py serial /dev/ttyUSB0 115200")
        print("  python printer_test.py usb")
        print("  python printer_test.py usb 04b8 0e15")
        return
    
    mode = sys.argv[1].lower()
    
    if mode == "net":
        if len(sys.argv) < 3:
            print("Error: IP address required")
            return
        ip = sys.argv[2]
        port = int(sys.argv[3]) if len(sys.argv) > 3 else 9100
        test_network_printer(ip, port)
    
    elif mode == "serial":
        if len(sys.argv) < 3:
            print("Error: Serial port required")
            return
        port = sys.argv[2]
        baud = int(sys.argv[3]) if len(sys.argv) > 3 else 9600
        test_serial_printer(port, baud)
    
    elif mode == "usb":
        vid = int(sys.argv[2], 16) if len(sys.argv) > 2 else None
        pid = int(sys.argv[3], 16) if len(sys.argv) > 3 else None
        test_usb_printer(vid, pid)
    
    else:
        print(f"Unknown mode: {mode}")


if __name__ == "__main__":
    main()