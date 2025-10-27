import re
import pandas as pd
from itertools import islice


URL_RE = re.compile(r"http\S+|www\S+|https\S+")
EMAIL_RE = re.compile(r"\S+@\S+")
HTML_RE = re.compile(r"<.*?>")
EMOJI_RE = re.compile(r"[^\x00-\x7F]+")
MULTISPACE_RE = re.compile(r"\s+")


STOPWORDS = set([
    # Articles / Determiners
    "a", "an", "the", "this", "that", "these", "those",

    # Conjunctions
    "and", "or", "but", "so", "because", "as", "if", "while", "though", "although",

    # Prepositions
    "in", "on", "at", "to", "from", "for", "of", "with", "by", "about", "against",
    "between", "into", "through", "during", "before", "after", "above", "below",
    "under", "over", "around", "near",

    # Pronouns
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves",
    "you", "your", "yours", "yourself", "yourselves",
    "he", "him", "his", "himself", "she", "her", "hers", "herself",
    "it", "its", "itself", "they", "them", "their", "theirs", "themselves",

    # Auxiliary & linking verbs
    "am", "is", "are", "was", "were", "be", "been", "being", "do", "does", "did",
    "doing", "have", "has", "had", "having", "can", "could", "shall", "should",
    "will", "would", "may", "might", "must",

    # Question / filler words
    "what", "which", "who", "whom", "whose", "where", "when", "why", "how",

    # Others (common short fillers)
    "there", "then", "than", "too", "very", "just", "not", "no", "nor", "only",
    "own", "same", "such", "s", "t", "re", "ll", "d", "m", "ve", 

    "podcast", "podcasts"
])


def clean_text(text):
    text = URL_RE.sub(" ", str(text))
    text = EMAIL_RE.sub(" ", text)
    text = HTML_RE.sub(" ", text)
    text = EMOJI_RE.sub(" ", text)
    text = MULTISPACE_RE.sub(" ", text)
    return text.strip()


def get_words_from_column(row, column_name):
    """Extract words from a CSV column, handling both string and list formats"""
    value = row.get(column_name) if isinstance(row, dict) else row[column_name]
    if not value or (isinstance(value, float) and pd.isna(value)):
        return []
    
    # Handle string format - check if it's a malformed list string
    if isinstance(value, str):
        # Check if it looks like a malformed list (e.g., "['word1'", "'word2'", ...])
        if value.startswith('[') or "'" in value:
            # Try to parse as a malformed list
            # Remove outer brackets if present
            if value.startswith('[') and value.endswith(']'):
                value = value[1:-1]
            
            # Split by comma and clean each part
            parts = value.split(',')
            clean_words = []
            for part in parts:
                # Remove quotes, brackets, and whitespace
                clean_part = part.strip().strip("'\"[]")
                clean_part = clean_part.replace("'", "").replace('"', "").replace("[", "").replace("]", "")
                clean_part = clean_part.strip()
                if clean_part:
                    clean_words.append(clean_part)
            return clean_words
        else:
            # Regular comma or space separated string
            if ',' in value:
                words = [w.strip() for w in value.split(',') if w.strip()]
            else:
                words = [w.strip() for w in value.split() if w.strip()]
            return words
    
    # Handle list format - clean each item
    if isinstance(value, list):
        clean_words = []
        for item in value:
            if item and str(item).strip():
                # Remove any quotes, brackets, or extra whitespace
                clean_item = str(item).strip().strip("'\"[]")
                # Additional cleaning for any remaining formatting
                clean_item = clean_item.replace("'", "").replace('"', "").replace("[", "").replace("]", "")
                if clean_item and clean_item.strip():
                    clean_words.append(clean_item.strip())
        return clean_words
    
    return []


def clean_word_for_planner(word):
    """Clean a word for keyword planner display"""
    if not word:
        return ""
    # Convert to string and remove any brackets, quotes
    clean_word = str(word).strip().strip("'\"[]")
    clean_word = clean_word.replace("'", "").replace('"', "").replace("[", "").replace("]", "")
    # Remove any extra whitespace
    clean_word = " ".join(clean_word.split())
    return clean_word.strip()


def create_podcast_variations(words):
    """Create podcast variations for a list of words"""
    variations = []
    for word in words:
        variations.append(f"{word} podcast")
        variations.append(f"{word} podcasts")
    return variations


def generate_keyword_planner_text(words):
    """Generate clean keyword planner text from words"""
    # Clean each word
    clean_words = []
    for word in words:
        cleaned = clean_word_for_planner(word)
        if cleaned:
            clean_words.append(cleaned)
    
    # Generate text
    text = ", ".join([f"{word} podcast, {word} podcasts" for word in clean_words])
    
    # Final cleaning to remove any extra spaces
    text = " ".join(text.split())
    text = text.strip()
    
    return text


def process_episode_data(row):
    """Process episode data and return all necessary variables"""
    # Get words from each column
    one_word = get_words_from_column(row, "Important Words 1")
    two_word = get_words_from_column(row, "Important Words 2") 
    three_word = get_words_from_column(row, "Important Words 3")
    general_words = get_words_from_column(row, "Important Words")
    
    # Create podcast variations
    one_word_podcasts = create_podcast_variations(one_word)
    two_word_podcasts = create_podcast_variations(two_word)
    three_word_podcasts = create_podcast_variations(three_word)
    
    # Generate keyword planner text
    one_word_text = generate_keyword_planner_text(one_word)
    two_word_text = generate_keyword_planner_text(two_word)
    three_word_text = generate_keyword_planner_text(three_word)
    
    return {
        'one_word': one_word,
        'two_word': two_word,
        'three_word': three_word,
        'general_words': general_words,
        'one_word_podcasts': one_word_podcasts,
        'two_word_podcasts': two_word_podcasts,
        'three_word_podcasts': three_word_podcasts,
        'one_word_text': one_word_text,
        'two_word_text': two_word_text,
        'three_word_text': three_word_text
    }


def validate_csv_columns(df):
    """Validate that CSV has required columns"""
    if "Title" not in df.columns or "Description" not in df.columns:
        return False, "CSV must contain columns: Title, Description"
    return True, None


def add_tracking_columns(df):
    """Add tracking columns if missing"""
    existing_cols = set(df.columns)
    required_defaults = {
        "Analyzed": False,
        "No of Queries": 0,
        "Added Queries": ""
    }
    # Only add the tracking columns if missing
    for col, default_val in required_defaults.items():
        if col not in existing_cols:
            df[col] = default_val
    return df


def get_display_dataframe(df):
    """Get display dataframe with only specific columns for home page"""
    display_columns = ["Title", "Description", "Analyzed", "No of Queries", "Added Queries"]
    return df[display_columns].copy()


def update_query_list(existing_raw, query, add=True):
    """Update query list by adding or removing a query"""
    # Coerce NaN / non-string to safe string
    if isinstance(existing_raw, float) and pd.isna(existing_raw):
        existing_raw = ""
    if not isinstance(existing_raw, str):
        existing_raw = str(existing_raw) if existing_raw is not None else ""

    items = [q for q in (s.strip() for s in existing_raw.split(",")) if q]
    
    if add:
        if query not in items:
            items.append(query)
    else:
        items = [q for q in items if q != query]
    
    return items


def generate_download_filename(uploaded_filename, df):
    """Generate descriptive filename for download"""
    true_count = df["Analyzed"].sum() if "Analyzed" in df.columns else 0
    false_count = len(df) - true_count
    
    # Remove any existing "_<num>_rows_processed_<num>_pending" pattern
    base_name = uploaded_filename.rsplit(".", 1)[0]
    base_name = re.sub(r"_\d+_rows_processed_\d+_rows_pending$", "", base_name)
    
    # Create new descriptive name
    return f"{base_name}_{true_count}_rows_processed_{false_count}_rows_pending.csv"




