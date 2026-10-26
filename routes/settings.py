from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from extensions import db
from models.document_models import Setting
from plagiarism.ocr_engine import get_ocr_status
from plagiarism.semantic_engine import get_semantic_status

settings_bp = Blueprint('settings', __name__)

DEFAULT_SETTINGS = {
    'SENTENCE_SIMILARITY_THRESHOLD': ('0.70', 'Cosine similarity threshold for sentence match detection (0.10 - 0.99)'),
    'MIN_SENTENCE_LENGTH': ('20', 'Minimum character length for evaluated sentences (5 - 200 chars)'),
    'MAX_CONTENT_LENGTH_MB': ('10', 'Maximum document upload limit in Megabytes (1 - 100 MB)'),
    'SIMILARITY_THRESHOLD_LOW': ('10.0', 'Threshold ceiling for Low Similarity category (%)'),
    'SIMILARITY_THRESHOLD_MODERATE': ('30.0', 'Threshold ceiling for Moderate Similarity category (%)'),
    'SIMILARITY_THRESHOLD_HIGH': ('60.0', 'Threshold ceiling for Elevated Similarity category (%)'),
}


def get_current_settings():
    """Retrieve all application settings with fallbacks."""
    settings = {}
    for key, (default_val, desc) in DEFAULT_SETTINGS.items():
        record = Setting.query.filter_by(key=key).first()
        if record:
            settings[key] = record.value
        else:
            settings[key] = default_val
    return settings


@settings_bp.route('/settings', methods=['GET', 'POST'])
def index():
    """Settings view and updater."""
    if request.method == 'GET':
        settings = get_current_settings()
        ocr_status = get_ocr_status()
        semantic_status = get_semantic_status()
        return render_template(
            'settings.html',
            settings=settings,
            ocr_status=ocr_status,
            semantic_status=semantic_status
        )

    # Process settings update
    try:
        sent_thresh_raw = request.form.get('sentence_similarity_threshold')
        min_len_raw = request.form.get('min_sentence_length')
        max_mb_raw = request.form.get('max_content_length_mb')
        sim_low_raw = request.form.get('similarity_threshold_low')
        sim_mod_raw = request.form.get('similarity_threshold_moderate')
        sim_high_raw = request.form.get('similarity_threshold_high')

        if not all([sent_thresh_raw, min_len_raw, max_mb_raw, sim_low_raw, sim_mod_raw, sim_high_raw]):
            flash("All configuration fields are required.", 'danger')
            return redirect(url_for('settings.index'))

        sent_thresh = float(sent_thresh_raw)
        min_len = int(min_len_raw)
        max_mb = int(max_mb_raw)
        sim_low = float(sim_low_raw)
        sim_mod = float(sim_mod_raw)
        sim_high = float(sim_high_raw)

        # Validate ranges
        if not (0.10 <= sent_thresh <= 0.99):
            flash("Sentence similarity threshold must be between 0.10 and 0.99.", 'danger')
            return redirect(url_for('settings.index'))

        if min_len < 5 or min_len > 200:
            flash("Minimum sentence length must be between 5 and 200 characters.", 'danger')
            return redirect(url_for('settings.index'))

        if max_mb < 1 or max_mb > 100:
            flash("Max upload size must be between 1 MB and 100 MB.", 'danger')
            return redirect(url_for('settings.index'))

        if not (0 < sim_low < sim_mod < sim_high < 100):
            flash("Category thresholds must satisfy: 0 < Low < Moderate < Elevated < 100.", 'danger')
            return redirect(url_for('settings.index'))

        # Save to database
        updates = {
            'SENTENCE_SIMILARITY_THRESHOLD': str(sent_thresh),
            'MIN_SENTENCE_LENGTH': str(min_len),
            'MAX_CONTENT_LENGTH_MB': str(max_mb),
            'SIMILARITY_THRESHOLD_LOW': str(sim_low),
            'SIMILARITY_THRESHOLD_MODERATE': str(sim_mod),
            'SIMILARITY_THRESHOLD_HIGH': str(sim_high),
        }

        for k, v in updates.items():
            record = Setting.query.filter_by(key=k).first()
            if not record:
                record = Setting(key=k, value=v, description=DEFAULT_SETTINGS[k][1])
                db.session.add(record)
            else:
                record.value = v

        db.session.commit()

        # Update in-memory app config
        current_app.config['SENTENCE_SIMILARITY_THRESHOLD'] = sent_thresh
        current_app.config['MIN_SENTENCE_LENGTH'] = min_len
        current_app.config['MAX_CONTENT_LENGTH'] = max_mb * 1024 * 1024
        current_app.config['SIMILARITY_THRESHOLD_LOW'] = sim_low
        current_app.config['SIMILARITY_THRESHOLD_MODERATE'] = sim_mod
        current_app.config['SIMILARITY_THRESHOLD_HIGH'] = sim_high

        flash("Settings saved and updated successfully.", 'success')
    except ValueError as e:
        flash(f"Invalid numerical format: {str(e)}", 'danger')
    except Exception as e:
        flash(f"Error saving settings: {str(e)}", 'danger')

    return redirect(url_for('settings.index'))


@settings_bp.route('/settings/reset', methods=['POST'])
def reset_defaults():
    """Resets all settings to their default values."""
    try:
        for k, (default_val, desc) in DEFAULT_SETTINGS.items():
            record = Setting.query.filter_by(key=k).first()
            if record:
                record.value = default_val
            else:
                record = Setting(key=k, value=default_val, description=desc)
                db.session.add(record)
        db.session.commit()

        # Restore in-memory config defaults
        current_app.config['SENTENCE_SIMILARITY_THRESHOLD'] = 0.70
        current_app.config['MIN_SENTENCE_LENGTH'] = 20
        current_app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
        current_app.config['SIMILARITY_THRESHOLD_LOW'] = 10.0
        current_app.config['SIMILARITY_THRESHOLD_MODERATE'] = 30.0
        current_app.config['SIMILARITY_THRESHOLD_HIGH'] = 60.0

        flash("All settings have been restored to default values.", 'success')
    except Exception as e:
        flash(f"Error restoring defaults: {str(e)}", 'danger')

    return redirect(url_for('settings.index'))
