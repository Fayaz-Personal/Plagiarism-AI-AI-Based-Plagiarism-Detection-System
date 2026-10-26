import os
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort
from extensions import db
from models.document_models import Document, Analysis, SimilarityResult

documents_bp = Blueprint('documents', __name__)


@documents_bp.route('/documents')
def index():
    """Document library view with filtering, search, sorting, and pagination."""
    search_query = request.args.get('search', '').strip()
    category = request.args.get('category', 'all').strip()
    file_type = request.args.get('type', 'all').strip().lower()
    sort_by = request.args.get('sort', 'date_desc').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 10

    query = Document.query

    # Search filter
    if search_query:
        query = query.filter(Document.original_filename.ilike(f'%{search_query}%'))

    # Category filter
    if category in ['submitted', 'reference']:
        query = query.filter_by(document_type=category)

    # File type filter
    if file_type in ['pdf', 'docx', 'txt']:
        query = query.filter_by(file_type=file_type)

    # Sorting
    if sort_by == 'date_asc':
        query = query.order_by(Document.upload_date.asc())
    elif sort_by == 'name_asc':
        query = query.order_by(Document.original_filename.asc())
    elif sort_by == 'size_desc':
        query = query.order_by(Document.file_size.desc())
    else:  # default date_desc
        query = query.order_by(Document.upload_date.desc())

    # Pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    documents = pagination.items

    return render_template(
        'documents.html',
        documents=documents,
        pagination=pagination,
        search_query=search_query,
        category=category,
        file_type=file_type,
        sort_by=sort_by
    )


@documents_bp.route('/documents/<int:document_id>')
def details(document_id: int):
    """View details of a specific document, including extracted text preview and analysis links."""
    doc = db.get_or_404(Document, document_id)
    analyses = Analysis.query.filter_by(document_id=doc.id).order_by(Analysis.analysis_date.desc()).all()
    reference_matches_count = SimilarityResult.query.filter_by(reference_document_id=doc.id).count()

    return render_template(
        'document_details.html',
        document=doc,
        analyses=analyses,
        reference_matches_count=reference_matches_count
    )


@documents_bp.route('/documents/<int:document_id>/delete', methods=['POST'])
def delete_document(document_id: int):
    """Safely delete a document and its stored physical file."""
    doc = db.get_or_404(Document, document_id)
    upload_folder = Path(current_app.config['UPLOAD_FOLDER']).resolve()

    # Safe filesystem path resolution to prevent path traversal
    stored_path = (upload_folder / doc.stored_filename).resolve()
    try:
        if stored_path.is_relative_to(upload_folder):
            if stored_path.is_file():
                os.remove(stored_path)
    except Exception as e:
        current_app.logger.error(f"Error removing file {stored_path}: {e}")

    filename = doc.original_filename
    doc_type = doc.document_type

    if doc_type == 'reference':
        # Safely remove from reference candidate pool
        doc.is_active = False
        db.session.delete(doc)
    else:
        # Cascade delete removes associated analyses
        db.session.delete(doc)

    db.session.commit()
    flash(f"Document '{filename}' was successfully removed from the system.", 'success')
    if doc_type == 'reference':
        return redirect(url_for('documents.reference_library'))
    return redirect(url_for('documents.index'))


@documents_bp.route('/references')
def reference_library():
    """Dedicated reference document library view."""
    search_query = request.args.get('search', '').strip()
    file_type = request.args.get('type', 'all').strip().lower()
    sort_by = request.args.get('sort', 'date_desc').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 10

    query = Document.query.filter_by(document_type='reference', is_active=True)

    if search_query:
        query = query.filter(Document.original_filename.ilike(f'%{search_query}%'))

    if file_type in ['pdf', 'docx', 'txt']:
        query = query.filter_by(file_type=file_type)

    if sort_by == 'date_asc':
        query = query.order_by(Document.upload_date.asc())
    elif sort_by == 'name_asc':
        query = query.order_by(Document.original_filename.asc())
    elif sort_by == 'size_desc':
        query = query.order_by(Document.file_size.desc())
    else:
        query = query.order_by(Document.upload_date.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    references = pagination.items

    return render_template(
        'references.html',
        references=references,
        pagination=pagination,
        search_query=search_query,
        file_type=file_type,
        sort_by=sort_by
    )
