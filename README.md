# Receipt Printer Manager

A web application for managing and printing thermal receipt templates. Design receipts with a simple markup language, configure multiple printers (network, USB, serial), and print with variable substitution.

## Features

- **Template Designer** - Create receipt templates with live preview
- **Custom DSL** - Simple markup for formatting, barcodes, QR codes, and images
- **Multiple Printers** - Support for network (TCP/IP), USB, and serial connections
- **Print History** - Track all print jobs with status and details
- **REST API** - Programmatic access for integration with other systems

## Quick Start

```bash
# Clone and install
git clone <repo-url>
cd receipt-printer
pip install -r requirements.txt

# Run the server
python run.py

# Open http://localhost:5000
```

## Screenshots

The web interface includes:
- **Print** - Select a template, fill in variables, preview, and print
- **Templates** - Create and edit receipt templates with live preview
- **Printers** - Configure printer connections
- **History** - View past print jobs

## Template DSL

Templates use a simple markup language that compiles to ESC/POS commands:

```
[center]
[bold]MY STORE[/bold]
123 Main Street
[/center]

[line]

Date: {{date}}
Order #{{order_id}}

[line]

{{#each items}}
{{name}}
  {{qty}} x ${{price}}
{{/each}}

[line char="="]

[right]
[bold]Total: ${{total}}[/bold]
[/right]

[feed n="2"]

[center]
[qr]{{receipt_url}}[/qr]
Scan for digital receipt
[/center]

[cut]
```

### Supported Tags

| Tag | Description |
|-----|-------------|
| `[center]...[/center]` | Center align text |
| `[right]...[/right]` | Right align text |
| `[bold]...[/bold]` | Bold text |
| `[underline]...[/underline]` | Underlined text |
| `[double-height]...[/double-height]` | Double height text |
| `[double-width]...[/double-width]` | Double width text |
| `[line]` or `[line char="="]` | Horizontal line |
| `[feed n="3"]` | Feed N lines |
| `[cut]` | Cut paper |
| `[barcode type="code128"]data[/barcode]` | Print barcode |
| `[qr]data[/qr]` | Print QR code |
| `[image src="path"]` | Print image |

### Variables

- `{{variable}}` - Simple variable substitution
- `{{#each items}}...{{/each}}` - Loop over arrays

## Printer Configuration

### Network Printer (TCP/IP)
Most thermal printers support raw TCP on port 9100:
- IP: `192.168.1.100`
- Port: `9100` (default)

### USB Printer
Requires vendor and product IDs (find with `lsusb` on Linux):
- Vendor ID: `04b8` (Epson)
- Product ID: `0e15`

### Serial Printer
- Port: `/dev/ttyUSB0` (Linux) or `COM3` (Windows)
- Baud rate: `9600` (default)

## REST API

### Print a Receipt
```bash
curl -X POST http://localhost:5000/api/print \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": 1,
    "variables": {
      "date": "2024-01-15",
      "order_id": "12345",
      "items": [
        {"name": "Coffee", "qty": "2", "price": "5.00"},
        {"name": "Sandwich", "qty": "1", "price": "8.50"}
      ],
      "total": "18.50"
    }
  }'
```

### Preview Without Printing
```bash
curl -X POST http://localhost:5000/api/preview \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": 1,
    "variables": {"date": "2024-01-15"}
  }'
```

### List Templates
```bash
curl http://localhost:5000/api/templates
```

### Full API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/templates` | List all templates |
| POST | `/api/templates` | Create template |
| GET | `/api/templates/<id>` | Get template details |
| PUT | `/api/templates/<id>` | Update template |
| DELETE | `/api/templates/<id>` | Delete template |
| GET | `/api/printers` | List configured printers |
| GET | `/api/printers/<id>` | Get printer details |
| POST | `/api/print` | Print a receipt |
| POST | `/api/preview` | Preview a receipt |
| GET | `/api/history` | List print history |
| GET | `/api/history/<id>` | Get print job details |

## CLI Tool

A standalone CLI tool is included for testing printer connectivity:

```bash
# Test network printer
python printer-test.py net 192.168.1.100

# Test without printing
python printer-test.py net 192.168.1.100 --no-print

# Test serial printer
python printer-test.py serial /dev/ttyUSB0 9600

# Scan for USB printers
python printer-test.py usb

# Test specific USB printer
python printer-test.py usb 04b8 0e15
```

## Configuration

Environment variables:
- `PORT` - Server port (default: 5000)
- `HOST` - Server host (default: 0.0.0.0)
- `FLASK_ENV` - Environment: `development` or `production`
- `DATABASE_URL` - SQLite database path
- `SECRET_KEY` - Flask secret key

## Supported Printers

Tested with ESC/POS compatible thermal printers:
- Epson TM series (TM-T20, TM-T88, TM-30)
- Star Micronics
- Bixolon
- Generic 58mm/80mm thermal printers

## Development

```bash
# Install dev dependencies
pip install -r requirements.txt

# Run in development mode
FLASK_ENV=development python run.py

# Database is auto-created in instance/receipts.db
```

## License

MIT
