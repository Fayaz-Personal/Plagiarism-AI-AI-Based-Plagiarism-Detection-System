from routes.dashboard import dashboard_bp
from routes.documents import documents_bp
from routes.analysis import analysis_bp
from routes.reports import reports_bp
from routes.settings import settings_bp
from routes.methodology import methodology_bp

__all__ = [
    'dashboard_bp',
    'documents_bp',
    'analysis_bp',
    'reports_bp',
    'settings_bp',
    'methodology_bp'
]
