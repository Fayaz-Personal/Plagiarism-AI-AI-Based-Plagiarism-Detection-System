import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from extensions import db
from models.document_models import Document, Analysis, SimilarityResult, SentenceMatch, Setting
from plagiarism.preprocessing import (
    normalize_text,
    segment_sentences,
    clean_for_vectorization,
    highlight_diff_words
)


def get_engine_setting(key: str, default: float | int) -> float | int:
    """Retrieve runtime configurable setting from DB, falling back to default."""
    try:
        setting = Setting.query.filter_by(key=key).first()
        if setting and setting.value:
            if isinstance(default, float):
                return float(setting.value)
            elif isinstance(default, int):
                return int(setting.value)
            return setting.value
    except Exception:
        pass
    return default


def preprocess_text(text: str) -> str:
    """Applies normalization and cleaning to text."""
    return normalize_text(text)


def create_vectorizer():
    """Builds a configured scikit-learn TfidfVectorizer."""
    return TfidfVectorizer(
        ngram_range=(1, 2),
        stop_words='english',
        sublinear_tf=True,
        token_pattern=r'(?u)\b\w+\b',
        max_features=10000
    )


def calculate_document_similarity(text_a: str, text_b: str) -> float:
    """
    Calculates cosine similarity between two documents using TF-IDF representation.
    Returns: similarity score as a percentage between 0.0 and 100.0.
    """
    clean_a = clean_for_vectorization(text_a)
    clean_b = clean_for_vectorization(text_b)

    if not clean_a or not clean_b:
        return 0.0

    # Exact identical text check (ignoring trivial whitespace)
    if clean_a == clean_b:
        return 100.0

    vectorizer = create_vectorizer()
    try:
        tfidf_matrix = vectorizer.fit_transform([clean_a, clean_b])
    except ValueError:
        # Fallback without stop words if vocab is empty
        fallback_vec = TfidfVectorizer(ngram_range=(1, 2), token_pattern=r'(?u)\b\w+\b')
        try:
            tfidf_matrix = fallback_vec.fit_transform([clean_a, clean_b])
        except ValueError:
            return 0.0

    sim_score = float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0])
    return round(max(0.0, min(100.0, sim_score * 100.0)), 2)


def compare_with_reference_documents(submitted_text: str, references: list[dict]) -> list[dict]:
    """
    Compares submitted text against multiple reference documents in a shared TF-IDF feature space.
    references: [{'id': doc.id, 'name': doc.original_filename, 'text': doc.extracted_text}, ...]
    Returns list of similarity result dictionaries.
    """
    if not references or not submitted_text.strip():
        return []

    clean_submitted = clean_for_vectorization(submitted_text)
    clean_refs = [clean_for_vectorization(r['text']) for r in references]

    corpus = [clean_submitted] + clean_refs

    vectorizer = create_vectorizer()
    try:
        tfidf_matrix = vectorizer.fit_transform(corpus)
    except ValueError:
        # Fallback if vocabulary is small or affected by stop words
        fallback_vec = TfidfVectorizer(ngram_range=(1, 2), token_pattern=r'(?u)\b\w+\b')
        try:
            tfidf_matrix = fallback_vec.fit_transform(corpus)
        except ValueError:
            return [{'reference_id': r['id'], 'reference_name': r['name'], 'document_similarity_score': 0.0} for r in references]

    # Compute similarity between submitted doc (row 0) and each reference (rows 1..N)
    submitted_vec = tfidf_matrix[0:1]
    results = []

    for idx, ref in enumerate(references):
        ref_vec = tfidf_matrix[idx + 1:idx + 2]
        sim_val = float(cosine_similarity(submitted_vec, ref_vec)[0][0])
        sim_score = round(max(0.0, min(100.0, sim_val * 100.0)), 2)

        results.append({
            'reference_id': ref['id'],
            'reference_name': ref['name'],
            'document_similarity_score': sim_score
        })

    return results


def classify_match(score: float) -> tuple[str, str]:
    """Assigns category label and explanation to sentence match."""
    if score >= 0.95:
        return 'Exact Match', 'Verbatim or near-identical text segment matching reference source.'
    elif score >= 0.80:
        return 'Strong Match', 'Substantial lexical alignment and identical phrasing with minor word variations.'
    else:
        return 'Moderate Match', 'Noticeable sentence-level textual resemblance and shared technical terminology.'


def find_matching_sentences(
    submitted_text: str,
    reference_text: str,
    threshold: float = 0.70,
    min_length: int = 20
) -> list[dict]:
    """
    Identifies sentence-level matches between submitted text and reference text.
    Uses TF-IDF vectorization and cosine similarity.
    """
    submitted_sentences = segment_sentences(submitted_text, min_length=min_length)
    reference_sentences = segment_sentences(reference_text, min_length=min_length)

    if not submitted_sentences or not reference_sentences:
        return []

    # Clean sentences for vectorization
    clean_sub_sents = [clean_for_vectorization(s) for s in submitted_sentences]
    clean_ref_sents = [clean_for_vectorization(s) for s in reference_sentences]

    # Filter out sentences that have no alphanumeric content after cleaning
    valid_sub_indices = [i for i, s in enumerate(clean_sub_sents) if s]
    valid_ref_indices = [j for j, s in enumerate(clean_ref_sents) if s]

    if not valid_sub_indices or not valid_ref_indices:
        return []

    corpus = [clean_sub_sents[i] for i in valid_sub_indices] + [clean_ref_sents[j] for j in valid_ref_indices]

    vec = TfidfVectorizer(ngram_range=(1, 2), stop_words='english', token_pattern=r'(?u)\b\w+\b')
    try:
        matrix = vec.fit_transform(corpus)
    except ValueError:
        vec = TfidfVectorizer(ngram_range=(1, 1), token_pattern=r'(?u)\b\w+\b')
        try:
            matrix = vec.fit_transform(corpus)
        except ValueError:
            return []

    n_sub = len(valid_sub_indices)
    sub_matrix = matrix[:n_sub]
    ref_matrix = matrix[n_sub:]

    sim_matrix = cosine_similarity(sub_matrix, ref_matrix)

    matches = []
    seen_pairs = set()

    for i_sub_pos, i_original in enumerate(valid_sub_indices):
        best_ref_match = None
        best_score = 0.0
        best_j_original = -1

        for j_ref_pos, j_original in enumerate(valid_ref_indices):
            score = float(sim_matrix[i_sub_pos, j_ref_pos])
            if score >= threshold and score > best_score:
                best_score = score
                best_ref_match = reference_sentences[j_original]
                best_j_original = j_original

        if best_ref_match:
            sub_sent = submitted_sentences[i_original]
            pair_key = (sub_sent, best_ref_match)
            if pair_key not in seen_pairs:
                seen_pairs.add(pair_key)
                category, explanation = classify_match(best_score)
                _, _, matching_words = highlight_diff_words(sub_sent, best_ref_match)

                matches.append({
                    'submitted_sentence': sub_sent,
                    'reference_sentence': best_ref_match,
                    'similarity_score': round(best_score, 4),
                    'match_category': category,
                    'match_explanation': explanation,
                    'overlapping_words': json.dumps(matching_words),
                    'submitted_sentence_index': i_original,
                    'reference_sentence_index': best_j_original
                })

    return matches


def calculate_similarity_statistics(
    pairwise_results: list[dict],
    submitted_sentences: list[str],
    all_sentence_matches: list[dict]
) -> dict:
    """
    Aggregates overall similarity metrics.
    Calculates highest similarity, average similarity, text coverage, and originality indicator.
    Coverage Formula: (character length of unique matched submitted sentences / total submitted text characters) * 100
    Originality Formula: max(0.0, 100.0 - highest_similarity_score)
    """
    if not pairwise_results:
        return {
            'highest_similarity_score': 0.0,
            'average_similarity_score': 0.0,
            'references_compared': 0,
            'matching_sentence_count': 0,
            'estimated_matching_text_coverage': 0.0,
            'originality_score': 100.0
        }

    scores = [r['document_similarity_score'] for r in pairwise_results]
    highest_score = max(scores) if scores else 0.0
    avg_score = sum(scores) / len(scores) if scores else 0.0

    # Calculate coverage
    total_chars = sum(len(s) for s in submitted_sentences) if submitted_sentences else 0
    unique_matched_texts = set(m['submitted_sentence'] for m in all_sentence_matches)
    matched_chars = sum(len(s) for s in unique_matched_texts)

    coverage = (matched_chars / total_chars * 100.0) if total_chars > 0 else 0.0
    coverage = round(min(100.0, max(0.0, coverage)), 2)
    originality = round(max(0.0, 100.0 - highest_score), 2)

    return {
        'highest_similarity_score': round(highest_score, 2),
        'average_similarity_score': round(avg_score, 2),
        'references_compared': len(pairwise_results),
        'matching_sentence_count': len(all_sentence_matches),
        'estimated_matching_text_coverage': coverage,
        'originality_score': originality
    }


def analyze_document(submitted_document_id: int) -> Analysis:
    """
    Main orchestration function to analyze a submitted document against all active reference documents.
    """
    doc = db.session.get(Document, submitted_document_id)
    if not doc:
        raise ValueError(f"Document with ID {submitted_document_id} does not exist.")

    if not doc.extracted_text or not doc.extracted_text.strip():
        # Document has no text
        analysis = Analysis(
            document_id=doc.id,
            highest_similarity_score=0.0,
            average_similarity_score=0.0,
            references_compared=0,
            matching_sentence_count=0,
            estimated_matching_text_coverage=0.0,
            originality_score=100.0,
            analysis_status='failed',
            error_message="The submitted document contains no extractable text. Please upload a readable document."
        )
        db.session.add(analysis)
        db.session.commit()
        return analysis

    # Query active reference documents
    reference_docs = Document.query.filter_by(
        document_type='reference',
        is_active=True
    ).all()

    # Filter references that have actual extracted text
    valid_references = [r for r in reference_docs if r.extracted_text and r.extracted_text.strip()]

    if not valid_references:
        # No reference documents exist in the library
        analysis = Analysis(
            document_id=doc.id,
            highest_similarity_score=0.0,
            average_similarity_score=0.0,
            references_compared=0,
            matching_sentence_count=0,
            estimated_matching_text_coverage=0.0,
            originality_score=100.0,
            analysis_status='no_references',
            error_message="No reference documents are currently available in the document library. Please upload reference documents to enable comparison."
        )
        db.session.add(analysis)
        db.session.commit()
        return analysis

    # Load runtime configurable thresholds
    sentence_threshold = get_engine_setting('SENTENCE_SIMILARITY_THRESHOLD', 0.70)
    min_length = int(get_engine_setting('MIN_SENTENCE_LENGTH', 20))

    # Prepare reference payloads
    ref_payloads = [
        {'id': r.id, 'name': r.original_filename, 'text': r.extracted_text}
        for r in valid_references
    ]

    # 1. Document-level TF-IDF Cosine Similarity
    pairwise_results = compare_with_reference_documents(doc.extracted_text, ref_payloads)

    # 2. Sentence-level matching across each reference document
    submitted_sentences = segment_sentences(doc.extracted_text, min_length=min_length)
    all_sentence_matches = []
    matches_per_reference = {}

    for ref in valid_references:
        ref_matches = find_matching_sentences(
            submitted_text=doc.extracted_text,
            reference_text=ref.extracted_text,
            threshold=sentence_threshold,
            min_length=min_length
        )
        matches_per_reference[ref.id] = ref_matches
        for m in ref_matches:
            all_sentence_matches.append({
                **m,
                'reference_document_id': ref.id,
                'reference_document_name': ref.original_filename
            })

    # 3. Calculate aggregate statistics
    stats = calculate_similarity_statistics(
        pairwise_results=pairwise_results,
        submitted_sentences=submitted_sentences,
        all_sentence_matches=all_sentence_matches
    )

    # 4. Save Analysis record
    analysis = Analysis(
        document_id=doc.id,
        highest_similarity_score=stats['highest_similarity_score'],
        average_similarity_score=stats['average_similarity_score'],
        references_compared=stats['references_compared'],
        matching_sentence_count=stats['matching_sentence_count'],
        estimated_matching_text_coverage=stats['estimated_matching_text_coverage'],
        originality_score=stats['originality_score'],
        analysis_status='completed',
        error_message=None
    )
    db.session.add(analysis)
    db.session.flush()  # generates analysis.id

    # 5. Save Pairwise Similarity Results
    for p_res in pairwise_results:
        ref_id = p_res['reference_id']
        match_count = len(matches_per_reference.get(ref_id, []))
        sim_res = SimilarityResult(
            analysis_id=analysis.id,
            reference_document_id=ref_id,
            reference_document_name=p_res['reference_name'],
            document_similarity_score=p_res['document_similarity_score'],
            matching_sentence_count=match_count,
            result_metadata=json.dumps({'match_count': match_count})
        )
        db.session.add(sim_res)

    # 6. Save Sentence Matches
    for m in all_sentence_matches:
        s_match = SentenceMatch(
            analysis_id=analysis.id,
            reference_document_id=m['reference_document_id'],
            reference_document_name=m['reference_document_name'],
            submitted_sentence=m['submitted_sentence'],
            reference_sentence=m['reference_sentence'],
            similarity_score=m['similarity_score'],
            match_category=m.get('match_category', 'Moderate Match'),
            match_explanation=m.get('match_explanation', 'Textual overlap detected.'),
            overlapping_words=m.get('overlapping_words'),
            submitted_sentence_index=m['submitted_sentence_index'],
            reference_sentence_index=m['reference_sentence_index']
        )
        db.session.add(s_match)

    db.session.commit()
    return analysis
