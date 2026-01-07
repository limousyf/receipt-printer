"""Admin routes for template and printer management."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models import Template, PrinterConfig
from app.printer import TemplateRenderer, create_printer

admin_bp = Blueprint("admin", __name__)


# Template Management

@admin_bp.route("/templates")
def templates_list():
    """List all templates."""
    templates = Template.query.order_by(Template.updated_at.desc()).all()
    return render_template("admin/templates.html", templates=templates)


@admin_bp.route("/templates/new", methods=["GET", "POST"])
def template_new():
    """Create a new template."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        content = request.form.get("content", "")

        if not name:
            flash("Template name is required", "error")
            return render_template("admin/template_edit.html", template=None,
                                   name=name, description=description, content=content)

        template = Template(name=name, description=description, content=content)
        db.session.add(template)
        db.session.commit()

        flash(f"Template '{name}' created successfully", "success")
        return redirect(url_for("admin.template_edit", template_id=template.id))

    # Default template content
    default_content = """[center]
[bold]RECEIPT[/bold]
[/center]

[line]

Date: {{date}}
Order: {{order_id}}

[line]

{{#each items}}
{{name}} x{{qty}}
  ${{price}}
{{/each}}

[line]

[right]
Total: ${{total}}
[/right]

[feed n="2"]
[center]
Thank you!
[/center]

[cut]
"""
    return render_template("admin/template_edit.html", template=None, content=default_content)


@admin_bp.route("/templates/<int:template_id>", methods=["GET", "POST"])
def template_edit(template_id):
    """Edit an existing template."""
    template = Template.query.get_or_404(template_id)

    if request.method == "POST":
        template.name = request.form.get("name", "").strip()
        template.description = request.form.get("description", "").strip()
        template.content = request.form.get("content", "")

        if not template.name:
            flash("Template name is required", "error")
            return render_template("admin/template_edit.html", template=template)

        db.session.commit()
        flash(f"Template '{template.name}' updated successfully", "success")

    return render_template("admin/template_edit.html", template=template)


@admin_bp.route("/templates/<int:template_id>/delete", methods=["POST"])
def template_delete(template_id):
    """Delete a template."""
    template = Template.query.get_or_404(template_id)
    name = template.name
    db.session.delete(template)
    db.session.commit()
    flash(f"Template '{name}' deleted", "success")
    return redirect(url_for("admin.templates_list"))


@admin_bp.route("/templates/<int:template_id>/preview", methods=["POST"])
def template_preview(template_id):
    """Get template preview with sample variables."""
    template = Template.query.get_or_404(template_id)

    # Get variables from request or use defaults
    variables = request.json or {}

    # Add sample data if not provided
    if not variables:
        variables = {
            "date": "2024-01-15",
            "order_id": "12345",
            "items": [
                {"name": "Coffee", "qty": "2", "price": "5.00"},
                {"name": "Sandwich", "qty": "1", "price": "8.50"},
            ],
            "total": "18.50",
        }

    renderer = TemplateRenderer()
    preview = renderer.render_preview(template.content, variables)
    extracted_vars = renderer.extract_variables(template.content)

    return jsonify({
        "preview": preview,
        "variables": extracted_vars,
    })


@admin_bp.route("/templates/preview", methods=["POST"])
def template_preview_content():
    """Preview template content without saving."""
    content = request.json.get("content", "")
    variables = request.json.get("variables", {})

    # Add sample data if not provided
    if not variables:
        variables = {
            "date": "2024-01-15",
            "order_id": "12345",
            "items": [
                {"name": "Coffee", "qty": "2", "price": "5.00"},
                {"name": "Sandwich", "qty": "1", "price": "8.50"},
            ],
            "total": "18.50",
        }

    renderer = TemplateRenderer()
    preview = renderer.render_preview(content, variables)
    extracted_vars = renderer.extract_variables(content)

    return jsonify({
        "preview": preview,
        "variables": extracted_vars,
    })


# Printer Management

@admin_bp.route("/printers")
def printers_list():
    """List all printer configurations."""
    printers = PrinterConfig.query.all()
    return render_template("admin/printers.html", printers=printers)


@admin_bp.route("/printers/new", methods=["GET", "POST"])
def printer_new():
    """Create a new printer configuration."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        printer_type = request.form.get("type", "").strip()
        is_default = request.form.get("is_default") == "on"

        if not name or not printer_type:
            flash("Name and type are required", "error")
            return render_template("admin/printer_edit.html", printer=None)

        # Build config based on type
        config = {}
        if printer_type == "network":
            config["ip"] = request.form.get("ip", "").strip()
            config["port"] = int(request.form.get("port", 9100))
        elif printer_type == "serial":
            config["port"] = request.form.get("serial_port", "").strip()
            config["baudrate"] = int(request.form.get("baudrate", 9600))
        elif printer_type == "usb":
            config["vendor_id"] = request.form.get("vendor_id", "").strip()
            config["product_id"] = request.form.get("product_id", "").strip()

        # If this is set as default, unset others
        if is_default:
            PrinterConfig.query.update({PrinterConfig.is_default: False})

        printer = PrinterConfig(name=name, type=printer_type, is_default=is_default)
        printer.config = config
        db.session.add(printer)
        db.session.commit()

        flash(f"Printer '{name}' created successfully", "success")
        return redirect(url_for("admin.printers_list"))

    return render_template("admin/printer_edit.html", printer=None)


@admin_bp.route("/printers/<int:printer_id>", methods=["GET", "POST"])
def printer_edit(printer_id):
    """Edit a printer configuration."""
    printer = PrinterConfig.query.get_or_404(printer_id)

    if request.method == "POST":
        printer.name = request.form.get("name", "").strip()
        printer.type = request.form.get("type", "").strip()
        is_default = request.form.get("is_default") == "on"

        # Build config based on type
        config = {}
        if printer.type == "network":
            config["ip"] = request.form.get("ip", "").strip()
            config["port"] = int(request.form.get("port", 9100))
        elif printer.type == "serial":
            config["port"] = request.form.get("serial_port", "").strip()
            config["baudrate"] = int(request.form.get("baudrate", 9600))
        elif printer.type == "usb":
            config["vendor_id"] = request.form.get("vendor_id", "").strip()
            config["product_id"] = request.form.get("product_id", "").strip()

        # If this is set as default, unset others
        if is_default and not printer.is_default:
            PrinterConfig.query.filter(PrinterConfig.id != printer_id).update({PrinterConfig.is_default: False})

        printer.is_default = is_default
        printer.config = config
        db.session.commit()

        flash(f"Printer '{printer.name}' updated successfully", "success")

    return render_template("admin/printer_edit.html", printer=printer)


@admin_bp.route("/printers/<int:printer_id>/delete", methods=["POST"])
def printer_delete(printer_id):
    """Delete a printer configuration."""
    printer = PrinterConfig.query.get_or_404(printer_id)
    name = printer.name
    db.session.delete(printer)
    db.session.commit()
    flash(f"Printer '{name}' deleted", "success")
    return redirect(url_for("admin.printers_list"))


@admin_bp.route("/printers/<int:printer_id>/test", methods=["POST"])
def printer_test(printer_id):
    """Test printer connection."""
    printer_config = PrinterConfig.query.get_or_404(printer_id)

    try:
        config = printer_config.config.copy()
        config["type"] = printer_config.type
        printer = create_printer(config)

        # Try to connect and send test page
        from app.printer import ESCPOSBuilder
        builder = ESCPOSBuilder()
        builder.align_center()
        builder.bold(True)
        builder.text("=== PRINTER TEST ===")
        builder.newline(2)
        builder.bold(False)
        builder.text(f"Name: {printer_config.name}")
        builder.newline()
        builder.text(f"Type: {printer_config.type}")
        builder.newline()
        builder.text("Status: OK")
        builder.newline(2)
        builder.cut()

        printer.print_data(builder.build())
        return jsonify({"success": True, "message": "Test page sent successfully"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
