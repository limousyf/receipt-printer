"""Print routes for selecting and printing receipts."""
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models import Template, PrinterConfig, PrintHistory
from app.printer import TemplateRenderer, create_printer

print_bp = Blueprint("print", __name__)


@print_bp.route("/")
def select_template():
    """Select a template to print."""
    templates = Template.query.order_by(Template.name).all()
    printers = PrinterConfig.query.all()
    default_printer = PrinterConfig.query.filter_by(is_default=True).first()

    return render_template("print/select.html",
                           templates=templates,
                           printers=printers,
                           default_printer=default_printer)


@print_bp.route("/template/<int:template_id>", methods=["GET", "POST"])
def print_template(template_id):
    """Print a specific template with variables."""
    template = Template.query.get_or_404(template_id)
    printers = PrinterConfig.query.all()
    default_printer = PrinterConfig.query.filter_by(is_default=True).first()

    # Extract variables from template
    renderer = TemplateRenderer()
    template_vars = renderer.extract_variables(template.content)

    if request.method == "POST":
        # Get variables from form
        variables = {}
        for var in template_vars:
            value = request.form.get(f"var_{var}", "")
            # Check if it's a JSON array (for loop variables)
            if value.startswith("["):
                try:
                    variables[var] = json.loads(value)
                except json.JSONDecodeError:
                    variables[var] = value
            else:
                variables[var] = value

        # Get printer
        printer_id = request.form.get("printer_id")
        if not printer_id:
            flash("Please select a printer", "error")
            return render_template("print/preview.html",
                                   template=template,
                                   variables=template_vars,
                                   printers=printers,
                                   default_printer=default_printer)

        printer_config = PrinterConfig.query.get(printer_id)
        if not printer_config:
            flash("Printer not found", "error")
            return redirect(url_for("print.print_template", template_id=template_id))

        # Render and print
        try:
            # Generate preview for history
            preview = renderer.render_preview(template.content, variables)

            # Render to ESC/POS
            escpos_data = renderer.render(template.content, variables)

            # Connect and print
            config = printer_config.config.copy()
            config["type"] = printer_config.type
            printer = create_printer(config)
            printer.print_data(escpos_data)

            # Log to history
            history = PrintHistory(
                template_id=template.id,
                rendered_preview=preview,
                status="success"
            )
            history.variables = variables
            history.printer_config = {
                "name": printer_config.name,
                "type": printer_config.type,
                **printer_config.config
            }
            db.session.add(history)
            db.session.commit()

            flash("Receipt printed successfully!", "success")
            return redirect(url_for("print.select_template"))

        except Exception as e:
            # Log failure to history
            history = PrintHistory(
                template_id=template.id,
                rendered_preview=renderer.render_preview(template.content, variables),
                status="failed",
                error_message=str(e)
            )
            history.variables = variables
            history.printer_config = {
                "name": printer_config.name,
                "type": printer_config.type,
                **printer_config.config
            }
            db.session.add(history)
            db.session.commit()

            flash(f"Print failed: {e}", "error")

    # Generate preview with sample/empty data
    sample_vars = {var: f"[{var}]" for var in template_vars}
    preview = renderer.render_preview(template.content, sample_vars)

    return render_template("print/preview.html",
                           template=template,
                           variables=template_vars,
                           preview=preview,
                           printers=printers,
                           default_printer=default_printer)


@print_bp.route("/template/<int:template_id>/preview", methods=["POST"])
def preview_with_variables(template_id):
    """Generate preview with provided variables."""
    template = Template.query.get_or_404(template_id)

    variables = request.json.get("variables", {})
    renderer = TemplateRenderer()
    preview = renderer.render_preview(template.content, variables)

    return jsonify({"preview": preview})


@print_bp.route("/history")
def history():
    """View print history."""
    page = request.args.get("page", 1, type=int)
    per_page = 20

    query = PrintHistory.query.order_by(PrintHistory.printed_at.desc())

    # Filter by status if provided
    status = request.args.get("status")
    if status:
        query = query.filter_by(status=status)

    # Filter by template if provided
    template_id = request.args.get("template_id", type=int)
    if template_id:
        query = query.filter_by(template_id=template_id)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    templates = Template.query.order_by(Template.name).all()

    return render_template("history.html",
                           history=pagination.items,
                           pagination=pagination,
                           templates=templates,
                           current_status=status,
                           current_template_id=template_id)


@print_bp.route("/history/<int:history_id>")
def history_detail(history_id):
    """View details of a specific print job."""
    record = PrintHistory.query.get_or_404(history_id)
    return render_template("print/history_detail.html", record=record)


@print_bp.route("/quick", methods=["POST"])
def quick_print():
    """Quick print API - print a template with variables."""
    data = request.json
    template_id = data.get("template_id")
    variables = data.get("variables", {})
    printer_id = data.get("printer_id")

    template = Template.query.get_or_404(template_id)

    # Get printer (use default if not specified)
    if printer_id:
        printer_config = PrinterConfig.query.get(printer_id)
    else:
        printer_config = PrinterConfig.query.filter_by(is_default=True).first()

    if not printer_config:
        return jsonify({"success": False, "error": "No printer configured"}), 400

    renderer = TemplateRenderer()

    try:
        # Generate preview for history
        preview = renderer.render_preview(template.content, variables)

        # Render to ESC/POS
        escpos_data = renderer.render(template.content, variables)

        # Connect and print
        config = printer_config.config.copy()
        config["type"] = printer_config.type
        printer = create_printer(config)
        printer.print_data(escpos_data)

        # Log to history
        history = PrintHistory(
            template_id=template.id,
            rendered_preview=preview,
            status="success"
        )
        history.variables = variables
        history.printer_config = {
            "name": printer_config.name,
            "type": printer_config.type,
            **printer_config.config
        }
        db.session.add(history)
        db.session.commit()

        return jsonify({"success": True, "history_id": history.id})

    except Exception as e:
        # Log failure
        history = PrintHistory(
            template_id=template.id,
            rendered_preview=renderer.render_preview(template.content, variables),
            status="failed",
            error_message=str(e)
        )
        history.variables = variables
        history.printer_config = {
            "name": printer_config.name,
            "type": printer_config.type,
            **printer_config.config
        }
        db.session.add(history)
        db.session.commit()

        return jsonify({"success": False, "error": str(e), "history_id": history.id}), 500
