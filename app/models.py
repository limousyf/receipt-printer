"""Database models."""
import json
from datetime import datetime
from app import db


class Template(db.Model):
    """Receipt template model."""
    __tablename__ = "templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to print history
    prints = db.relationship("PrintHistory", backref="template", lazy="dynamic")

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Template {self.name}>"


class PrinterConfig(db.Model):
    """Printer configuration model."""
    __tablename__ = "printer_configs"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # network, usb, serial
    config_json = db.Column(db.Text, nullable=False)  # JSON: {ip, port} or {vendor_id, product_id} etc.
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def config(self):
        """Parse config JSON."""
        return json.loads(self.config_json) if self.config_json else {}

    @config.setter
    def config(self, value):
        """Set config as JSON."""
        self.config_json = json.dumps(value)

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "config": self.config,
            "is_default": self.is_default,
        }

    def __repr__(self):
        return f"<PrinterConfig {self.name} ({self.type})>"


class PrintHistory(db.Model):
    """Print history model."""
    __tablename__ = "print_history"

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey("templates.id"), nullable=True)
    variables_json = db.Column(db.Text, nullable=True)  # JSON of variables used
    rendered_preview = db.Column(db.Text, nullable=True)  # Text preview of what was printed
    printer_config_json = db.Column(db.Text, nullable=True)  # Snapshot of printer config used
    status = db.Column(db.String(20), nullable=False)  # success, failed
    error_message = db.Column(db.Text, nullable=True)
    printed_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def variables(self):
        """Parse variables JSON."""
        return json.loads(self.variables_json) if self.variables_json else {}

    @variables.setter
    def variables(self, value):
        """Set variables as JSON."""
        self.variables_json = json.dumps(value)

    @property
    def printer_config(self):
        """Parse printer config JSON."""
        return json.loads(self.printer_config_json) if self.printer_config_json else {}

    @printer_config.setter
    def printer_config(self, value):
        """Set printer config as JSON."""
        self.printer_config_json = json.dumps(value)

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "template_id": self.template_id,
            "template_name": self.template.name if self.template else None,
            "variables": self.variables,
            "rendered_preview": self.rendered_preview,
            "printer_config": self.printer_config,
            "status": self.status,
            "error_message": self.error_message,
            "printed_at": self.printed_at.isoformat() if self.printed_at else None,
        }

    def __repr__(self):
        return f"<PrintHistory {self.id} ({self.status})>"
