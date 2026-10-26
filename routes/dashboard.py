from collections import defaultdict
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from sqlalchemy import func
from extensions import db
from models.document_models import Document, Analysis
from seed_data import seed_sample_data

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def index():
    """Main dashboard page displaying real computed database metrics and analytics."""
    # Summary card calculations
    total_documents = Document.query.count()
    total_reference_docs = Document.query.filter_by(document_type='reference', is_active=True).count()
    total_submitted_docs = Document.query.filter_by(document_type='submitted', is_active=True).count()
    documents_analyzed = Analysis.query.filter_by(analysis_status='completed').count()

    avg_score_raw = db.session.query(
        func.avg(Analysis.highest_similarity_score)
    ).filter(Analysis.analysis_status == 'completed').scalar()
    avg_similarity_score = round(float(avg_score_raw), 1) if avg_score_raw is not None else 0.0

    # High similarity reports (score >= 30%)
    high_similarity_reports = Analysis.query.filter(
        Analysis.analysis_status == 'completed',
        Analysis.highest_similarity_score >= 30.0
    ).count()

    # Recent Analyses (Limit to 6 for clean visual balance)
    recent_analyses = Analysis.query.order_by(Analysis.analysis_date.desc()).limit(6).all()

    # Recent Uploads (Limit to 5)
    recent_uploads = Document.query.order_by(Document.upload_date.desc()).limit(5).all()

    # Similarity distribution calculation for Chart.js
    completed_analyses = Analysis.query.filter_by(analysis_status='completed').all()
    dist_low = sum(1 for a in completed_analyses if a.highest_similarity_score < 10.0)
    dist_moderate = sum(1 for a in completed_analyses if 10.0 <= a.highest_similarity_score < 30.0)
    dist_elevated = sum(1 for a in completed_analyses if 30.0 <= a.highest_similarity_score < 60.0)
    dist_high = sum(1 for a in completed_analyses if a.highest_similarity_score >= 60.0)

    distribution_data = {
        'low': dist_low,
        'moderate': dist_moderate,
        'elevated': dist_elevated,
        'high': dist_high
    }

    # Document format breakdown for Chart.js
    all_docs = Document.query.all()
    format_counts = {'pdf': 0, 'docx': 0, 'txt': 0}
    for d in all_docs:
        ftype = d.file_type.lower()
        if ftype in format_counts:
            format_counts[ftype] += 1
        else:
            format_counts['txt'] += 1

    format_data = {
        'pdf': format_counts['pdf'],
        'docx': format_counts['docx'],
        'txt': format_counts['txt']
    }

    # Activity over time (analyses per day for timeline chart)
    activity_map = defaultdict(int)
    for a in completed_analyses:
        date_str = a.analysis_date.strftime('%b %d')
        activity_map[date_str] += 1

    activity_data = {
        'labels': list(activity_map.keys())[-7:],
        'counts': list(activity_map.values())[-7:]
    }

    reports_count = documents_analyzed

    # Real recent activity log derived directly from database records
    recent_activity = []
    for a in recent_analyses:
        doc_name = a.document.original_filename if a.document else f"Document #{a.document_id}"
        recent_activity.append({
            'type': 'analysis',
            'timestamp': a.analysis_date,
            'title': f"Similarity check completed: {doc_name}",
            'desc': f"Similarity: {a.highest_similarity_score}% ({a.similarity_category}) across {a.references_compared} references",
            'score': a.highest_similarity_score,
            'category': a.similarity_category,
            'badge_class': a.badge_color_class,
            'url': url_for('analysis.results', analysis_id=a.id),
            'action': 'View Report'
        })
    for u in recent_uploads:
        is_ref = (u.document_type == 'reference')
        recent_activity.append({
            'type': 'upload',
            'timestamp': u.upload_date,
            'title': f"{'Reference document' if is_ref else 'Submitted document'} uploaded: {u.original_filename}",
            'desc': f"{u.word_count} words extracted ({u.formatted_size})",
            'score': None,
            'category': 'Reference' if is_ref else 'Submitted',
            'badge_class': 'badge-info' if is_ref else 'badge-secondary',
            'url': url_for('documents.details', document_id=u.id),
            'action': 'Document Details'
        })
    recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)

    return render_template(
        'dashboard.html',
        total_documents=total_documents,
        total_reference_docs=total_reference_docs,
        total_submitted_docs=total_submitted_docs,
        documents_analyzed=documents_analyzed,
        reports_count=reports_count,
        avg_similarity_score=avg_similarity_score,
        high_similarity_reports=high_similarity_reports,
        recent_analyses=recent_analyses,
        recent_uploads=recent_uploads,
        recent_activity=recent_activity[:8],
        distribution_data=distribution_data,
        format_data=format_data,
        activity_data=activity_data,
        reference_count=total_reference_docs
    )


@dashboard_bp.route('/seed-demo', methods=['POST'])
def generate_demo_data():
    """Generates synthetic academic demonstration data and analyzes sample document."""
    try:
        msg = seed_sample_data(current_app)
        flash(msg, 'success')
    except Exception as e:
        flash(f"Error generating sample data: {str(e)}", 'danger')

    return redirect(url_for('dashboard.index'))
