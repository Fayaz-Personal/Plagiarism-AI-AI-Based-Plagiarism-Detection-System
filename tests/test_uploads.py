import io
from pathlib import Path
from models.document_models import Document
from plagiarism.document_processor import generate_safe_filename


def test_1_upload_valid_txt_document(client, app):
    """TEST 1: Upload a valid TXT document."""
    data = {
        'document_type': 'submitted',
        'document_file': (io.BytesIO(b"Artificial intelligence is transforming educational research and technology."), 'sample_paper.txt')
    }
    response = client.post('/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        doc = Document.query.filter_by(original_filename='sample_paper.txt').first()
        assert doc is not None
        assert doc.file_type == 'txt'
        assert "Artificial intelligence" in doc.extracted_text
        assert doc.word_count > 0


def test_2_reject_unsupported_file_format(client, app):
    """TEST 2: Reject an unsupported file format (e.g. .exe, .py, .csv)."""
    data = {
        'document_type': 'submitted',
        'document_file': (io.BytesIO(b"print('Malicious executable script')"), 'malicious_script.py')
    }
    response = client.post('/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b"Unsupported file format" in response.data

    with app.app_context():
        doc = Document.query.filter_by(original_filename='malicious_script.py').first()
        assert doc is None


def test_3_reject_empty_document(client, app):
    """TEST 3: Reject an empty document (0 bytes)."""
    data = {
        'document_type': 'submitted',
        'document_file': (io.BytesIO(b""), 'empty_document.txt')
    }
    response = client.post('/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b"The uploaded file is empty" in response.data

    with app.app_context():
        doc = Document.query.filter_by(original_filename='empty_document.txt').first()
        assert doc is None


def test_15_uploaded_filenames_cannot_escape_upload_directory(app, test_dirs):
    """TEST 15: Verify that uploaded filenames cannot escape the upload directory."""
    # Attempt malicious path traversal in filename
    malicious_filename = "../../../../etc/passwd.txt"
    stored_name, ext = generate_safe_filename(malicious_filename)

    upload_folder = Path(app.config['UPLOAD_FOLDER']).resolve()
    resolved_target = (upload_folder / stored_name).resolve()

    # The stored filename must not have directory traversal components and must resolve strictly inside uploads
    assert ".." not in stored_name
    assert resolved_target.is_relative_to(upload_folder)
    assert resolved_target.parent == upload_folder


def test_sha256_duplicate_warning(client, app):
    """Verify that uploading an identical file hash records hash and triggers duplicate detection notice."""
    content = b"Cryptographic content hashing ensures that identical uploaded files are flagged cleanly."
    data1 = {
        'document_type': 'submitted',
        'document_file': (io.BytesIO(content), 'hash_test_1.txt')
    }
    resp1 = client.post('/upload', data=data1, content_type='multipart/form-data', follow_redirects=True)
    assert resp1.status_code == 200

    # Upload exact duplicate
    data2 = {
        'document_type': 'submitted',
        'document_file': (io.BytesIO(content), 'hash_test_2.txt')
    }
    resp2 = client.post('/upload', data=data2, content_type='multipart/form-data', follow_redirects=True)
    assert resp2.status_code == 200
    assert b"Duplicate file notice" in resp2.data

    with app.app_context():
        doc2 = Document.query.filter_by(original_filename='hash_test_2.txt').first()
        assert doc2 is not None
        assert doc2.file_hash is not None
        assert len(doc2.file_hash) == 64  # SHA-256 hex string


def test_utf8_bom_and_unicode_text(client, app):
    """Verify that UTF-8 with BOM and non-ASCII characters (e.g. café, naïve, résumé) are extracted properly."""
    content = "\ufeffMachine learning models analyze résumé documents with café naïve Bayes algorithms.".encode('utf-8')
    data = {
        'document_type': 'submitted',
        'document_file': (io.BytesIO(content), 'unicode_sample.txt')
    }
    resp = client.post('/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        doc = Document.query.filter_by(original_filename='unicode_sample.txt').first()
        assert doc is not None
        assert "café" in doc.extracted_text or "cafe" in doc.extracted_text
        assert "résumé" in doc.extracted_text or "resume" in doc.extracted_text

