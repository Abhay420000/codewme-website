from flask import Flask, render_template, abort, send_from_directory
import json
import os
import math

app = Flask(__name__)

# --- CONFIGURATION ---
QUESTIONS_PER_SET = 20  

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
    Example: [{'category': 'Salesforce', 'set_num': 1}, {'category': 'Salesforce', 'set_num': 2}]
    """
    if not os.path.exists('mcqs.json'):
        return []
    
    with open('mcqs.json', 'r', encoding='utf-8') as f:
        questions = json.load(f)
    
    # 1. Identify all unique Category + Set combinations
    # Structure: { ("Salesforce Agentforce", 1), ("Salesforce Agentforce", 2) }
    unique_sets = set()
    for q in questions:
        cat = q.get('category', 'Uncategorized')
        set_id = q.get('set_id', 1)
        unique_sets.add((cat, set_id))
    
    # 2. Convert to a clean list of dictionaries
    set_list = []
    for cat, sid in unique_sets:
        set_list.append({
            'category': cat,
            'set_num': sid,
            'url_slug': cat.replace(' ', '-').lower()
        })
    
    # 3. Sort by Category then Set Number
    set_list.sort(key=lambda x: (x['category'], x['set_num']))
    
    return set_list

# --- 1. HOMEPAGE ---
@app.route('/')
def home():
    articles = get_articles()
    return render_template('home.html', articles=articles)

# --- 2. FEATURE ROUTES ---
@app.route('/contest')
def page_contest():
    return render_template('contest.html')

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
    questions = [q for q in all_data if q['set_id'] == set_num and q['category'].lower() == cat_clean.lower()]

    if not questions:
        abort(404)

    # Check if Next Set exists (for button visibility)
    next_set_questions = [q for q in all_data if q['set_id'] == set_num + 1 and q['category'].lower() == cat_clean.lower()]
    has_next = len(next_set_questions) > 0

    title = f"{cat_clean.title()} Exam Questions - Set {set_num}"
    
    return render_template(
        'mcq_layout.html', 
        questions=questions, 
        title=title, 
        category=cat_clean, 
        set_num=set_num, 
        has_next=has_next
    )

if __name__ == '__main__':
    app.run(debug=True)