from pathlib import Path
from flask import Blueprint, render_template, send_file, current_app, abort, flash, redirect, url_for
from werkzeug.utils import secure_filename
from extensions import db
from models.document_models import Analysis
from plagiarism.report_generator import generate_pdf_report, generate_docx_report

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/reports')
def index():
    """Lists all available reports generated from completed analyses."""
    analyses = Analysis.query.filter_by(analysis_status='completed').order_by(Analysis.analysis_date.desc()).all()
    return render_template('reports.html', analyses=analyses)


@reports_bp.route('/reports/<int:analysis_id>/pdf')
def download_pdf(analysis_id: int):
    """Generates and downloads a formal academic plagiarism report in PDF format."""
    analysis = db.get_or_404(Analysis, analysis_id)

    report_folder = Path(current_app.config['REPORT_FOLDER']).resolve()
    report_folder.mkdir(parents=True, exist_ok=True)

    doc_name = analysis.document.original_filename if analysis.document else "Document"
    safe_name = secure_filename(doc_name.rsplit('.', 1)[0]) or f"doc_{analysis.document_id}"
    filename = f"PlagiarismReport_#{analysis.id}_{safe_name}.pdf"
    file_path = report_folder / filename

    try:
        generate_pdf_report(analysis, str(file_path))
        return send_file(
            str(file_path),
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    except Exception as e:
        current_app.logger.error(f"PDF Generation failed: {str(e)}")
        flash(f"Failed to generate PDF report: {str(e)}", 'danger')
        return redirect(url_for('analysis.results', analysis_id=analysis.id))


@reports_bp.route('/reports/<int:analysis_id>/docx')
def download_docx(analysis_id: int):
    """Generates and downloads a formal academic plagiarism report in Microsoft Word (.docx) format."""
    analysis = db.get_or_404(Analysis, analysis_id)

    report_folder = Path(current_app.config['REPORT_FOLDER']).resolve()
    report_folder.mkdir(parents=True, exist_ok=True)

    doc_name = analysis.document.original_filename if analysis.document else "Document"
    safe_name = secure_filename(doc_name.rsplit('.', 1)[0]) or f"doc_{analysis.document_id}"
    filename = f"PlagiarismReport_#{analysis.id}_{safe_name}.docx"
    file_path = report_folder / filename

    try:
        generate_docx_report(analysis, str(file_path))
        return send_file(
            str(file_path),
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    except Exception as e:
        current_app.logger.error(f"DOCX Generation failed: {str(e)}")
        flash(f"Failed to generate Word report: {str(e)}", 'danger')
        return redirect(url_for('analysis.results', analysis_id=analysis.id))
