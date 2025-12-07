from flask import Flask, render_template, abort, send_from_directory
import json
import os
import math
from datetime import datetime

app = Flask(__name__)

# --- CONFIGURATION ---
QUESTIONS_PER_SET = 20 
CONTESTS_DB = 'contests.json'

# --- HELPER: Load Articles ---
def get_articles():
    if os.path.exists('articles.json'):
        with open('articles.json', 'r') as f:
            return json.load(f)
    return []

# --- HELPER: Load & Organize MCQs ---
def get_mcq_sets():
    """
    Returns a flat list of all available sets for the Practice Page.
    """
    if not os.path.exists('mcqs.json'):
        return []
    
    with open('mcqs.json', 'r', encoding='utf-8') as f:
        questions = json.load(f)
    
    # Identify unique sets by (Category, SetID)
    sets_map = {} 
    for q in questions:
        cat = q.get('category', 'Uncategorized')
        sid = q.get('set_id', 1)
        tag = q.get('tag', 'General')
        
        # Default text matches your original hardcoded text to keep design consistent
        default_desc = f"Practice questions for Set {sid}. Master the concepts with detailed explanations."
        desc = q.get('description', default_desc)
        
        # We only need to grab metadata once per set (using the first question found)
        if (cat, sid) not in sets_map:
            sets_map[(cat, sid)] = {
                'tag': tag,
                'description': desc
            }
    
    # Convert to list
    set_list = []
    for (cat, sid), meta in sets_map.items():
        set_list.append({
            'category': cat,
            'set_num': sid,
            'tag': meta['tag'],
            'description': meta['description'],
            'url_slug': cat.replace(' ', '-').lower()
        })
    
    # Sort
    set_list.sort(key=lambda x: (x['category'], x['set_num']))
    
    return set_list
    # --- HELPER: Load & Sort Contests ---
def get_contests():
    if not os.path.exists(CONTESTS_DB):
        return [], []
    
    with open(CONTESTS_DB, 'r', encoding='utf-8') as f:
        all_contests = json.load(f)

    now = datetime.now()
    live_contests = []
    expired_contests = []

    for c in all_contests:
        start_time = datetime.strptime(c['start_date'], '%Y-%m-%d %H:%M:%S')
        end_time = datetime.strptime(c['end_date'], '%Y-%m-%d %H:%M:%S')
        
        if end_time > now:
            # Contest is Live/Upcoming (Use start_date for sorting)
            live_contests.append(c)
        else:
            # Contest is Expired (Use end_date for sorting)
            expired_contests.append(c)

    # 1. Sort Live: Older Order (Earliest start_date first)
    live_contests.sort(key=lambda x: datetime.strptime(x['start_date'], '%Y-%m-%d %H:%M:%S'))

    # 2. Sort Expired: Latest Expired Order (Most recent end_date first)
    expired_contests.sort(key=lambda x: datetime.strptime(x['end_date'], '%Y-%m-%d %H:%M:%S'), reverse=True)

    return live_contests, expired_contests
# --- 1. HOMEPAGE ---
@app.route('/')
def home():
    articles = get_articles()
    return render_template('home.html', articles=articles)

# --- 2. FEATURE ROUTES ---
@app.route('/contest')
def page_contest():
    live_contests, expired_contests = get_contests()
    return render_template('contest.html', 
                           live_contests=live_contests, 
                           expired_contests=expired_contests)

@app.route('/practice-mcqs')
def page_practice_mcqs():
    # Get the flat list of sets
    all_sets = get_mcq_sets()
    return render_template('practice_mcqs.html', all_sets=all_sets)

@app.route('/online-compiler')
def page_online_compiler():
    return render_template('online_compiler.html')

# --- 3. LEGAL & INFO PAGES ---
@app.route('/about')
def page_about():
    return render_template('legal/about.html')

@app.route('/contact')
def page_contact():
    return render_template('legal/contact.html')

@app.route('/privacy-policy')
def page_privacy():
    return render_template('legal/privacy.html')

@app.route('/terms-of-service')
def page_terms():
    return render_template('legal/terms.html')

# --- 4. ADS.TXT ---
@app.route('/ads.txt')
def ads_txt():
    return send_from_directory('static', 'ads.txt')

# --- 5. DYNAMIC ARTICLE ROUTE ---
@app.route('/<slug>')
def article_detail(slug):
    articles = get_articles()
    article = next((item for item in articles if item["slug"] == slug), None)
    
    if article:
        try:
            return render_template(f'articles/{slug}.html', article=article)
        except Exception as e:
            return f"<h1>Error</h1><p>Template 'templates/articles/{slug}.html' not found.</p>", 404
    else:
        abort(404)

# --- 6. MCQ SETS ROUTE ---
@app.route('/mcqs/<category>/set-<int:set_num>')
def mcq_page(category, set_num):
    if os.path.exists('mcqs.json'):
        with open('mcqs.json', 'r', encoding='utf-8') as f:
            all_data = json.load(f)
    else:
        all_data = []

    # Clean URL category back to normal string
    cat_clean = category.replace('-', ' ')
    
    # Filter Questions for Current Set
    # Note: Using case-insensitive match for category
    questions = [q for q in all_data if q['set_id'] == set_num and q['category'].lower() == cat_clean.lower()]

    if not questions:
        abort(404)

    # Get metadata from the first question of this set
    first_q = questions[0]
    current_tag = first_q.get('tag', 'General')

    # Check Next Set
    next_set_questions = [q for q in all_data if q['set_id'] == set_num + 1 and q['category'].lower() == cat_clean.lower()]
    has_next = len(next_set_questions) > 0

    # Sidebar sets (Same Category only)
    all_sets_info = get_mcq_sets()
    sidebar_sets = [s for s in all_sets_info if s['category'].lower() == cat_clean.lower()]

    title = f"{cat_clean} - Set {set_num}"
    
    return render_template(
        'mcq_layout.html', 
        questions=questions, 
        title=title, 
        category=cat_clean,
        current_tag=current_tag, 
        set_num=set_num, 
        has_next=has_next,
        sidebar_sets=sidebar_sets
    )

if __name__ == '__main__':
    app.run(debug=True)
