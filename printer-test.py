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
                test_data = (
                    b'\x1b\x40'           # Initialize
                    b'\x1b\x61\x01'       # Center align
                    b'=== PRINTER TEST ===\n\n'
                    b'\x1b\x61\x00'       # Left align
                    b'Connection: Network\n'
                    + f'Address: {ip}:{port}\n'.encode()
                    + b'Status: OK\n'
                    b'\n\n\n\n\n\n'       # Feed paper past cutter
                    b'\x1d\x56\x00'       # Cut paper
                )
                sock.sendall(test_data)
                print("✓ Test page sent")

            return True
    except socket.timeout:
        print("✗ Connection timed out")
    except ConnectionRefusedError:
        print("✗ Connection refused - printer may be offline")
    except Exception as e:
        print(f"✗ Error: {e}")
    return False


def test_serial_printer(port: str, baudrate: int = 9600, print_test: bool = True) -> bool:
    """Test serial connection to printer."""
    if not SERIAL_AVAILABLE:
        print("✗ pyserial not installed. Run: pip install pyserial")
        return False

    print(f"Testing serial connection on {port} at {baudrate} baud...")
    try:
        with serial.Serial(port, baudrate, timeout=3) as ser:
            print(f"✓ Connected to {port}")

            if print_test:
                test_data = (
                    b'\x1b\x40'           # Initialize
                    b'\x1b\x61\x01'       # Center align
                    b'=== PRINTER TEST ===\n\n'
                    b'\x1b\x61\x00'       # Left align
                    b'Connection: Serial\n'
                    + f'Port: {port}\n'.encode()
                    + b'Status: OK\n'
                    b'\n\n\n\n\n\n'       # Feed paper past cutter
                    b'\x1d\x56\x00'       # Cut paper
                )
                ser.write(test_data)
                print("✓ Test page sent")
            else:
                # Just send initialize command to verify communication
                ser.write(b'\x1b\x40')  # ESC @

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
    import argparse

    parser = argparse.ArgumentParser(
        description="Thermal Receipt Printer Connectivity Tester",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python printer-test.py net 192.168.1.100
  python printer-test.py net 192.168.1.100 9100 --no-print
  python printer-test.py serial COM3
  python printer-test.py serial /dev/ttyUSB0 115200
  python printer-test.py usb
  python printer-test.py usb 04b8 0e15 --no-print
        """
    )

    parser.add_argument("--no-print", action="store_true",
                        help="Skip printing test page (connection test only)")

    subparsers = parser.add_subparsers(dest="mode", required=True)

    # Network subcommand
    net_parser = subparsers.add_parser("net", help="Test network printer")
    net_parser.add_argument("ip", help="Printer IP address")
    net_parser.add_argument("port", nargs="?", type=int, default=9100,
                            help="Port number (default: 9100)")

    # Serial subcommand
    serial_parser = subparsers.add_parser("serial", help="Test serial printer")
    serial_parser.add_argument("port", help="Serial port (e.g., COM3, /dev/ttyUSB0)")
    serial_parser.add_argument("baudrate", nargs="?", type=int, default=9600,
                               help="Baud rate (default: 9600)")

    # USB subcommand
    usb_parser = subparsers.add_parser("usb", help="Test USB printer")
    usb_parser.add_argument("vendor_id", nargs="?", help="Vendor ID in hex (e.g., 04b8)")
    usb_parser.add_argument("product_id", nargs="?", help="Product ID in hex (e.g., 0e15)")

    args = parser.parse_args()

    print("=" * 40)
    print("Thermal Printer Connectivity Tester")
    print("=" * 40 + "\n")

    print_test = not args.no_print
    mode = args.mode
    
    if mode == "net":
        test_network_printer(args.ip, args.port, print_test=print_test)

    elif mode == "serial":
        test_serial_printer(args.port, args.baudrate, print_test=print_test)

    elif mode == "usb":
        vid = int(args.vendor_id, 16) if args.vendor_id else None
        pid = int(args.product_id, 16) if args.product_id else None
        test_usb_printer(vid, pid, print_test=print_test)


if __name__ == "__main__":
    main()