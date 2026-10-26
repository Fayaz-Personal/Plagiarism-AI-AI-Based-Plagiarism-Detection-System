"""
Optional Optical Character Recognition (OCR) Engine Module.
Provides graceful fallback for scanned image-based PDFs when OCR tools are not present.
"""
import shutil


def is_ocr_available() -> bool:
    """Check if an open-source OCR tool (such as Tesseract) is installed and accessible."""
    try:
        import pytesseract  # noqa: F401
        tesseract_bin = shutil.which('tesseract')
        return tesseract_bin is not None
    except ImportError:
        return False


def get_ocr_status() -> dict:
    """Return status and configuration details for OCR processing."""
    available = is_ocr_available()
    return {
        'available': available,
        'engine': 'Tesseract OCR' if available else 'None (Offline)',
        'description': (
            'Tesseract OCR engine is active and available for scanned document processing.'
            if available else
            'External OCR engine (Tesseract) is not detected in system PATH. Scanned image-based documents require OCR preprocessing.'
        )
    }


def extract_text_with_ocr(file_path: str) -> tuple[str, str | None]:
    """
    Attempt OCR extraction on a document.
    Returns: (extracted_text, error_message)
    """
    if not is_ocr_available():
        return "", (
            "OCR engine (Tesseract) is not installed or configured in the system environment. "
            "Please upload documents containing native digital text or install Tesseract OCR."
        )

    try:
        import pytesseract
        from pypdf import PdfReader
        # Placeholder for actual page-by-page rendering if pdf2image and tesseract are configured
        return "", "OCR processing requires pdf2image and Poppler to render PDF pages."
    except Exception as e:
        return "", f"OCR extraction failed: {str(e)}"
