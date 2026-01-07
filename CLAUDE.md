# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Receipt Printer Manager - A Flask web application for managing thermal receipt printer templates and printing. Includes a standalone CLI tool for printer connectivity testing.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the web server
PORT=9001 python run.py

# Or use the CLI tester directly
python printer-test.py net 192.168.1.100
```

## Project Structure

```
receipt-printer/
├── app/                      # Flask application
│   ├── __init__.py          # App factory
│   ├── config.py            # Configuration
│   ├── models.py            # SQLAlchemy models (Template, PrinterConfig, PrintHistory)
│   ├── printer/             # Printer module
│   │   ├── connection.py    # Network/USB/Serial printer connections
│   │   ├── escpos.py        # ESC/POS command builder
│   │   └── renderer.py      # Template DSL parser and renderer
│   ├── routes/              # Flask blueprints
│   │   ├── admin.py         # Template & printer CRUD
│   │   ├── print.py         # Print interface & history
│   │   └── api.py           # REST API endpoints
│   ├── templates/           # Jinja2 HTML templates
│   └── static/              # CSS/JS assets
├── instance/                # SQLite database (auto-created)
├── run.py                   # Web server entry point
├── printer-test.py          # Standalone CLI tester
└── requirements.txt
```

## Running the Application

### Web Server
```bash
# Development (default port 5000)
python run.py

# Custom port
PORT=9001 python run.py

# Production
FLASK_ENV=production python run.py
```

### CLI Printer Tester
```bash
# Network printer
python printer-test.py net <ip> [port] [--no-print]

# Serial printer
python printer-test.py serial <port> [baudrate]

# USB printer (scan or specify IDs)
python printer-test.py usb [vendor_id product_id]
```

## Dependencies

- **Python 3.6+**
- **Flask + Flask-SQLAlchemy** - Web framework and ORM
- **Pillow** - Image processing for receipt images
- **qrcode** - QR code generation
- **python-barcode** - Barcode generation
- **pyserial** - Serial connections (optional)
- **pyusb** - USB connections (optional)

## Architecture

### Database Models (`app/models.py`)
- `Template` - Receipt templates with DSL content
- `PrinterConfig` - Printer connection settings (network/serial/usb)
- `PrintHistory` - Log of all print jobs with status

### Template DSL (`app/printer/renderer.py`)
Templates use a custom markup language:
```
[center][bold]RECEIPT[/bold][/center]
[line]
Date: {{date}}
{{#each items}}
  {{name}} - ${{price}}
{{/each}}
[barcode type="code128"]{{order_id}}[/barcode]
[qr]{{url}}[/qr]
[cut]
```

**Supported tags:** `[center]`, `[right]`, `[bold]`, `[underline]`, `[double-height]`, `[line]`, `[feed n="N"]`, `[cut]`, `[barcode]`, `[qr]`, `[image]`

### ESC/POS Builder (`app/printer/escpos.py`)
Low-level command builder for thermal printers. Supports text formatting, alignment, images, barcodes, and QR codes.

### Printer Connections (`app/printer/connection.py`)
Abstract `PrinterConnection` base class with implementations:
- `NetworkPrinter` - TCP socket (port 9100)
- `SerialPrinter` - pyserial
- `USBPrinter` - pyusb

Factory function: `create_printer(config_dict)`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/templates` | List all templates |
| POST | `/api/templates` | Create template |
| GET | `/api/templates/<id>` | Get template with variables |
| PUT | `/api/templates/<id>` | Update template |
| DELETE | `/api/templates/<id>` | Delete template |
| GET | `/api/printers` | List printers |
| POST | `/api/print` | Print receipt |
| POST | `/api/preview` | Preview without printing |
| GET | `/api/history` | Print history |

## Common Tasks

### Adding a new ESC/POS command
1. Add constant in `app/printer/escpos.py`
2. Add method to `ESCPOSBuilder` class
3. Add tag handling in `app/printer/renderer.py`

### Adding a new template tag
1. Update `_render_content()` in `renderer.py`
2. Update `_handle_tag()` for ESC/POS output
3. Update `render_preview()` for text preview

### Testing printer connection
```python
from app.printer import create_printer
printer = create_printer({"type": "network", "ip": "192.168.1.100", "port": 9100})
printer.print_data(b'\x1b\x40Test\n')  # Initialize + print
```
