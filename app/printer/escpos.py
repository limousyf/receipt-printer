"""ESC/POS command builder for thermal printers."""
import io
from typing import Optional, Union
from PIL import Image

# Optional barcode/QR support
try:
    import barcode
    from barcode.writer import ImageWriter
    BARCODE_AVAILABLE = True
except ImportError:
    BARCODE_AVAILABLE = False

try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False


class ESCPOSBuilder:
    """Builder for ESC/POS printer commands."""

    # ESC/POS Command Constants
    ESC = b'\x1b'
    GS = b'\x1d'
    FS = b'\x1c'

    # Initialize printer
    INIT = ESC + b'\x40'  # ESC @

    # Text formatting
    BOLD_ON = ESC + b'\x45\x01'   # ESC E 1
    BOLD_OFF = ESC + b'\x45\x00'  # ESC E 0
    UNDERLINE_ON = ESC + b'\x2d\x01'   # ESC - 1
    UNDERLINE_OFF = ESC + b'\x2d\x00'  # ESC - 0
    DOUBLE_HEIGHT_ON = ESC + b'\x21\x10'   # ESC ! 16
    DOUBLE_WIDTH_ON = ESC + b'\x21\x20'    # ESC ! 32
    DOUBLE_SIZE_ON = ESC + b'\x21\x30'     # ESC ! 48
    NORMAL_SIZE = ESC + b'\x21\x00'        # ESC ! 0

    # Alignment
    ALIGN_LEFT = ESC + b'\x61\x00'    # ESC a 0
    ALIGN_CENTER = ESC + b'\x61\x01'  # ESC a 1
    ALIGN_RIGHT = ESC + b'\x61\x02'   # ESC a 2

    # Paper control
    CUT_FULL = GS + b'\x56\x00'  # GS V 0 - Full cut
    CUT_PARTIAL = GS + b'\x56\x01'  # GS V 1 - Partial cut
    FEED_LINE = b'\n'

    # Character settings
    CHARSET_PC437 = ESC + b'\x74\x00'  # USA: Standard Europe
    CHARSET_PC850 = ESC + b'\x74\x02'  # Multilingual

    def __init__(self, width: int = 48):
        """Initialize builder.

        Args:
            width: Character width per line (48 for 58mm, 42 for 80mm paper)
        """
        self.width = width
        self._buffer = bytearray()
        self._buffer.extend(self.INIT)

    def reset(self) -> "ESCPOSBuilder":
        """Reset the buffer and initialize printer."""
        self._buffer = bytearray()
        self._buffer.extend(self.INIT)
        return self

    # Text formatting methods

    def text(self, content: str) -> "ESCPOSBuilder":
        """Add plain text."""
        self._buffer.extend(content.encode("cp437", errors="replace"))
        return self

    def newline(self, count: int = 1) -> "ESCPOSBuilder":
        """Add newline(s)."""
        self._buffer.extend(self.FEED_LINE * count)
        return self

    def bold(self, on: bool = True) -> "ESCPOSBuilder":
        """Set bold mode."""
        self._buffer.extend(self.BOLD_ON if on else self.BOLD_OFF)
        return self

    def underline(self, on: bool = True) -> "ESCPOSBuilder":
        """Set underline mode."""
        self._buffer.extend(self.UNDERLINE_ON if on else self.UNDERLINE_OFF)
        return self

    def double_height(self, on: bool = True) -> "ESCPOSBuilder":
        """Set double height mode."""
        self._buffer.extend(self.DOUBLE_HEIGHT_ON if on else self.NORMAL_SIZE)
        return self

    def double_width(self, on: bool = True) -> "ESCPOSBuilder":
        """Set double width mode."""
        self._buffer.extend(self.DOUBLE_WIDTH_ON if on else self.NORMAL_SIZE)
        return self

    def double_size(self, on: bool = True) -> "ESCPOSBuilder":
        """Set double height and width."""
        self._buffer.extend(self.DOUBLE_SIZE_ON if on else self.NORMAL_SIZE)
        return self

    def normal(self) -> "ESCPOSBuilder":
        """Reset to normal text size."""
        self._buffer.extend(self.NORMAL_SIZE)
        self._buffer.extend(self.BOLD_OFF)
        self._buffer.extend(self.UNDERLINE_OFF)
        return self

    # Alignment methods

    def align_left(self) -> "ESCPOSBuilder":
        """Set left alignment."""
        self._buffer.extend(self.ALIGN_LEFT)
        return self

    def align_center(self) -> "ESCPOSBuilder":
        """Set center alignment."""
        self._buffer.extend(self.ALIGN_CENTER)
        return self

    def align_right(self) -> "ESCPOSBuilder":
        """Set right alignment."""
        self._buffer.extend(self.ALIGN_RIGHT)
        return self

    # Line formatting

    def line(self, char: str = "-") -> "ESCPOSBuilder":
        """Print a horizontal line."""
        self._buffer.extend((char * self.width).encode("cp437"))
        self._buffer.extend(self.FEED_LINE)
        return self

    def feed(self, lines: int = 1) -> "ESCPOSBuilder":
        """Feed paper by number of lines."""
        self._buffer.extend(self.FEED_LINE * lines)
        return self

    # Paper control

    def cut(self, partial: bool = False) -> "ESCPOSBuilder":
        """Cut the paper."""
        # Feed a bit before cutting to ensure content clears the cutter
        self._buffer.extend(self.FEED_LINE * 4)
        self._buffer.extend(self.CUT_PARTIAL if partial else self.CUT_FULL)
        return self

    # Image printing

    def image(self, img: Union[Image.Image, bytes, str], max_width: Optional[int] = None) -> "ESCPOSBuilder":
        """Print an image.

        Args:
            img: PIL Image, bytes (raw image data), or path to image file
            max_width: Maximum width in pixels (default: 384 for 58mm paper)
        """
        if max_width is None:
            max_width = 384  # 58mm paper at 203 DPI

        # Load image if needed
        if isinstance(img, str):
            img = Image.open(img)
        elif isinstance(img, bytes):
            img = Image.open(io.BytesIO(img))

        # Convert to grayscale and resize if needed
        img = img.convert("L")
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

        # Convert to 1-bit
        img = img.convert("1")

        # Build raster image command
        width_bytes = (img.width + 7) // 8
        self._buffer.extend(self.GS)
        self._buffer.extend(b'\x76\x30\x00')  # GS v 0 - Raster bit image
        self._buffer.append(width_bytes & 0xff)
        self._buffer.append((width_bytes >> 8) & 0xff)
        self._buffer.append(img.height & 0xff)
        self._buffer.append((img.height >> 8) & 0xff)

        # Convert image to bytes
        for y in range(img.height):
            row_bytes = bytearray(width_bytes)
            for x in range(img.width):
                if img.getpixel((x, y)) == 0:  # Black pixel
                    row_bytes[x // 8] |= (0x80 >> (x % 8))
            self._buffer.extend(row_bytes)

        return self

    # Barcode printing

    def barcode(self, data: str, barcode_type: str = "code128", height: int = 80) -> "ESCPOSBuilder":
        """Print a barcode.

        Args:
            data: Barcode data/content
            barcode_type: Type of barcode (code128, ean13, code39, etc.)
            height: Barcode height in pixels
        """
        if not BARCODE_AVAILABLE:
            # Fallback: print text representation
            self.text(f"[{barcode_type}: {data}]").newline()
            return self

        try:
            # Generate barcode image
            barcode_class = barcode.get_barcode_class(barcode_type)
            bc = barcode_class(data, writer=ImageWriter())

            # Render to image buffer
            buffer = io.BytesIO()
            bc.write(buffer, options={"write_text": False, "module_height": height / 10})
            buffer.seek(0)

            # Print as image
            self.image(buffer.read())
        except Exception:
            # Fallback on error
            self.text(f"[{barcode_type}: {data}]").newline()

        return self

    def qr(self, data: str, size: int = 4, error_correction: str = "M") -> "ESCPOSBuilder":
        """Print a QR code.

        Args:
            data: QR code content
            size: Module size (1-8, higher = larger)
            error_correction: Error correction level (L, M, Q, H)
        """
        if not QRCODE_AVAILABLE:
            # Fallback: print text representation
            self.text(f"[QR: {data}]").newline()
            return self

        try:
            # Map error correction
            ec_map = {
                "L": qrcode.constants.ERROR_CORRECT_L,
                "M": qrcode.constants.ERROR_CORRECT_M,
                "Q": qrcode.constants.ERROR_CORRECT_Q,
                "H": qrcode.constants.ERROR_CORRECT_H,
            }
            ec = ec_map.get(error_correction.upper(), qrcode.constants.ERROR_CORRECT_M)

            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=ec,
                box_size=size,
                border=2,
            )
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            # Print as image
            self.image(img.get_image())
        except Exception:
            # Fallback on error
            self.text(f"[QR: {data}]").newline()

        return self

    # Build output

    def build(self) -> bytes:
        """Build and return the command buffer."""
        return bytes(self._buffer)

    def __bytes__(self) -> bytes:
        """Allow bytes() conversion."""
        return self.build()

    def __len__(self) -> int:
        """Return buffer length."""
        return len(self._buffer)
