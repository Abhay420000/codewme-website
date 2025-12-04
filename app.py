from flask import Flask, render_template

app = Flask(__name__)

# --- 1. HOMEPAGE ---
@app.route('/')
def home():
    return render_template('home.html')

# --- 2. ARTICLE ROUTES ---
# EVERY TIME you make a new video, you will add a new block here.
# The string inside @app.route('...') is what appears in the browser URL.

# Add this to app.py
@app.route('/quick-text-in-salesforce')
def article_service_console():
    return render_template('articles/service_console_tools_quickText.html')

# Article 2: Apex Transactions
@app.route('/how-to-manage-transactions-in-salesforce-apex')
def article_apex_transactions():
    return render_template('articles/apex_transactions.html')

if __name__ == '__main__':
    app.run(debug=True)