from flask import Flask, render_template, abort, send_from_directory, request, jsonify, session, redirect, url_for, make_response
from flask_mail import Mail, Message
import os
import random
import utils  # <--- IMPORT YOUR NEW UTILS MODULE

# --- DOTENV ---
try:
    from dotenv import load_dotenv
    load_dotenv() 
except ModuleNotFoundError: 
    pass

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default-key')

# --- MAIL CONFIG ---
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')

mail = Mail(app)

# In-memory store for OTPs (resets on restart)
user_otps = {} 

# ==========================================
# 1. MAIN PAGE ROUTES
# ==========================================

@app.route('/')
def home():
    # Fetch articles using Utils (JSON)
    articles = utils.get_all_articles()
    return render_template('home.html', articles=articles)

# ==========================================
# CONTEST PAGE ROUTE (TOGGLE BELOW)
# ==========================================

# --- OPTION 1: TEMPORARY COMING SOON PAGE (ACTIVE) ---
@app.route('/contest')
def page_contest():
   return render_template('contest_coming_soon.html')

# --- OPTION 2: REAL CONTEST PAGE (COMMENTED OUT) ---
# @app.route('/contest')
# def page_contest():
#     # Fetch contests using Utils (JSON)
#     live, expired = utils.get_contests_data()
#     return render_template('contest.html', live_contests=live, expired_contests=expired)

@app.route('/practice-mcqs')
def page_practice_mcqs():
    # Only fetch the first 6 sets (Page 1)
    # This keeps the initial load instant and RAM usage low
    initial_sets = utils.get_paginated_mcq_sets(page=1, per_page=6)
    return render_template('practice_mcqs.html', initial_sets=initial_sets)

# --- NEW: API FOR "LOAD MORE" BUTTON ---
@app.route('/api/load-sets')
def api_load_sets():
    try:
        # Get page number from URL (e.g., ?page=2), default to 2
        page = int(request.args.get('page', 2))
        
        # Fetch the next chunk of sets
        sets = utils.get_paginated_mcq_sets(page=page, per_page=6)
        
        return jsonify({
            'success': True,
            'sets': sets,
            'has_more': len(sets) == 6 # If we got fewer than 6, we reached the end
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/mcqs/<category>/set-<int:set_num>')
def mcq_page(category, set_num):
    # Fetch all data for the single set page using Utils (SQLite)
    data = utils.get_mcq_set_data(category, set_num)
    
    if not data:
        abort(404)

    return render_template(
        'mcq_layout.html', 
        questions=data['questions'], 
        title=f"{data['clean_category']} - Set {set_num}", 
        category=data['clean_category'],
        current_tag=data['current_tag'], 
        set_num=set_num, 
        has_next=data['has_next'],
        sidebar_sets=data['sidebar_sets']
    )

@app.route('/<slug>')
def article_detail(slug):
    # Fetch article by slug using Utils (JSON)
    article = utils.get_article_by_slug(slug)
    
    if article:
        try:
            return render_template(f'articles/{slug}.html', article=article)
        except:
            return f"<h1>Error</h1><p>Template for '{slug}' not found.</p>", 404
            
    # Fallback/404
    abort(404)

# ==========================================
# 2. STATIC & LEGAL PAGES
# ==========================================

@app.route('/online-compiler')
def page_online_compiler():
    return render_template('online_compiler.html')

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

# ==========================================
# 3. REGISTRATION API (OTPs)
# ==========================================
"""
@app.route('/register/<contest_id>')
def registration_page(contest_id):
    live, _ = utils.get_contests_data()
    contest = next((c for c in live if c['id'] == contest_id), None)
    if not contest: abort(404)
    return render_template('registration_page.html', contest=contest)

@app.route('/api/contest/send_otp', methods=['POST'])
def send_otp():
    data = request.get_json()
    email = data.get('email')
    contest_id = data.get('contest_id')
    
    if not email or not contest_id:
        return jsonify({'success': False, 'message': 'Missing data'}), 400

    otp = str(random.randint(100000, 999999))
    
    if contest_id not in user_otps: user_otps[contest_id] = {}
    user_otps[contest_id][email] = otp
    session['registration_email'] = email
    session['current_contest_id'] = contest_id

    try:
        msg = Message(subject='CodeWme Contest Verification', recipients=[email])
        msg.body = f"Your OTP is: {otp}"
        mail.send(msg)
        return jsonify({'success': True})
    except Exception as e:
        print(f"SMTP Error: {e}")
        return jsonify({'success': False, 'message': 'Email failed'}), 500

@app.route('/api/contest/verify_otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    entered_otp = data.get('otp')
    email = session.get('registration_email')
    contest_id = session.get('current_contest_id')

    if not email or not contest_id:
        return jsonify({'success': False, 'message': 'Session expired'}), 400

    stored_otp = user_otps.get(contest_id, {}).get(email)

    if entered_otp == stored_otp:
        session['is_verified'] = True
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Invalid OTP'}), 401

@app.route('/api/contest/confirm_payment', methods=['POST'])
def confirm_payment():
    if not session.get('is_verified'):
        return jsonify({'success': False, 'message': 'Not verified'}), 403
    
    # Simulate success
    session.pop('registration_email', None)
    session.pop('current_contest_id', None)
    session.pop('is_verified', None)
    
    return jsonify({'success': True})
"""

@app.route('/ads.txt')
def ads_txt():
    # Serves the ads.txt file from the root directory
    return send_from_directory(app.root_path, 'ads.txt')

@app.route('/sitemap.xml')
def sitemap():
    host = "https://codewme.dev"
    
    # 1. Static pages
    static_urls = [
        "/",
        "/practice-mcqs",
        "/contest",
        "/online-compiler",
        "/about",
        "/contact",
        "/privacy-policy",
        "/terms-of-service"
    ]
    
    # 2. Dynamic pages from Utils
    dynamic_urls = utils.get_all_sitemap_urls()
    
    all_urls = static_urls + dynamic_urls
    
    # 3. Generate XML
    xml_sitemap = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_sitemap.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    
    for url in all_urls:
        xml_sitemap.append('<url>')
        xml_sitemap.append(f'<loc>{host}{url}</loc>')
        xml_sitemap.append('<changefreq>weekly</changefreq>')
        xml_sitemap.append('<priority>0.8</priority>')
        xml_sitemap.append('</url>')
        
    xml_sitemap.append('</urlset>')
    
    response = make_response('\n'.join(xml_sitemap))
    response.headers["Content-Type"] = "application/xml"
    return response

if __name__ == '__main__':
    app.run(debug=False)