from flask import Flask, render_template, abort
import json
import os

app = Flask(__name__)

# --- HELPER: Load Database ---
def get_articles():
    """Reads the articles.json file and returns a list of dictionaries."""
    if os.path.exists('articles.json'):
        with open('articles.json', 'r') as f:
            return json.load(f)
    return []

# --- 1. HOMEPAGE ---
@app.route('/')
def home():
    # Fetch all articles from the database
    articles = get_articles()
    # Pass them to the template so it can loop through them
    return render_template('home.html', articles=articles)

# --- 2. DYNAMIC ARTICLE ROUTE ---
# This single function handles ALL current and future articles.
@app.route('/<slug>')
def article_detail(slug):
    articles = get_articles()
    
    # Find the specific article data by matching the URL slug
    article = next((item for item in articles if item["slug"] == slug), None)
    
    if article:
        # Try to load the HTML file that matches the slug
        # Example: /quick-text-in-salesforce looks for templates/articles/quick-text-in-salesforce.html
        try:
            return render_template(f'articles/{slug}.html', article=article)
        except Exception as e:
            return f"<h1>Error</h1><p>Template 'templates/articles/{slug}.html' not found. Please check the filename.</p>", 404
    else:
        abort(404)

if __name__ == '__main__':
    app.run(debug=True)