import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')


class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'plagiarism-ai-dev-secret-key-2026')
    
    # SQLite Database stored in instance directory
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{BASE_DIR / 'instance' / 'plagiarism.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Directories
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    REPORT_FOLDER = BASE_DIR / 'reports'
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}

    # Upload restrictions (Default: 10 MB)
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH_MB', 10)) * 1024 * 1024

    # Plagiarism Algorithm Thresholds
    SENTENCE_SIMILARITY_THRESHOLD = float(os.environ.get('SENTENCE_SIMILARITY_THRESHOLD', 0.70))
    MIN_SENTENCE_LENGTH = int(os.environ.get('MIN_SENTENCE_LENGTH', 20))

    # Similarity Display Categories (Percentage thresholds)
    SIMILARITY_THRESHOLD_LOW = float(os.environ.get('SIMILARITY_THRESHOLD_LOW', 10.0))
    SIMILARITY_THRESHOLD_MODERATE = float(os.environ.get('SIMILARITY_THRESHOLD_MODERATE', 30.0))
    SIMILARITY_THRESHOLD_HIGH = float(os.environ.get('SIMILARITY_THRESHOLD_HIGH', 60.0))

    WTF_CSRF_ENABLED = True


class TestingConfig(Config):
    """Configuration for automated test suite."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    UPLOAD_FOLDER = BASE_DIR / 'instance' / 'test_uploads'
    REPORT_FOLDER = BASE_DIR / 'instance' / 'test_reports'
