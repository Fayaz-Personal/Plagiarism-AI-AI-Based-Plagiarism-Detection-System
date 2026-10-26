import pytest
from pathlib import Path
from extensions import db
from models.document_models import Document, Analysis
from plagiarism.document_processor import extract_text_from_pdf, extract_text_from_docx
from plagiarism.plagiarism_engine import (
    calculate_document_similarity,
    find_matching_sentences,
    analyze_document
)
from tests.conftest import create_sample_pdf, create_sample_docx


def test_4_extract_text_from_valid_pdf(test_dirs):
    """TEST 4: Extract text from a valid PDF."""
    pdf_path = Path(test_dirs['uploads']) / "sample_academic.pdf"
    expected_content = "Supervised machine learning algorithms identify complex patterns in data."
    create_sample_pdf(pdf_path, expected_content)

    text, is_scanned, page_count = extract_text_from_pdf(str(pdf_path))
    assert not is_scanned
    assert page_count >= 1
    assert "Supervised machine learning" in text


def test_5_extract_text_from_valid_docx(test_dirs):
    """TEST 5: Extract text from a valid DOCX document."""
    docx_path = Path(test_dirs['uploads']) / "sample_paper.docx"
    expected_content = "Neural networks utilize layered artificial neurons to compute representations."
    create_sample_docx(docx_path, expected_content)

    text, is_scanned, page_count = extract_text_from_docx(str(docx_path))
    assert not is_scanned
    assert page_count >= 1
    assert "Neural networks utilize layered artificial neurons" in text


def test_6_compare_identical_documents():
    """TEST 6: Compare identical documents and verify similarity is approximately 100%."""
    doc_text = """Deep learning architectures have revolutionized image processing and computer vision.
Convolutional neural networks extract hierarchical spatial representations from pixel arrays."""

    score = calculate_document_similarity(doc_text, doc_text)
    assert score >= 99.0


def test_7_compare_substantially_overlapping_documents():
    """TEST 7: Compare two documents with substantial overlapping text and verify high similarity."""
    doc_a = """Natural language processing facilitates machine understanding of human textual discourse.
Transformer architectures utilize self-attention mechanisms to process contextual representations.
Pretrained language models can be effectively fine-tuned for downstream question answering tasks."""

    doc_b = """Natural language processing facilitates machine understanding of human textual discourse.
Transformer architectures utilize self-attention mechanisms to process contextual representations.
Our experiments evaluated deep reinforcement learning in automated theorem proving."""

    score = calculate_document_similarity(doc_a, doc_b)
    # Substantial overlap should yield a high similarity score (typically > 50%)
    assert score >= 45.0


def test_8_compare_unrelated_documents():
    """TEST 8: Compare unrelated documents and verify similarity is lower than identical documents."""
    doc_ai = """Artificial neural networks model biological brain synaptic pathways for mathematical pattern recognition."""
    doc_cooking = """Baking artisan sourdough bread requires fermenting wild yeast cultures with hydration and flour."""

    score = calculate_document_similarity(doc_ai, doc_cooking)
    assert score < 20.0


def test_9_identify_matching_sentences():
    """TEST 9: Identify matching sentences between reference documents."""
    sub_text = "Gradient descent minimizes empirical risk through successive loss evaluations."
    ref_text = (
        "Relational databases enforce ACID transactions. "
        "Gradient descent minimizes empirical risk through successive loss evaluations. "
        "Photovoltaic cells convert photons into direct electrical current."
    )

    matches = find_matching_sentences(sub_text, ref_text, threshold=0.70)
    assert len(matches) >= 1
    assert matches[0]['similarity_score'] >= 0.70
    assert "Gradient descent minimizes" in matches[0]['submitted_sentence']


def test_10_handle_absence_of_reference_documents(app):
    """TEST 10: Handle the absence of reference documents gracefully without fabricating results."""
    with app.app_context():
        # Create a submitted document with NO reference documents in the system
        doc = Document(
            original_filename="alone_paper.txt",
            stored_filename="alone_paper.txt",
            file_type="txt",
            file_size=100,
            document_type="submitted",
            extracted_text="Academic paper written in complete isolation without reference documents.",
            word_count=10,
            sentence_count=1,
            is_active=True
        )
        db.session.add(doc)
        db.session.commit()

        analysis = analyze_document(doc.id)
        assert analysis.analysis_status == 'no_references'
        assert analysis.highest_similarity_score == 0.0
        assert analysis.references_compared == 0
        assert "No reference documents" in analysis.error_message


def test_14_deleting_reference_document_prevents_future_use(app):
    """TEST 14: Verify that deleting a reference document prevents it from being used in future analyses."""
    with app.app_context():
        # Create a reference document
        ref_doc = Document(
            original_filename="ref_biology.txt",
            stored_filename="ref_biology.txt",
            file_type="txt",
            file_size=200,
            document_type="reference",
            extracted_text="Mitochondria are the primary adenosine triphosphate energy producers in eukaryotic cells.",
            is_active=True
        )
        db.session.add(ref_doc)
        db.session.commit()

        # Create a submitted document
        sub_doc = Document(
            original_filename="sub_biology.txt",
            stored_filename="sub_biology.txt",
            file_type="txt",
            file_size=200,
            document_type="submitted",
            extracted_text="Mitochondria are the primary adenosine triphosphate energy producers in eukaryotic cells.",
            is_active=True
        )
        db.session.add(sub_doc)
        db.session.commit()

        # First analysis with reference present
        first_analysis = analyze_document(sub_doc.id)
        assert first_analysis.references_compared == 1
        assert first_analysis.highest_similarity_score >= 90.0

        # Now delete/deactivate the reference document
        ref_doc.is_active = False
        db.session.commit()

        # Second analysis should no longer include the deactivated reference document
        second_analysis = analyze_document(sub_doc.id)
        assert second_analysis.analysis_status == 'no_references'


def test_word_diff_highlighting():
    """Verify word-level diff produces correct inline HTML mark tags."""
    from plagiarism.preprocessing import highlight_diff_words

    sub_sent = "The artificial neural network learns latent representations from features."
    ref_sent = "The artificial neural network learns hierarchical representations from images."

    hl_sub, hl_ref, matched_words = highlight_diff_words(sub_sent, ref_sent)
    assert len(matched_words) > 0
    assert 'class="hl-match-sub"' in hl_sub
    assert 'class="hl-match-ref"' in hl_ref
    assert "artificial neural network" in hl_sub


def test_empty_vocabulary_handling():
    """Verify similarity calculation handles empty or non-alphanumeric vocabulary safely."""
    score1 = calculate_document_similarity("   ", "   ")
    assert score1 == 0.0

    score2 = calculate_document_similarity("... ??? !!!", "--- === +++")
    assert score2 == 0.0


def test_similarity_classification_bands(app):
    """Verify similarity classification categories match academic thresholds."""
    with app.app_context():
        # Low: < 10%
        assert Analysis.calculate_similarity_category(5.0) == 'Low'
        assert 'badge-low' in Analysis.calculate_badge_class(5.0)

        # Moderate: 10% to < 30%
        assert Analysis.calculate_similarity_category(22.5) == 'Moderate'
        assert 'badge-moderate' in Analysis.calculate_badge_class(22.5)

        # Elevated: 30% to < 60%
        assert Analysis.calculate_similarity_category(45.0) == 'Elevated'
        assert 'badge-elevated' in Analysis.calculate_badge_class(45.0)

        # High: >= 60%
        assert Analysis.calculate_similarity_category(85.0) == 'High'
        assert 'badge-high' in Analysis.calculate_badge_class(85.0)


def test_extension_engines_graceful_status():
    """Verify OCR and Semantic extension engines report status cleanly without throwing."""
    from plagiarism.ocr_engine import get_ocr_status, is_ocr_available
    from plagiarism.semantic_engine import get_semantic_status, is_semantic_available

    ocr_st = get_ocr_status()
    assert isinstance(ocr_st, dict)
    assert 'available' in ocr_st
    assert isinstance(is_ocr_available(), bool)

    sem_st = get_semantic_status()
    assert isinstance(sem_st, dict)
    assert 'available' in sem_st
    assert isinstance(is_semantic_available(), bool)
