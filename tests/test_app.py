import os
from pathlib import Path
from extensions import db
from models.document_models import Document, Analysis, Setting
from app import create_app
from config import Config


def test_12_previous_analyses_remain_available_after_restart(test_dirs):
    """TEST 12: Verify that previous analyses remain available after the application restarts."""
    db_file = Path(test_dirs['root']) / "persistent_test.db"
    db_uri = f"sqlite:///{db_file}"

    class PersistentConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = db_uri
        WTF_CSRF_ENABLED = False
        UPLOAD_FOLDER = test_dirs['uploads']
        REPORT_FOLDER = test_dirs['reports']
        SERVER_NAME = 'localhost'

    # App Instance 1: Create document and analysis
    app1 = create_app(PersistentConfig)
    with app1.app_context():
        doc = Document(
            original_filename="persistent_paper.txt",
            stored_filename="persistent_paper.txt",
            file_type="txt",
            file_size=150,
            document_type="submitted",
            extracted_text="Text content for persistence verification test.",
            is_active=True
        )
        db.session.add(doc)
        db.session.commit()

        analysis = Analysis(
            document_id=doc.id,
            highest_similarity_score=38.2,
            average_similarity_score=19.1,
            references_compared=2,
            matching_sentence_count=1,
            analysis_status="completed"
        )
        db.session.add(analysis)
        db.session.commit()
        analysis_id = analysis.id

    # App Instance 2: Simulating server restart
    app2 = create_app(PersistentConfig)
    with app2.app_context():
        retrieved = db.session.get(Analysis, analysis_id)
        assert retrieved is not None
        assert retrieved.highest_similarity_score == 38.2
        assert retrieved.document.original_filename == "persistent_paper.txt"


def test_13_invalid_document_ids_produce_appropriate_errors(client):
    """TEST 13: Verify that invalid document IDs produce appropriate errors (404 instead of raw crash)."""
    # Test invalid document details route
    response = client.get('/documents/999999')
    assert response.status_code == 404

    # Test invalid results route
    response = client.get('/results/999999')
    assert response.status_code == 404

    # Test invalid report download route
    response = client.get('/reports/999999/pdf')
    assert response.status_code == 404


def test_dashboard_renders_with_real_metrics(client, app):
    """Verify that the dashboard loads cleanly and calculates database metrics."""
    with app.app_context():
        doc = Document(
            original_filename="dashboard_test.txt",
            stored_filename="dashboard_test.txt",
            file_type="txt",
            file_size=120,
            document_type="submitted",
            extracted_text="Testing dashboard calculations.",
            is_active=True
        )
        db.session.add(doc)
        db.session.commit()

    response = client.get('/')
    assert response.status_code == 200
    assert b"Total Documents" in response.data
    assert b"PlagiarismAI" in response.data


def test_settings_update_and_validation(client, app):
    """Verify settings update route and validation rules."""
    # Valid update
    valid_data = {
        'sentence_similarity_threshold': '0.75',
        'min_sentence_length': '25',
        'max_content_length_mb': '15',
        'similarity_threshold_low': '15.0',
        'similarity_threshold_moderate': '35.0',
        'similarity_threshold_high': '65.0'
    }
    resp = client.post('/settings', data=valid_data, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Settings saved and updated successfully" in resp.data

    with app.app_context():
        thresh = Setting.query.filter_by(key='SENTENCE_SIMILARITY_THRESHOLD').first()
        assert thresh is not None
        assert thresh.value == '0.75'

    # Invalid update (inverted thresholds)
    invalid_data = {
        'sentence_similarity_threshold': '0.75',
        'min_sentence_length': '25',
        'max_content_length_mb': '15',
        'similarity_threshold_low': '50.0',
        'similarity_threshold_moderate': '20.0',  # Invalid: moderate < low
        'similarity_threshold_high': '65.0'
    }
    resp = client.post('/settings', data=invalid_data, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Category thresholds must satisfy" in resp.data


def test_methodology_and_about_pages(client):
    """Verify that About and Methodology pages render complete mathematical documentation."""
    resp1 = client.get('/methodology')
    assert resp1.status_code == 200
    assert b"Detection Methodology" in resp1.data
    assert b"TF-IDF" in resp1.data
    assert b"Cosine Similarity" in resp1.data

    resp2 = client.get('/about')
    assert resp2.status_code == 200
    assert b"Methodology &amp; Architecture" in resp2.data or b"Methodology & Architecture" in resp2.data
    assert b"PlagiarismAI" in resp2.data
    assert b"B.Tech Computer Science" in resp2.data


def test_delete_analysis_record_preserves_documents(client, app):
    """Verify that deleting an analysis record does NOT delete the submitted or reference documents."""
    with app.app_context():
        doc = Document(
            original_filename="preserve_test.txt",
            stored_filename="preserve_test.txt",
            file_type="txt",
            file_size=100,
            document_type="submitted",
            extracted_text="Content to verify document preservation during analysis deletion.",
            is_active=True
        )
        db.session.add(doc)
        db.session.commit()

        analysis = Analysis(
            document_id=doc.id,
            highest_similarity_score=40.0,
            average_similarity_score=20.0,
            references_compared=1,
            matching_sentence_count=1,
            analysis_status="completed"
        )
        db.session.add(analysis)
        db.session.commit()
        analysis_id = analysis.id
        doc_id = doc.id

    # Delete the analysis record via POST
    del_resp = client.post(f'/history/{analysis_id}/delete', follow_redirects=True)
    assert del_resp.status_code == 200
    assert b"successfully removed" in del_resp.data

    # Verify that Analysis is gone but Document remains intact
    with app.app_context():
        assert db.session.get(Analysis, analysis_id) is None
        assert db.session.get(Document, doc_id) is not None


def test_documents_library_search_filter_pagination(client, app):
    """Verify document library querying with filtering and pagination."""
    with app.app_context():
        for i in range(15):
            d = Document(
                original_filename=f"paper_batch_{i}.txt",
                stored_filename=f"paper_batch_{i}.txt",
                file_type="txt",
                file_size=100 + i,
                document_type="reference" if i % 2 == 0 else "submitted",
                extracted_text=f"Batch sample text for index {i}.",
                is_active=True
            )
            db.session.add(d)
        db.session.commit()

    # Query page 1
    resp1 = client.get('/documents?page=1')
    assert resp1.status_code == 200
    assert b"paper_batch_" in resp1.data

    # Query with category filter
    resp_ref = client.get('/documents?category=reference')
    assert resp_ref.status_code == 200

    # Query with search
    resp_search = client.get('/documents?search=batch_5')
    assert resp_search.status_code == 200
    assert b"paper_batch_5.txt" in resp_search.data

