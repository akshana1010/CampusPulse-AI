"""
CampusPulse AI – Duplicate Report Detection Service
Uses a lightweight TF-IDF + Cosine Similarity text comparison and geographic/building proximity checks.
Zero external heavy dependencies.
"""

import re
import math
from collections import Counter
from app.models import Report
from app.utils.campus_data import get_building_by_id, get_building_by_name

# Standard English stopwords
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
    "hasn't", "have", "haven't", "having", "he", "her", "here", "hers", "herself",
    "him", "himself", "his", "how", "i", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
    "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't",
    "she", "should", "shouldn't", "so", "some", "such", "than", "that", "the",
    "their", "theirs", "them", "themselves", "then", "there", "these", "they",
    "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "wasn't", "we", "were", "weren't", "what", "when", "where", "which", "while",
    "who", "whom", "why", "with", "won't", "would", "wouldn't", "you", "your",
    "yours", "yourself", "yourselves", "please", "also", "there", "here"
}

def clean_word(word: str) -> str:
    """Basic stemming/normalizing for common English suffixes."""
    w = word.lower().strip("_-.,!?:;\"'()[]{}")
    if len(w) > 4:
        if w.endswith("ing"):
            w = w[:-3]
        elif w.endswith("ed"):
            w = w[:-2]
        elif w.endswith("es"):
            w = w[:-2]
        elif w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
    return w

def tokenize(text: str) -> list[str]:
    """Tokenize and filter text into normalized lowercase words."""
    if not text:
        return []
    raw_words = re.findall(r'\b[a-zA-Z0-9_-]+\b', text.lower())
    tokens = []
    for raw in raw_words:
        w = clean_word(raw)
        if w and w not in STOPWORDS and len(w) > 1:
            tokens.append(w)
    return tokens

def compute_cosine_similarity(text1: str, text2: str) -> float:
    """
    Compute text similarity combining TF-IDF cosine similarity and token overlap.
    Returns float between 0.0 and 1.0.
    """
    tokens1 = tokenize(text1)
    tokens2 = tokenize(text2)
    
    if not tokens1 or not tokens2:
        return 0.0

    tf1 = Counter(tokens1)
    tf2 = Counter(tokens2)
    
    all_terms = set(tf1.keys()).union(set(tf2.keys()))
    if not all_terms:
        return 0.0

    vec1 = {}
    vec2 = {}
    for term in all_terms:
        c1 = tf1.get(term, 0)
        c2 = tf2.get(term, 0)
        
        # IDF calculation across the pair
        doc_count = (1 if c1 > 0 else 0) + (1 if c2 > 0 else 0)
        idf = math.log(2.0 / doc_count) + 1.0
        
        v1 = (1.0 + math.log(c1)) * idf if c1 > 0 else 0.0
        v2 = (1.0 + math.log(c2)) * idf if c2 > 0 else 0.0
        
        vec1[term] = v1
        vec2[term] = v2

    dot_product = sum(vec1[t] * vec2[t] for t in all_terms)
    mag1 = math.sqrt(sum(v * v for v in vec1.values()))
    mag2 = math.sqrt(sum(v * v for v in vec2.values()))
    
    tfidf_sim = (dot_product / (mag1 * mag2)) if (mag1 > 0 and mag2 > 0) else 0.0
    
    # Overlap metrics
    set1 = set(tokens1)
    set2 = set(tokens2)
    intersection = set1 & set2
    
    if not intersection:
        return 0.0

    overlap_ratio = len(intersection) / min(len(set1), len(set2))
    jaccard = len(intersection) / len(set1 | set2)
    
    # Weighted ensemble score
    score = (tfidf_sim * 0.5) + (overlap_ratio * 0.3) + (jaccard * 0.2)
    return min(1.0, max(0.0, score))


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates in meters."""
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def are_locations_matching(lat1, lon1, building1, label1,
                           lat2, lon2, building2, label2,
                           max_distance_meters: float = 120.0) -> bool:
    """
    Check if two locations refer to the same or nearby campus location.
    Matches if:
    - Same campus building ID
    - Geographic coordinates within max_distance_meters
    - Similar location labels/names
    """
    # 1. Building ID match
    if building1 and building2 and building1 != "custom" and building2 != "custom":
        if building1.strip().lower() == building2.strip().lower():
            return True

    # 2. Coordinates proximity match
    if lat1 is not None and lon1 is not None and lat2 is not None and lon2 is not None:
        try:
            dist = haversine_distance_meters(float(lat1), float(lon1), float(lat2), float(lon2))
            if dist <= max_distance_meters:
                return True
        except (ValueError, TypeError):
            pass

    # 3. Location label text match
    if label1 and label2:
        norm1 = label1.strip().lower()
        norm2 = label2.strip().lower()
        if norm1 == norm2:
            return True
        # Check if one contains the other (e.g. "Library" in "Central Library")
        if len(norm1) >= 4 and len(norm2) >= 4:
            if norm1 in norm2 or norm2 in norm1:
                return True

    # 4. Check building name from building ID against label
    b1_info = get_building_by_id(building1) if building1 else None
    b2_info = get_building_by_id(building2) if building2 else None
    
    if b1_info and label2:
        if b1_info["name"].lower() in label2.lower() or label2.lower() in b1_info["name"].lower():
            return True
    if b2_info and label1:
        if b2_info["name"].lower() in label1.lower() or label1.lower() in b2_info["name"].lower():
            return True

    return False


def find_duplicate_report(title: str, description: str, category: str = None,
                          latitude: float = None, longitude: float = None,
                          campus_building: str = None, location_label: str = None,
                          similarity_threshold: float = 0.35) -> dict | None:
    """
    Find existing report that is likely a duplicate of the given problem.
    Returns dictionary with duplicate details or None.
    """
    query_text = f"{title} {description}".strip()
    if not query_text:
        return None

    # Fetch existing reports from DB (order by most recent)
    existing_reports = Report.query.order_by(Report.created_at.desc()).limit(150).all()
    
    best_match = None
    highest_sim = 0.0

    for rep in existing_reports:
        rep_building = getattr(rep, "campus_building", None)
        rep_label = rep.location_label or ""
        
        loc_match = are_locations_matching(
            latitude, longitude, campus_building, location_label,
            rep.latitude, rep.longitude, rep_building, rep_label
        )

        if not loc_match:
            continue

        existing_text = f"{rep.title} {rep.description}".strip()
        sim = compute_cosine_similarity(query_text, existing_text)

        # Small boost if categories match
        if category and rep.category and category.lower() == rep.category.lower():
            sim = min(1.0, sim * 1.05)

        if sim >= similarity_threshold and sim > highest_sim:
            highest_sim = sim
            
            # Format human-readable location label
            disp_loc = rep.location_label
            if not disp_loc and rep.latitude is not None and rep.longitude is not None:
                disp_loc = f"Pinned Map Location ({rep.latitude:.4f}, {rep.longitude:.4f})"
            elif not disp_loc:
                disp_loc = "Campus Location"

            best_match = {
                "id": rep.id,
                "title": rep.title,
                "description": rep.description[:150] + ("..." if len(rep.description) > 150 else ""),
                "location": disp_loc,
                "status": rep.status,
                "similarity_pct": int(round(sim * 100)),
                "category": rep.category,
                "created_at": rep.created_at.strftime("%b %d, %Y") if rep.created_at else "",
            }

    return best_match
