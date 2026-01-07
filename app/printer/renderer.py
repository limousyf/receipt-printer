"""Template DSL parser and renderer for receipt templates."""
import re
from typing import Any, Optional
from app.printer.escpos import ESCPOSBuilder


class TemplateRenderer:
    """Renders template DSL to ESC/POS commands.

    Template DSL supports:
    - Variables: {{variable_name}}
    - Loops: {{#each items}}...{{/each}}
    - Tags: [center], [bold], [line], [barcode], [qr], [cut], etc.
    """

    # Regex patterns
    VAR_PATTERN = re.compile(r'\{\{(\w+)\}\}')
    EACH_PATTERN = re.compile(r'\{\{#each\s+(\w+)\}\}(.*?)\{\{/each\}\}', re.DOTALL)
    TAG_PATTERN = re.compile(r'\[(/?)(\w+)(?:\s+([^\]]*))?\]')

    def __init__(self, width: int = 48):
        """Initialize renderer.

        Args:
            width: Character width per line
        """
        self.width = width

    def render(self, template: str, variables: Optional[dict] = None) -> bytes:
        """Render template to ESC/POS bytes.

        Args:
            template: Template DSL string
            variables: Dictionary of variables to substitute

        Returns:
            ESC/POS command bytes
        """
        variables = variables or {}
        builder = ESCPOSBuilder(width=self.width)

        # Process the template
        content = self._process_loops(template, variables)
        content = self._substitute_variables(content, variables)

        # Parse and render tags/text
        self._render_content(content, builder, variables)

        return builder.build()

    def render_preview(self, template: str, variables: Optional[dict] = None) -> str:
        """Render template to plain text preview.

        Args:
            template: Template DSL string
            variables: Dictionary of variables to substitute

        Returns:
            Plain text preview of receipt
        """
        variables = variables or {}

        # Process loops and variables
        content = self._process_loops(template, variables)
        content = self._substitute_variables(content, variables)

        # Convert tags to text representation
        lines = []
        current_line = ""
        alignment = "left"

        i = 0
        while i < len(content):
            # Check for tag
            tag_match = self.TAG_PATTERN.match(content, i)
            if tag_match:
                is_closing = tag_match.group(1) == "/"
                tag_name = tag_match.group(2).lower()
                tag_attrs = tag_match.group(3) or ""
                i = tag_match.end()

                if tag_name == "center" and not is_closing:
                    if current_line:
                        lines.append(self._align_text(current_line, alignment))
                        current_line = ""
                    alignment = "center"
                elif tag_name == "center" and is_closing:
                    if current_line:
                        lines.append(self._align_text(current_line, alignment))
                        current_line = ""
                    alignment = "left"
                elif tag_name == "right" and not is_closing:
                    if current_line:
                        lines.append(self._align_text(current_line, alignment))
                        current_line = ""
                    alignment = "right"
                elif tag_name == "right" and is_closing:
                    if current_line:
                        lines.append(self._align_text(current_line, alignment))
                        current_line = ""
                    alignment = "left"
                elif tag_name == "left":
                    if current_line:
                        lines.append(self._align_text(current_line, alignment))
                        current_line = ""
                    alignment = "left"
                elif tag_name == "line":
                    if current_line:
                        lines.append(self._align_text(current_line, alignment))
                        current_line = ""
                    lines.append("-" * self.width)
                elif tag_name == "cut":
                    if current_line:
                        lines.append(self._align_text(current_line, alignment))
                        current_line = ""
                    lines.append("")
                    lines.append("--- CUT ---")
                elif tag_name == "feed":
                    if current_line:
                        lines.append(self._align_text(current_line, alignment))
                        current_line = ""
                    n = self._parse_attr(tag_attrs, "n", "1")
                    for _ in range(int(n)):
                        lines.append("")
                elif tag_name == "barcode":
                    if current_line:
                        lines.append(self._align_text(current_line, alignment))
                        current_line = ""
                    # Find content until closing tag
                    end_idx = content.find("[/barcode]", i)
                    if end_idx > i:
                        barcode_data = content[i:end_idx]
                        i = end_idx + len("[/barcode]")
                        bc_type = self._parse_attr(tag_attrs, "type", "code128")
                        lines.append(f"[BARCODE:{bc_type}:{barcode_data}]")
                elif tag_name == "qr":
                    if current_line:
                        lines.append(self._align_text(current_line, alignment))
                        current_line = ""
                    # Find content until closing tag
                    end_idx = content.find("[/qr]", i)
                    if end_idx > i:
                        qr_data = content[i:end_idx]
                        i = end_idx + len("[/qr]")
                        lines.append(f"[QR:{qr_data}]")
                elif tag_name == "image":
                    if current_line:
                        lines.append(self._align_text(current_line, alignment))
                        current_line = ""
                    src = self._parse_attr(tag_attrs, "src", "")
                    lines.append(f"[IMAGE:{src}]")
                # Text formatting tags (bold, underline, etc.) - just skip in preview
                continue

            # Check for newline
            elif content[i] == "\n":
                lines.append(self._align_text(current_line, alignment))
                current_line = ""
                i += 1
            else:
                current_line += content[i]
                i += 1

        # Add any remaining content
        if current_line:
            lines.append(self._align_text(current_line, alignment))

        return "\n".join(lines)

    def extract_variables(self, template: str) -> list:
        """Extract variable names from template.

        Args:
            template: Template DSL string

        Returns:
            List of unique variable names
        """
        variables = set()

        # Find simple variables
        for match in self.VAR_PATTERN.finditer(template):
            variables.add(match.group(1))

        # Find loop variables (the list name)
        for match in self.EACH_PATTERN.finditer(template):
            variables.add(match.group(1))

        return sorted(variables)

    def _process_loops(self, template: str, variables: dict) -> str:
        """Process {{#each}} loops in template."""
        def replace_loop(match):
            list_name = match.group(1)
            loop_content = match.group(2)
            items = variables.get(list_name, [])

            if not isinstance(items, list):
                return ""

            result = []
            for item in items:
                # Replace item properties in loop content
                item_content = loop_content
                if isinstance(item, dict):
                    for key, value in item.items():
                        item_content = item_content.replace(f"{{{{{key}}}}}", str(value))
                else:
                    item_content = item_content.replace("{{.}}", str(item))
                result.append(item_content)

            return "".join(result)

        return self.EACH_PATTERN.sub(replace_loop, template)

    def _substitute_variables(self, content: str, variables: dict) -> str:
        """Substitute {{variable}} placeholders."""
        def replace_var(match):
            var_name = match.group(1)
            return str(variables.get(var_name, f"{{{{{var_name}}}}}"))

        return self.VAR_PATTERN.sub(replace_var, content)

    def _render_content(self, content: str, builder: ESCPOSBuilder, variables: dict):
        """Parse tags and render to ESCPOSBuilder."""
        i = 0
        text_buffer = ""

        while i < len(content):
            # Check for tag
            tag_match = self.TAG_PATTERN.match(content, i)
            if tag_match:
                # Flush text buffer
                if text_buffer:
                    builder.text(text_buffer)
                    text_buffer = ""

                is_closing = tag_match.group(1) == "/"
                tag_name = tag_match.group(2).lower()
                tag_attrs = tag_match.group(3) or ""
                i = tag_match.end()

                self._handle_tag(builder, tag_name, tag_attrs, is_closing, content, i, variables)

                # Skip past content for tags with content (barcode, qr)
                if tag_name in ("barcode", "qr") and not is_closing:
                    end_tag = f"[/{tag_name}]"
                    end_idx = content.find(end_tag, i)
                    if end_idx > i:
                        tag_content = content[i:end_idx]
                        i = end_idx + len(end_tag)
                        if tag_name == "barcode":
                            bc_type = self._parse_attr(tag_attrs, "type", "code128")
                            builder.barcode(tag_content, bc_type)
                        elif tag_name == "qr":
                            size = int(self._parse_attr(tag_attrs, "size", "4"))
                            builder.qr(tag_content, size=size)
            elif content[i] == "\n":
                if text_buffer:
                    builder.text(text_buffer)
                    text_buffer = ""
                builder.newline()
                i += 1
            else:
                text_buffer += content[i]
                i += 1

        # Flush remaining text
        if text_buffer:
            builder.text(text_buffer)

    def _handle_tag(self, builder: ESCPOSBuilder, tag_name: str, attrs: str,
                    is_closing: bool, content: str, pos: int, variables: dict):
        """Handle a single tag."""
        if tag_name == "center":
            if is_closing:
                builder.align_left()
            else:
                builder.align_center()
        elif tag_name == "right":
            if is_closing:
                builder.align_left()
            else:
                builder.align_right()
        elif tag_name == "left":
            builder.align_left()
        elif tag_name == "bold":
            builder.bold(not is_closing)
        elif tag_name == "underline":
            builder.underline(not is_closing)
        elif tag_name == "double-height":
            builder.double_height(not is_closing)
        elif tag_name == "double-width":
            builder.double_width(not is_closing)
        elif tag_name == "double-size":
            builder.double_size(not is_closing)
        elif tag_name == "normal":
            builder.normal()
        elif tag_name == "line":
            char = self._parse_attr(attrs, "char", "-")
            builder.line(char)
        elif tag_name == "feed":
            n = int(self._parse_attr(attrs, "n", "1"))
            builder.feed(n)
        elif tag_name == "cut":
            partial = self._parse_attr(attrs, "partial", "false").lower() == "true"
            builder.cut(partial=partial)
        elif tag_name == "image":
            src = self._parse_attr(attrs, "src", "")
            if src:
                try:
                    builder.image(src)
                except Exception:
                    builder.text(f"[IMAGE ERROR: {src}]").newline()
        # barcode and qr are handled in _render_content due to their content

    def _parse_attr(self, attrs: str, name: str, default: str = "") -> str:
        """Parse a single attribute from tag attributes string."""
        pattern = re.compile(rf'{name}=["\']?([^"\'\s\]]+)["\']?')
        match = pattern.search(attrs)
        return match.group(1) if match else default

    def _align_text(self, text: str, alignment: str) -> str:
        """Align text for preview."""
        text = text.rstrip()
        if not text:
            return ""
        if alignment == "center":
            return text.center(self.width)
        elif alignment == "right":
            return text.rjust(self.width)
        return text
