import os
from pathlib import Path
from flask import Flask, render_template
from config import Config
from extensions import db, csrf
from routes import (
    dashboard_bp,
    documents_bp,
    analysis_bp,
    reports_bp,
    settings_bp,
    methodology_bp
)


def ensure_schema_upgrades(app):
    """Safely check and add any newly introduced columns to existing SQLite tables."""
    from sqlalchemy import text
    with app.app_context():
        db.create_all()
        try:
            with db.engine.connect() as conn:
                # Check documents columns
                doc_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(documents)")).fetchall()]
                if doc_cols:
                    if 'file_hash' not in doc_cols:
                        conn.execute(text("ALTER TABLE documents ADD COLUMN file_hash VARCHAR(64)"))
                    if 'page_count' not in doc_cols:
                        conn.execute(text("ALTER TABLE documents ADD COLUMN page_count INTEGER"))

                # Check analyses columns
                ana_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(analyses)")).fetchall()]
                if ana_cols:
                    if 'originality_score' not in ana_cols:
                        conn.execute(text("ALTER TABLE analyses ADD COLUMN originality_score FLOAT DEFAULT 0.0"))

                # Check sentence_matches columns
                sm_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(sentence_matches)")).fetchall()]
                if sm_cols:
                    if 'match_category' not in sm_cols:
                        conn.execute(text("ALTER TABLE sentence_matches ADD COLUMN match_category VARCHAR(50) DEFAULT 'Moderate Match'"))
                    if 'match_explanation' not in sm_cols:
                        conn.execute(text("ALTER TABLE sentence_matches ADD COLUMN match_explanation VARCHAR(255)"))
                    if 'overlapping_words' not in sm_cols:
                        conn.execute(text("ALTER TABLE sentence_matches ADD COLUMN overlapping_words TEXT"))

                conn.commit()
        except Exception as e:
            app.logger.warning(f"Schema upgrade note: {e}")


def create_app(config_class=Config):
    """Application factory pattern for PlagiarismAI."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure required directories exist
    upload_path = Path(app.config['UPLOAD_FOLDER'])
    report_path = Path(app.config['REPORT_FOLDER'])
    instance_path = Path(app.instance_path)

    upload_path.mkdir(parents=True, exist_ok=True)
    report_path.mkdir(parents=True, exist_ok=True)
    instance_path.mkdir(parents=True, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    csrf.init_app(app)

    # Register blueprints
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(methodology_bp)

    # Register context processors
    @app.context_processor
    def inject_global_data():
        return {
            'app_name': 'PlagiarismAI',
            'app_tagline': 'Verify Originality. Protect Academic Integrity.',
            'app_version': '1.0.0',
            'current_year': 2026
        }

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500

    @app.errorhandler(413)
    def request_entity_too_large(e):
        return render_template(
            '500.html',
            error_title="File Too Large",
            error_message="The uploaded document exceeds the maximum allowed file size."
        ), 413

    # Automatically create and upgrade database tables if needed
    ensure_schema_upgrades(app)

    # Register CLI seed command
    @app.cli.command('seed-data')
    def seed_data_command():
        """CLI command to seed sample academic data."""
        from seed_data import seed_sample_data
        msg = seed_sample_data(app)
        print(msg)

    return app


if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='127.0.0.1', port=port, debug=True)
