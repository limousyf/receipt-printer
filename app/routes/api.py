"""REST API endpoints for programmatic access."""
from flask import Blueprint, request, jsonify
from app import db
from app.models import Template, PrinterConfig, PrintHistory
from app.printer import TemplateRenderer, create_printer

api_bp = Blueprint("api", __name__)


# Templates API

@api_bp.route("/templates", methods=["GET"])
def list_templates():
    """List all templates."""
    templates = Template.query.order_by(Template.name).all()
    return jsonify({
        "templates": [t.to_dict() for t in templates]
    })


@api_bp.route("/templates/<int:template_id>", methods=["GET"])
def get_template(template_id):
    """Get a specific template."""
    template = Template.query.get_or_404(template_id)
    renderer = TemplateRenderer()
    variables = renderer.extract_variables(template.content)

    result = template.to_dict()
    result["variables"] = variables
    return jsonify(result)


@api_bp.route("/templates", methods=["POST"])
def create_template():
    """Create a new template."""
    data = request.json

    if not data.get("name"):
        return jsonify({"error": "Name is required"}), 400
    if not data.get("content"):
        return jsonify({"error": "Content is required"}), 400

    template = Template(
        name=data["name"],
        description=data.get("description", ""),
        content=data["content"]
    )
    db.session.add(template)
    db.session.commit()

    return jsonify(template.to_dict()), 201


@api_bp.route("/templates/<int:template_id>", methods=["PUT"])
def update_template(template_id):
    """Update a template."""
    template = Template.query.get_or_404(template_id)
    data = request.json

    if "name" in data:
        template.name = data["name"]
    if "description" in data:
        template.description = data["description"]
    if "content" in data:
        template.content = data["content"]

    db.session.commit()
    return jsonify(template.to_dict())


@api_bp.route("/templates/<int:template_id>", methods=["DELETE"])
def delete_template(template_id):
    """Delete a template."""
    template = Template.query.get_or_404(template_id)
    db.session.delete(template)
    db.session.commit()
    return jsonify({"success": True})


# Printers API

@api_bp.route("/printers", methods=["GET"])
def list_printers():
    """List all printers."""
    printers = PrinterConfig.query.all()
    return jsonify({
        "printers": [p.to_dict() for p in printers]
    })


@api_bp.route("/printers/<int:printer_id>", methods=["GET"])
def get_printer(printer_id):
    """Get a specific printer."""
    printer = PrinterConfig.query.get_or_404(printer_id)
    return jsonify(printer.to_dict())


# Print API

@api_bp.route("/print", methods=["POST"])
def print_receipt():
    """Print a receipt.

    Request body:
    {
        "template_id": 1,
        "variables": {"date": "2024-01-15", ...},
        "printer_id": 1  // optional, uses default if not provided
    }
    """
    data = request.json

    template_id = data.get("template_id")
    if not template_id:
        return jsonify({"error": "template_id is required"}), 400

    template = Template.query.get(template_id)
    if not template:
        return jsonify({"error": "Template not found"}), 404

    variables = data.get("variables", {})

    # Get printer
    printer_id = data.get("printer_id")
    if printer_id:
        printer_config = PrinterConfig.query.get(printer_id)
    else:
        printer_config = PrinterConfig.query.filter_by(is_default=True).first()

    if not printer_config:
        return jsonify({"error": "No printer configured"}), 400

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

        return jsonify({
            "success": True,
            "history_id": history.id,
            "message": "Receipt printed successfully"
        })

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

        return jsonify({
            "success": False,
            "history_id": history.id,
            "error": str(e)
        }), 500


@api_bp.route("/preview", methods=["POST"])
def preview_receipt():
    """Preview a receipt without printing.

    Request body:
    {
        "template_id": 1,
        "variables": {"date": "2024-01-15", ...}
    }
    OR
    {
        "content": "[center]...",
        "variables": {"date": "2024-01-15", ...}
    }
    """
    data = request.json

    template_id = data.get("template_id")
    content = data.get("content")

    if template_id:
        template = Template.query.get(template_id)
        if not template:
            return jsonify({"error": "Template not found"}), 404
        content = template.content
    elif not content:
        return jsonify({"error": "template_id or content is required"}), 400

    variables = data.get("variables", {})
    renderer = TemplateRenderer()

    preview = renderer.render_preview(content, variables)
    extracted_vars = renderer.extract_variables(content)

    return jsonify({
        "preview": preview,
        "variables": extracted_vars
    })


# History API

@api_bp.route("/history", methods=["GET"])
def list_history():
    """List print history.

    Query params:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)
    - status: Filter by status (success/failed)
    - template_id: Filter by template
    """
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    query = PrintHistory.query.order_by(PrintHistory.printed_at.desc())

    status = request.args.get("status")
    if status:
        query = query.filter_by(status=status)

    template_id = request.args.get("template_id", type=int)
    if template_id:
        query = query.filter_by(template_id=template_id)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "history": [h.to_dict() for h in pagination.items],
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev
    })


@api_bp.route("/history/<int:history_id>", methods=["GET"])
def get_history(history_id):
    """Get a specific history record."""
    record = PrintHistory.query.get_or_404(history_id)
    return jsonify(record.to_dict())
