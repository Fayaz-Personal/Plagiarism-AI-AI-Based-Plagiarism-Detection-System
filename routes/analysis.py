import os
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort
from werkzeug.utils import secure_filename

from extensions import db
from models.document_models import Document, Analysis, SimilarityResult, SentenceMatch, Setting
from plagiarism.document_processor import (
    generate_safe_filename,
    is_allowed_file,
    extract_text,
    compute_file_hash,
    DocumentExtractionError
)
from plagiarism.plagiarism_engine import analyze_document
from plagiarism.preprocessing import segment_sentences, highlight_diff_words

analysis_bp = Blueprint('analysis', __name__)


@analysis_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    """Document upload page and handler."""
    if request.method == 'GET':
        reference_count = Document.query.filter_by(document_type='reference', is_active=True).count()
        reference_docs = Document.query.filter_by(document_type='reference', is_active=True).order_by(Document.upload_date.desc()).all()
        return render_template('upload.html', reference_count=reference_count, reference_docs=reference_docs)

    # Handle POST
    if 'document_file' not in request.files:
        flash("No file was submitted with the request.", 'danger')
        return redirect(url_for('analysis.upload'))

    file = request.files['document_file']
    if not file or not file.filename:
        flash("Please select a document file to upload.", 'warning')
        return redirect(url_for('analysis.upload'))

    allowed_exts = current_app.config['ALLOWED_EXTENSIONS']
    if not is_allowed_file(file.filename, allowed_exts):
        ext_list = ", ".join(f".{e}" for e in sorted(allowed_exts))
        flash(f"Unsupported file format. Please upload {ext_list} files only.", 'danger')
        return redirect(url_for('analysis.upload'))

    # Document type: 'submitted' or 'reference'
    doc_type = request.form.get('document_type', 'submitted').strip().lower()
    if doc_type not in ['submitted', 'reference']:
        doc_type = 'submitted'

    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size == 0:
        flash("The uploaded file is empty (0 bytes). Please upload a valid document.", 'danger')
        return redirect(url_for('analysis.upload'))

    max_size = current_app.config['MAX_CONTENT_LENGTH']
    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        flash(f"File size exceeds the maximum limit of {max_mb:.0f} MB.", 'danger')
        return redirect(url_for('analysis.upload'))

    # Generate safe server-side filename
    stored_name, ext = generate_safe_filename(file.filename)
    upload_folder = Path(current_app.config['UPLOAD_FOLDER']).resolve()
    upload_folder.mkdir(parents=True, exist_ok=True)
    destination = (upload_folder / stored_name).resolve()

    # Safety check against path traversal
    if not destination.is_relative_to(upload_folder):
        flash("Security violation: Invalid filename path.", 'danger')
        return redirect(url_for('analysis.upload'))

    try:
        file.save(str(destination))
    except Exception as e:
        flash(f"Failed to save file: {str(e)}", 'danger')
        return redirect(url_for('analysis.upload'))

    # Compute cryptographic file hash for duplicate detection
    file_hash = compute_file_hash(str(destination))
    duplicate_doc = Document.query.filter_by(file_hash=file_hash, is_active=True).first()
    if duplicate_doc:
        flash(
            f"Duplicate file notice: A document with identical content ('{duplicate_doc.original_filename}') was already uploaded on {duplicate_doc.upload_date.strftime('%b %d, %Y')}.",
            'info'
        )

    # Extract text and page count
    extracted_text, error_msg, is_scanned, page_count = extract_text(str(destination), ext)

    if error_msg:
        if is_scanned:
            flash(error_msg, 'warning')
        else:
            flash(f"Text extraction failed: {error_msg}", 'danger')

    if not extracted_text.strip():
        # Clean up file on unextractable text
        if destination.is_file():
            os.remove(destination)
        flash("No readable text could be extracted from this document. Please ensure it contains readable text.", 'danger')
        return redirect(url_for('analysis.upload'))

    # Calculate basic statistics
    sentences = segment_sentences(extracted_text)
    word_count = len(extracted_text.split())

    # Create document record
    doc = Document(
        original_filename=file.filename,
        stored_filename=stored_name,
        file_type=ext,
        file_size=file_size,
        file_hash=file_hash,
        page_count=page_count,
        document_type=doc_type,
        extracted_text=extracted_text,
        word_count=word_count,
        sentence_count=len(sentences),
        processing_status='processed',
        is_active=True
    )
    db.session.add(doc)
    db.session.commit()

    if doc_type == 'reference':
        flash(f"Reference document '{doc.original_filename}' successfully added to the reference library.", 'success')
        return redirect(url_for('documents.reference_library'))
    else:
        analyze_now = request.form.get('analyze_now') == '1'
        if analyze_now:
            return redirect(url_for('analysis.run_analysis', document_id=doc.id))
        flash(f"Document '{doc.original_filename}' uploaded successfully.", 'success')
        return redirect(url_for('analysis.analyze_page'))


@analysis_bp.route('/analyze')
def analyze_page():
    """Selection page to pick an uploaded document and start analysis."""
    submitted_docs = Document.query.filter_by(
        document_type='submitted',
        is_active=True
    ).order_by(Document.upload_date.desc()).all()

    reference_count = Document.query.filter_by(
        document_type='reference',
        is_active=True
    ).count()

    return render_template(
        'analyze.html',
        submitted_docs=submitted_docs,
        reference_count=reference_count
    )


@analysis_bp.route('/analyze/<int:document_id>', methods=['POST', 'GET'])
def run_analysis(document_id: int):
    """Executes plagiarism analysis on the selected document."""
    doc = db.get_or_404(Document, document_id)

    try:
        analysis = analyze_document(doc.id)
        if analysis.analysis_status == 'no_references':
            flash("Notice: No reference documents are available in the system library. Please upload reference documents to perform comparison.", 'warning')
        elif analysis.analysis_status == 'failed':
            flash(f"Analysis could not be completed: {analysis.error_message}", 'danger')
        else:
            flash(f"Analysis completed successfully for '{doc.original_filename}'.", 'success')
        return redirect(url_for('analysis.results', analysis_id=analysis.id))
    except Exception as e:
        flash(f"An error occurred during analysis: {str(e)}", 'danger')
        return redirect(url_for('analysis.analyze_page'))


@analysis_bp.route('/results/<int:analysis_id>')
def results(analysis_id: int):
    """Detailed plagiarism analysis results view with word diff highlights."""
    analysis = db.get_or_404(Analysis, analysis_id)
    pairwise_results = SimilarityResult.query.filter_by(analysis_id=analysis.id).order_by(
        SimilarityResult.document_similarity_score.desc()
    ).all()
    sentence_matches = SentenceMatch.query.filter_by(analysis_id=analysis.id).order_by(
        SentenceMatch.similarity_score.desc()
    ).all()

    # Pre-render highlighted HTML for each match card
    enriched_matches = []
    unique_references = set()
    for m in sentence_matches:
        hl_sub, hl_ref, _ = highlight_diff_words(m.submitted_sentence, m.reference_sentence)
        unique_references.add(m.reference_document_name)
        enriched_matches.append({
            'match': m,
            'highlighted_sub': hl_sub,
            'highlighted_ref': hl_ref,
            'reference_name': m.reference_document_name,
            'score': m.percentage_score,
            'category': getattr(m, 'match_category', 'Moderate Match'),
            'explanation': getattr(m, 'match_explanation', 'Textual overlap detected.')
        })

    # Threshold settings for display
    threshold_low = float(current_app.config.get('SIMILARITY_THRESHOLD_LOW', 10.0))
    threshold_mod = float(current_app.config.get('SIMILARITY_THRESHOLD_MODERATE', 30.0))
    threshold_high = float(current_app.config.get('SIMILARITY_THRESHOLD_HIGH', 60.0))

    return render_template(
        'results.html',
        analysis=analysis,
        pairwise_results=pairwise_results,
        enriched_matches=enriched_matches,
        unique_references=sorted(list(unique_references)),
        threshold_low=threshold_low,
        threshold_mod=threshold_mod,
        threshold_high=threshold_high
    )


@analysis_bp.route('/history')
def history():
    """Analysis history view with searching, date filtering, and status filtering."""
    search_query = request.args.get('search', '').strip()
    category_filter = request.args.get('category', 'all').strip()
    status_filter = request.args.get('status', 'all').strip()
    date_filter = request.args.get('date', 'all').strip()
    sort_by = request.args.get('sort', 'date_desc').strip()

    query = Analysis.query.join(Document)

    # Search filter
    if search_query:
        query = query.filter(Document.original_filename.ilike(f'%{search_query}%'))

    # Status filter
    if status_filter in ['completed', 'failed', 'no_references']:
        query = query.filter(Analysis.analysis_status == status_filter)

    # Date filter
    now = datetime.now(timezone.utc)
    if date_filter == 'today':
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.filter(Analysis.analysis_date >= start_of_day)
    elif date_filter == 'week':
        one_week_ago = now - timedelta(days=7)
        query = query.filter(Analysis.analysis_date >= one_week_ago)
    elif date_filter == 'month':
        one_month_ago = now - timedelta(days=30)
        query = query.filter(Analysis.analysis_date >= one_month_ago)

    # Sorting
    if sort_by == 'similarity_desc':
        query = query.order_by(Analysis.highest_similarity_score.desc())
    elif sort_by == 'similarity_asc':
        query = query.order_by(Analysis.highest_similarity_score.asc())
    elif sort_by == 'date_asc':
        query = query.order_by(Analysis.analysis_date.asc())
    else:  # default date_desc
        query = query.order_by(Analysis.analysis_date.desc())

    analyses = query.all()

    # Category filter
    if category_filter != 'all':
        analyses = [a for a in analyses if a.similarity_category.lower() == category_filter.lower()]

    return render_template(
        'history.html',
        analyses=analyses,
        search_query=search_query,
        category_filter=category_filter,
        status_filter=status_filter,
        date_filter=date_filter,
        sort_by=sort_by
    )


@analysis_bp.route('/history/<int:analysis_id>/delete', methods=['POST'])
def delete_analysis(analysis_id: int):
    """Safely deletes an individual analysis record without deleting documents."""
    analysis = db.get_or_404(Analysis, analysis_id)
    doc_name = analysis.document.original_filename if analysis.document else f"Analysis #{analysis_id}"

    db.session.delete(analysis)
    db.session.commit()
    flash(f"Analysis #{analysis_id} for '{doc_name}' was successfully removed.", 'success')
    return redirect(url_for('analysis.history'))
