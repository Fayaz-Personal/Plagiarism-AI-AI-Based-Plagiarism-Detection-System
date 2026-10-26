from plagiarism.preprocessing import normalize_text, segment_sentences, highlight_diff_words
from plagiarism.document_processor import (
    extract_text,
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_txt,
    compute_file_hash,
    generate_safe_filename
)
from plagiarism.plagiarism_engine import analyze_document, calculate_document_similarity, find_matching_sentences
from plagiarism.ocr_engine import is_ocr_available, get_ocr_status
from plagiarism.semantic_engine import is_semantic_available, get_semantic_status

__all__ = [
    'normalize_text',
    'segment_sentences',
    'highlight_diff_words',
    'extract_text',
    'extract_text_from_pdf',
    'extract_text_from_docx',
    'extract_text_from_txt',
    'compute_file_hash',
    'generate_safe_filename',
    'analyze_document',
    'calculate_document_similarity',
    'find_matching_sentences',
    'is_ocr_available',
    'get_ocr_status',
    'is_semantic_available',
    'get_semantic_status'
]
