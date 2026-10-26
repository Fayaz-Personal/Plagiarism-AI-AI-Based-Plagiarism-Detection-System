import os
from pathlib import Path
from extensions import db
from models.document_models import Document, Analysis, SimilarityResult, SentenceMatch
from plagiarism.report_generator import generate_pdf_report, generate_docx_report


def test_11_generate_and_download_pdf_report(app, client, test_dirs):
    """TEST 11: Generate and download a PDF report."""
    with app.app_context():
        # Setup document and analysis
        doc = Document(
            original_filename="sample_essay.txt",
            stored_filename="sample_essay.txt",
            file_type="txt",
            file_size=250,
            document_type="submitted",
            extracted_text="Machine learning transforms healthcare diagnostics.",
            is_active=True
        )
        db.session.add(doc)
        db.session.commit()

        analysis = Analysis(
            document_id=doc.id,
            highest_similarity_score=45.5,
            average_similarity_score=22.3,
            references_compared=2,
            matching_sentence_count=1,
            estimated_matching_text_coverage=33.3,
            analysis_status="completed"
        )
        db.session.add(analysis)
        db.session.flush()

        # Add a similarity result & match
        sim_res = SimilarityResult(
            analysis_id=analysis.id,
            reference_document_name="Ref_Diagnostics.txt",
            document_similarity_score=45.5,
            matching_sentence_count=1
        )
        db.session.add(sim_res)

        match = SentenceMatch(
            analysis_id=analysis.id,
            reference_document_name="Ref_Diagnostics.txt",
            submitted_sentence="Machine learning transforms healthcare diagnostics.",
            reference_sentence="Machine learning algorithms transform healthcare diagnostics and imaging.",
            similarity_score=0.88,
            submitted_sentence_index=0,
            reference_sentence_index=0
        )
        db.session.add(match)
        db.session.commit()
        analysis_id = analysis.id

    # Test PDF generation directly
    output_pdf = Path(test_dirs['reports']) / f"report_{analysis_id}.pdf"
    with app.app_context():
        gen_analysis = db.session.get(Analysis, analysis_id)
        generate_pdf_report(gen_analysis, str(output_pdf))

    assert output_pdf.is_file()
    assert os.path.getsize(output_pdf) > 1000

    with open(output_pdf, 'rb') as f:
        header = f.read(5)
        assert header == b'%PDF-'

    # Test download route via test client
    resp = client.get(f'/reports/{analysis_id}/pdf')
    assert resp.status_code == 200
    assert resp.content_type == 'application/pdf'
    assert resp.data.startswith(b'%PDF-')


def test_generate_and_download_docx_report(app, client, test_dirs):
    """Verify Word (.docx) report generation and download."""
    with app.app_context():
        doc = Document(
            original_filename="word_essay.docx",
            stored_filename="word_essay.docx",
            file_type="docx",
            file_size=300,
            document_type="submitted",
            extracted_text="Artificial intelligence ethics in autonomous transportation.",
            is_active=True
        )
        db.session.add(doc)
        db.session.commit()

        analysis = Analysis(
            document_id=doc.id,
            highest_similarity_score=15.0,
            average_similarity_score=15.0,
            references_compared=1,
            matching_sentence_count=0,
            estimated_matching_text_coverage=0.0,
            analysis_status="completed"
        )
        db.session.add(analysis)
        db.session.commit()
        analysis_id = analysis.id

    resp = client.get(f'/reports/{analysis_id}/docx')
    assert resp.status_code == 200
    assert 'officedocument.wordprocessingml' in resp.content_type
    assert len(resp.data) > 500


def test_report_with_unicode_and_many_matches(app, test_dirs):
    """Verify that reports containing unusual Unicode, math symbols, and multiple matches build without crashing."""
    with app.app_context():
        doc = Document(
            original_filename="unicode_symbols_paper.txt",
            stored_filename="unicode_symbols_paper.txt",
            file_type="txt",
            file_size=500,
            document_type="submitted",
            extracted_text="Testing mathematical symbols: α + β = γ — analysis of π ≈ 3.14159…",
            is_active=True
        )
        db.session.add(doc)
        db.session.commit()

        analysis = Analysis(
            document_id=doc.id,
            highest_similarity_score=82.4,
            average_similarity_score=50.2,
            references_compared=2,
            matching_sentence_count=2,
            estimated_matching_text_coverage=60.0,
            originality_score=17.6,
            analysis_status="completed"
        )
        db.session.add(analysis)
        db.session.flush()

        for i in range(2):
            m = SentenceMatch(
                analysis_id=analysis.id,
                reference_document_name=f"Ref_Source_{i}.txt",
                submitted_sentence=f"Special passage {i}: α = β² with em-dash — and quotes “example”.",
                reference_sentence=f"Reference text {i}: α = β² with em-dash — and quotes “example”.",
                similarity_score=0.92,
                submitted_sentence_index=i,
                reference_sentence_index=i,
                match_category="Exact Match",
                match_explanation="Verbatim character sequence detected."
            )
            db.session.add(m)
        db.session.commit()
        analysis_id = analysis.id

        output_pdf = Path(test_dirs['reports']) / f"unicode_report_{analysis_id}.pdf"
        output_docx = Path(test_dirs['reports']) / f"unicode_report_{analysis_id}.docx"

        gen_analysis = db.session.get(Analysis, analysis_id)
        generate_pdf_report(gen_analysis, str(output_pdf))
        generate_docx_report(gen_analysis, str(output_docx))

        assert output_pdf.is_file()
        assert output_docx.is_file()

