from flask import Flask, render_template, abort, send_from_directory
import json
import os

app = Flask(__name__)

# --- HELPER: Load Database ---
def get_articles():
    if os.path.exists('articles.json'):
        with open('articles.json', 'r') as f:
            return json.load(f)
    return []

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
    return render_template('practice_mcqs.html')

@app.route('/online-compiler')
def page_online_compiler():
    return render_template('online_compiler.html')

# --- 3. LEGAL & INFO PAGES (Required for AdSense) ---
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

# --- 4. DYNAMIC ARTICLE ROUTE ---
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

if __name__ == '__main__':
    app.run(debug=True)