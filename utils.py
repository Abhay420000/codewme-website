import sqlite3
import json
import os
from datetime import datetime

# --- CONFIGURATION ---
DB_NAME = 'mcqs.db'
ARTICLES_FILE = 'articles.json'
CONTESTS_FILE = 'contests.json'

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    if not os.path.exists(DB_NAME):
        return None
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name (row['id'])
    return conn

# --- ARTICLE HELPERS (JSON) ---
def get_all_articles():
    """Reads all articles from JSON."""
    if os.path.exists(ARTICLES_FILE):
        with open(ARTICLES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def get_article_by_slug(slug):
    """Finds a specific article by its slug."""
    articles = get_all_articles()
    return next((a for a in articles if a["slug"] == slug), None)

# --- MCQ HELPERS (SQLite) ---

def get_paginated_mcq_sets(page=1, per_page=6):
    """
    Fetches a specific chunk of sets for the Load More button.
    Efficiently uses LIMIT and OFFSET.
    """
    conn = get_db_connection()
    if not conn: return []
    
    offset = (page - 1) * per_page
    
    # --- SORTING LOGIC ---
    # ORDER BY category ASC  -> A to Z (e.g. Apex, then Salesforce)
    # ORDER BY set_id DESC   -> 10 to 1 (Newest/Highest Set first)
    rows = conn.execute('''
        SELECT category, set_id as set_num, tag, description 
        FROM questions 
        GROUP BY category, set_id 
        ORDER BY category ASC, set_id DESC
        LIMIT ? OFFSET ?
    ''', (per_page, offset)).fetchall()
    conn.close()
    
    sets = []
    for r in rows:
        s = dict(r)
        s['url_slug'] = s['category'].replace(' ', '-').lower()
        sets.append(s)
    return sets

def get_mcq_set_data(category, set_num):
    """
    Fetches everything needed for the Single Set Page:
    1. The Questions
    2. The Metadata (Tags)
    3. 'Next Set' check
    4. Sidebar Links
    """
    clean_cat = category.replace('-', ' ')
    conn = get_db_connection()
    if not conn: return None
    
    # 1. Fetch Questions for this set
    q_rows = conn.execute('''
        SELECT * FROM questions 
        WHERE set_id = ? AND category = ? COLLATE NOCASE
    ''', (set_num, clean_cat)).fetchall()
    
    if not q_rows:
        conn.close()
        return None

    # Parse JSON strings back to Python lists
    questions = []
    for row in q_rows:
        q = dict(row)
        q['options'] = json.loads(q['options'])
        q['correct'] = json.loads(q['correct'])
        questions.append(q)

    # 2. Check if Next Set exists (for the "Next" button)
    next_check = conn.execute('''
        SELECT 1 FROM questions 
        WHERE set_id = ? AND category = ? COLLATE NOCASE 
        LIMIT 1
    ''', (set_num + 1, clean_cat)).fetchone()
    has_next = next_check is not None

    # 3. Sidebar Data (Latest 5 sets in this category)
    sb_rows = conn.execute('''
        SELECT DISTINCT set_id 
        FROM questions 
        WHERE category = ? COLLATE NOCASE 
        ORDER BY set_id DESC
        LIMIT 5
    ''', (clean_cat,)).fetchall()
    
    sidebar_sets = [
        {'category': clean_cat, 'set_num': r['set_id'], 'url_slug': category} 
        for r in sb_rows
    ]
    
    conn.close()

    return {
        'questions': questions,
        'current_tag': questions[0]['tag'],
        'clean_category': clean_cat,
        'has_next': has_next,
        'sidebar_sets': sidebar_sets
    }

# --- CONTEST HELPERS (JSON) ---
def get_contests_data():
    """Returns live and expired contests from JSON."""
    if not os.path.exists(CONTESTS_FILE):
        return [], []
    
    with open(CONTESTS_FILE, 'r', encoding='utf-8') as f:
        all_c = json.load(f)

    now = datetime.now()
    live, expired = [], []

    for c in all_c:
        try:
            # Parse dates
            start = datetime.strptime(c['start_date'], '%Y-%m-%d %H:%M:%S')
            end = datetime.strptime(c['end_date'], '%Y-%m-%d %H:%M:%S')
            
            if end > now: 
                live.append(c)
            else: 
                expired.append(c)
        except: 
            continue

    # Sort Live by Start Date
    live.sort(key=lambda x: x['start_date'])
    # Sort Expired by End Date (Newest expired first)
    expired.sort(key=lambda x: x['end_date'], reverse=True)
    
    return live, expired