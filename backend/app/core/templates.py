"""
Template rendering utilities
"""
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from fastapi import Request
from fastapi.templating import Jinja2Templates

# Get templates directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "frontend" / "templates"

# Create Jinja2 environment
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
    enable_async=True,
)

# Create FastAPI templates instance
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def render_template(template_name: str, context: dict, request: Request):
    """Render template with context"""
    return templates.TemplateResponse(template_name, {"request": request, **context})

