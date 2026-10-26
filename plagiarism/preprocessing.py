import re
import html
import difflib
import unicodedata


# Common abbreviations that should not trigger sentence boundaries
ABBREVIATIONS = (
    r'\b(?:e\.g|i\.e|etc|vs|dr|mr|mrs|ms|prof|fig|vol|no|dept|univ|al|et al)\.'
)


def normalize_text(text: str) -> str:
    """
    Unicode normalization (NFKC), whitespace cleaning, and character standardization.
    Preserves case and punctuation for accurate reporting.
    """
    if not text:
        return ""

    # Unicode normalization
    text = unicodedata.normalize('NFKC', text)

    # Standardize curved quotes, dashes, and apostrophes
    text = re.sub(r'[\u2018\u2019\u201A\u201B]', "'", text)
    text = re.sub(r'[\u201C\u201D\u201E\u201F]', '"', text)
    text = re.sub(r'[\u2013\u2014]', '-', text)

    # Normalize excessive newlines and whitespace
    text = re.sub(r'\r\n|\r', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def segment_sentences(text: str, min_length: int = 20) -> list[str]:
    """
    Segments normalized text into meaningful sentences.
    Respects common abbreviations and filters out very short fragments.
    """
    if not text:
        return []

    normalized = normalize_text(text)

    # Temporarily mask periods in common abbreviations
    def mask_abbrev(match):
        return match.group(0).replace('.', '@DOT@')

    masked_text = re.sub(ABBREVIATIONS, mask_abbrev, normalized, flags=re.IGNORECASE)

    # Split on sentence ending punctuation followed by whitespace or end of string
    raw_sentences = re.split(r'(?<=[.!?])\s+', masked_text)

    sentences = []
    for s in raw_sentences:
        # Restore masked periods
        unmasked = s.replace('@DOT@', '.').strip()
        # Collapse internal whitespace
        unmasked = re.sub(r'\s+', ' ', unmasked)

        # Filter sentences by minimum character length and meaningful word count
        if len(unmasked) >= min_length and len(unmasked.split()) >= 3:
            sentences.append(unmasked)

    return sentences


def clean_for_vectorization(text: str) -> str:
    """
    Preprocesses text specifically for TF-IDF feature extraction.
    Lowercases, cleans non-alphanumeric characters while keeping alphanumeric words.
    """
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def highlight_diff_words(submitted_sentence: str, reference_sentence: str) -> tuple[str, str, list[str]]:
    """
    Highlights common word sequences between submitted and reference sentences using difflib.
    Returns: (highlighted_submitted_html, highlighted_reference_html, list_of_matching_words)
    """
    sub_words = re.findall(r'\b[\w-]+\b|[^\w\s]', submitted_sentence)
    ref_words = re.findall(r'\b[\w-]+\b|[^\w\s]', reference_sentence)

    sub_lower = [w.lower() for w in sub_words]
    ref_lower = [w.lower() for w in ref_words]

    matcher = difflib.SequenceMatcher(None, sub_lower, ref_lower)
    matching_blocks = matcher.get_matching_blocks()

    sub_marked = [False] * len(sub_words)
    ref_marked = [False] * len(ref_words)
    matched_words = []

    for block in matching_blocks:
        if block.size > 0:
            for k in range(block.size):
                sub_idx = block.a + k
                ref_idx = block.b + k
                # Ignore isolated punctuation matches
                if re.match(r'^\w', sub_words[sub_idx]):
                    sub_marked[sub_idx] = True
                    ref_marked[ref_idx] = True
                    matched_words.append(sub_words[sub_idx])

    def render_highlighted(tokens, marked, mark_class):
        res = []
        in_mark = False
        for i, token in enumerate(tokens):
            safe_tok = html.escape(token)
            prefix = " " if i > 0 and re.match(r'^\w', token) else ""
            if marked[i]:
                if not in_mark:
                    res.append(f'{prefix}<mark class="{mark_class}">{safe_tok}')
                    in_mark = True
                else:
                    res.append(f'{prefix}{safe_tok}')
            else:
                if in_mark:
                    res.append('</mark>')
                    in_mark = False
                res.append(f'{prefix}{safe_tok}')
        if in_mark:
            res.append('</mark>')
        return "".join(res)

    hl_sub = render_highlighted(sub_words, sub_marked, "hl-match-sub")
    hl_ref = render_highlighted(ref_words, ref_marked, "hl-match-ref")

    return hl_sub, hl_ref, list(set(matched_words))
