import json
from datetime import datetime, timezone
from extensions import db


def utc_now():
    return datetime.now(timezone.utc)


class Document(db.Model):
    """Uploaded document representation (either a document to analyze or a reference document)."""
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False, unique=True)
    file_type = db.Column(db.String(10), nullable=False)  # 'pdf', 'docx', 'txt'
    file_size = db.Column(db.Integer, nullable=False)  # size in bytes
    file_hash = db.Column(db.String(64), nullable=True, index=True)  # SHA-256 hash for duplicate detection
    page_count = db.Column(db.Integer, default=1)  # Extracted page count
    document_type = db.Column(db.String(20), nullable=False, default='submitted')  # 'submitted' or 'reference'
    extracted_text = db.Column(db.Text, nullable=True)
    word_count = db.Column(db.Integer, default=0)
    sentence_count = db.Column(db.Integer, default=0)
    upload_date = db.Column(db.DateTime, default=utc_now, nullable=False)
    processing_status = db.Column(db.String(30), default='processed')  # 'processed', 'empty', 'failed'
    is_active = db.Column(db.Boolean, default=True, nullable=False)  # Active for comparisons

    # Relationships
    analyses = db.relationship('Analysis', back_populates='document', cascade='all, delete-orphan')
    reference_results = db.relationship(
        'SimilarityResult',
        back_populates='reference_document',
        foreign_keys='SimilarityResult.reference_document_id'
    )
    sentence_matches = db.relationship(
        'SentenceMatch',
        back_populates='reference_document',
        foreign_keys='SentenceMatch.reference_document_id'
    )

    def __repr__(self):
        return f"<Document {self.id}: {self.original_filename} ({self.document_type})>"

    @property
    def formatted_size(self):
        """Human-readable file size."""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} GB"


class Analysis(db.Model):
    """Analysis result record for a submitted document."""
    __tablename__ = 'analyses'

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    analysis_date = db.Column(db.DateTime, default=utc_now, nullable=False)
    highest_similarity_score = db.Column(db.Float, default=0.0)  # 0.0 - 100.0%
    average_similarity_score = db.Column(db.Float, default=0.0)  # 0.0 - 100.0%
    references_compared = db.Column(db.Integer, default=0)
    matching_sentence_count = db.Column(db.Integer, default=0)
    estimated_matching_text_coverage = db.Column(db.Float, default=0.0)  # 0.0 - 100.0%
    originality_score = db.Column(db.Float, default=100.0)  # 100.0 - highest_similarity_score
    analysis_status = db.Column(db.String(30), default='completed')  # 'completed', 'no_references', 'failed'
    error_message = db.Column(db.Text, nullable=True)

    # Relationships
    document = db.relationship('Document', back_populates='analyses')
    similarity_results = db.relationship('SimilarityResult', back_populates='analysis', cascade='all, delete-orphan')
    sentence_matches = db.relationship('SentenceMatch', back_populates='analysis', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Analysis {self.id} for Doc {self.document_id}: {self.highest_similarity_score:.1f}%>"

    @staticmethod
    def calculate_similarity_category(score: float) -> str:
        """Returns standard academic textual resemblance classification band."""
        if score < 10.0:
            return 'Low'
        elif score < 30.0:
            return 'Moderate'
        elif score < 60.0:
            return 'Elevated'
        else:
            return 'High'

    @staticmethod
    def calculate_badge_class(score: float) -> str:
        """CSS badge class based on similarity score."""
        category = Analysis.calculate_similarity_category(score)
        mapping = {
            'Low': 'badge-success badge-low',
            'Moderate': 'badge-info badge-moderate',
            'Elevated': 'badge-warning badge-elevated',
            'High': 'badge-danger badge-high'
        }
        return mapping.get(category, 'badge-secondary')

    @property
    def similarity_category(self):
        """Returns standard academic textual resemblance classification band."""
        return Analysis.calculate_similarity_category(self.highest_similarity_score)

    @property
    def badge_color_class(self):
        """CSS badge class based on similarity score."""
        return Analysis.calculate_badge_class(self.highest_similarity_score)


class SimilarityResult(db.Model):
    """Pairwise document similarity result between submitted doc and one reference doc."""
    __tablename__ = 'similarity_results'

    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey('analyses.id', ondelete='CASCADE'), nullable=False)
    reference_document_id = db.Column(db.Integer, db.ForeignKey('documents.id', ondelete='SET NULL'), nullable=True)
    reference_document_name = db.Column(db.String(255), nullable=False)  # Preserved even if reference doc is deleted
    document_similarity_score = db.Column(db.Float, nullable=False, default=0.0)  # 0.0 - 100.0%
    matching_sentence_count = db.Column(db.Integer, nullable=False, default=0)
    result_metadata = db.Column(db.Text, nullable=True)  # JSON-encoded extra details

    # Relationships
    analysis = db.relationship('Analysis', back_populates='similarity_results')
    reference_document = db.relationship(
        'Document',
        back_populates='reference_results',
        foreign_keys=[reference_document_id]
    )

    def __repr__(self):
        return f"<SimilarityResult Analysis {self.analysis_id} vs Ref {self.reference_document_name}: {self.document_similarity_score:.1f}%>"


class SentenceMatch(db.Model):
    """Granular sentence-level match details."""
    __tablename__ = 'sentence_matches'

    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey('analyses.id', ondelete='CASCADE'), nullable=False)
    reference_document_id = db.Column(db.Integer, db.ForeignKey('documents.id', ondelete='SET NULL'), nullable=True)
    reference_document_name = db.Column(db.String(255), nullable=False)
    submitted_sentence = db.Column(db.Text, nullable=False)
    reference_sentence = db.Column(db.Text, nullable=False)
    similarity_score = db.Column(db.Float, nullable=False)  # Cosine similarity (0.0 - 1.0 or 0 - 100%)
    match_category = db.Column(db.String(50), default='Moderate Match')  # 'Exact Match', 'Strong Match', 'Moderate Match'
    match_explanation = db.Column(db.String(255), nullable=True)
    overlapping_words = db.Column(db.Text, nullable=True)  # JSON list of overlapping words
    submitted_sentence_index = db.Column(db.Integer, default=0)
    reference_sentence_index = db.Column(db.Integer, default=0)

    # Relationships
    analysis = db.relationship('Analysis', back_populates='sentence_matches')
    reference_document = db.relationship(
        'Document',
        back_populates='sentence_matches',
        foreign_keys=[reference_document_id]
    )

    def __repr__(self):
        return f"<SentenceMatch {self.id} ({self.similarity_score:.2f})>"

    @property
    def percentage_score(self):
        return self.similarity_score * 100.0 if self.similarity_score <= 1.0 else self.similarity_score


class Setting(db.Model):
    """Key-value application settings."""
    __tablename__ = 'settings'

    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<Setting {self.key}={self.value}>"
