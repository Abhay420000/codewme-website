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
@app.route('/service-console-tools')
def article_service_console():
    return render_template('articles/service_console_tools_quickText.html')

# Example for your next video (Uncomment when needed):
# @app.route('/python-variables-tutorial')
# def article_python_vars():
#     return render_template('articles/python_vars.html')

if __name__ == '__main__':
    app.run(debug=True)