import os
import shutil
import tempfile
from pathlib import Path
import pytest
import docx
from reportlab.pdfgen import canvas

from app import create_app
from config import TestingConfig
from extensions import db
from models.document_models import Document, Analysis


@pytest.fixture
def test_dirs():
    """Create isolated temporary upload and report directories."""
    temp_dir = tempfile.mkdtemp()
    upload_dir = Path(temp_dir) / 'uploads'
    report_dir = Path(temp_dir) / 'reports'
    upload_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    yield {
        'root': temp_dir,
        'uploads': upload_dir,
        'reports': report_dir
    }

    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def app(test_dirs):
    """Create and configure a clean Flask application instance for testing."""
    class CustomTestingConfig(TestingConfig):
        UPLOAD_FOLDER = test_dirs['uploads']
        REPORT_FOLDER = test_dirs['reports']
        WTF_CSRF_ENABLED = False
        SERVER_NAME = 'localhost'

    app = create_app(CustomTestingConfig)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


def create_sample_pdf(file_path: Path, text: str):
    """Helper to generate a real PDF with text layer for testing."""
    c = canvas.Canvas(str(file_path))
    c.drawString(72, 720, text)
    c.save()


def create_sample_docx(file_path: Path, text: str):
    """Helper to generate a real Word .docx document for testing."""
    doc = docx.Document()
    doc.add_paragraph(text)
    doc.save(str(file_path))
