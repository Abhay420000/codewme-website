import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog, filedialog
import json
import os
import re
import shutil
from datetime import datetime

# --- CONFIGURATION ---
ARTICLES_DB = 'articles.json'
TEMPLATE_DIR = os.path.join('templates', 'articles')

# --- TOOLTIP CLASS ---
class CreateToolTip(object):
    """
    create a tooltip for a given widget
    """
    def __init__(self, widget, text='widget info'):
        self.waittime = 500     #miliseconds
        self.wraplength = 180   #pixels
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        # creates a toplevel window
        self.tw = tk.Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(self.tw, text=self.text, justify='left',
                       background="#ffffe0", relief='solid', borderwidth=1,
                       wraplength = self.wraplength, font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tw
        self.tw= None
        if tw:
            tw.destroy()

class ArticleAutomator:
    def __init__(self, root):
        self.root = root
        self.root.title("CodeWme CMS & Builder")
        self.root.geometry("1200x850")
        self.root.configure(bg="#f0f2f5")
        
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TLabel", background="#f0f2f5", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#1e293b")

        # --- TABS ---
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Editor
        self.tab_editor = tk.Frame(self.notebook, bg="#f0f2f5")
        self.notebook.add(self.tab_editor, text=" 📝 Editor (Create/Update) ")
        self._init_editor_tab()

        # Tab 2: Manager
        self.tab_manage = tk.Frame(self.notebook, bg="white")
        self.notebook.add(self.tab_manage, text=" 📂 Manage Articles ")
        self._init_manage_tab()

    # ==========================================
    # TAB 1: EDITOR UI
    # ==========================================
    def _init_editor_tab(self):
        # Left Panel (Metadata)
        left_frame = tk.Frame(self.tab_editor, bg="#f0f2f5", width=350, padx=20, pady=20)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        # Right Panel (Content)
        right_frame = tk.Frame(self.tab_editor, bg="white", padx=20, pady=20)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # --- LEFT PANEL CONTENT ---
        ttk.Label(left_frame, text="Article Metadata", style="Header.TLabel").pack(anchor="w", pady=(0, 20))

        # Buttons
        tk.Button(left_frame, text="Clear Form / New Article", bg="#64748b", fg="white", command=self.clear_form).pack(fill=tk.X, pady=(0,15))

        # Fields
        
        # 1. YouTube Iframe
        yt_label_frame = tk.Frame(left_frame, bg="#f0f2f5")
        yt_label_frame.pack(anchor="w", fill=tk.X)
        ttk.Label(yt_label_frame, text="Paste YouTube Iframe:").pack(side=tk.LEFT)
        lbl_help_yt = tk.Label(yt_label_frame, text="ⓘ", bg="#f0f2f5", fg="#3b82f6", font=("Segoe UI", 12), cursor="hand2")
        lbl_help_yt.pack(side=tk.LEFT, padx=5)
        CreateToolTip(lbl_help_yt, "Go to YouTube video -> Share -> Embed. Copy the full <iframe> code and paste it here. Or simply paste the video URL.")

        self.txt_youtube = tk.Text(left_frame, height=4, font=("Consolas", 9), wrap=tk.WORD)
        self.txt_youtube.pack(fill=tk.X, pady=(5, 10))
        self.txt_youtube.bind('<KeyRelease>', self.parse_video_id)

        self.var_video_id = tk.StringVar()
        tk.Entry(left_frame, textvariable=self.var_video_id, state="readonly", bg="#e2e8f0").pack(fill=tk.X, pady=(0, 15))

        # 2. Article Title
        title_label_frame = tk.Frame(left_frame, bg="#f0f2f5")
        title_label_frame.pack(anchor="w", fill=tk.X)
        ttk.Label(title_label_frame, text="Article Title:").pack(side=tk.LEFT)
        lbl_help_title = tk.Label(title_label_frame, text="ⓘ", bg="#f0f2f5", fg="#3b82f6", font=("Segoe UI", 12), cursor="hand2")
        lbl_help_title.pack(side=tk.LEFT, padx=5)
        CreateToolTip(lbl_help_title, "The main headline of your article. This will appear as H1 on the page and in the browser tab.")

        self.var_title = tk.StringVar()
        tk.Entry(left_frame, textvariable=self.var_title, font=("Segoe UI", 11)).pack(fill=tk.X, pady=(5, 15))

        # 3. URL Slug
        slug_label_frame = tk.Frame(left_frame, bg="#f0f2f5")
        slug_label_frame.pack(anchor="w", fill=tk.X)
        ttk.Label(slug_label_frame, text="URL Slug (Unique ID):").pack(side=tk.LEFT)
        lbl_help_slug = tk.Label(slug_label_frame, text="ⓘ", bg="#f0f2f5", fg="#3b82f6", font=("Segoe UI", 12), cursor="hand2")
        lbl_help_slug.pack(side=tk.LEFT, padx=5)
        CreateToolTip(lbl_help_slug, "The URL path for this article (e.g., 'my-article-name'). Must be unique and URL-friendly (lowercase, hyphens).")

        self.var_slug = tk.StringVar()
        self.entry_slug = tk.Entry(left_frame, textvariable=self.var_slug, font=("Consolas", 10, "bold"))
        self.entry_slug.pack(fill=tk.X, pady=(5, 15))

        # 4. Category
        cat_label_frame = tk.Frame(left_frame, bg="#f0f2f5")
        cat_label_frame.pack(anchor="w", fill=tk.X)
        ttk.Label(cat_label_frame, text="Category:").pack(side=tk.LEFT)
        lbl_help_cat = tk.Label(cat_label_frame, text="ⓘ", bg="#f0f2f5", fg="#3b82f6", font=("Segoe UI", 12), cursor="hand2")
        lbl_help_cat.pack(side=tk.LEFT, padx=5)
        CreateToolTip(lbl_help_cat, "The tag displayed on the article card (e.g., 'PYTHON', 'SALESFORCE'). Useful for grouping content.")

        self.var_category = tk.StringVar(value="SALESFORCE")
        tk.Entry(left_frame, textvariable=self.var_category).pack(fill=tk.X, pady=(5, 15))

        # 5. Description
        desc_label_frame = tk.Frame(left_frame, bg="#f0f2f5")
        desc_label_frame.pack(anchor="w", fill=tk.X)
        ttk.Label(desc_label_frame, text="Short Description:").pack(side=tk.LEFT)
        lbl_help_desc = tk.Label(desc_label_frame, text="ⓘ", bg="#f0f2f5", fg="#3b82f6", font=("Segoe UI", 12), cursor="hand2")
        lbl_help_desc.pack(side=tk.LEFT, padx=5)
        CreateToolTip(lbl_help_desc, "A brief summary shown on the homepage card to entice users to click.")

        self.txt_desc = tk.Text(left_frame, height=4, font=("Segoe UI", 10), wrap=tk.WORD)
        self.txt_desc.pack(fill=tk.X, pady=(5, 20))

        tk.Button(left_frame, text="💾 SAVE / PUBLISH", bg="#22c55e", fg="white", font=("Segoe UI", 12, "bold"), pady=10, relief=tk.FLAT, command=self.publish_article).pack(fill=tk.X, side=tk.BOTTOM)

        # --- RIGHT PANEL CONTENT ---
        ttk.Label(right_frame, text="Content Editor", style="Header.TLabel", background="white").pack(anchor="w", pady=(0, 10))
        
        # Toolbar
        toolbar = tk.Frame(right_frame, bg="#f8fafc", padx=5, pady=5, relief=tk.RIDGE, bd=1)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        def make_btn(parent, text, cmd, bg="#3b82f6", fg="white", tip=None):
            btn = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, relief=tk.FLAT, padx=8, pady=2, font=("Segoe UI", 9))
            btn.pack(side=tk.LEFT, padx=2)
            if tip:
                CreateToolTip(btn, tip)

        make_btn(toolbar, "H2", lambda: self.wrap_text('<h2 class="article-h2">', '</h2>'), tip="Insert a Level 2 Heading")
        make_btn(toolbar, "H3", lambda: self.wrap_text('<h3 class="article-h3">', '</h3>'), tip="Insert a Level 3 Heading")
        make_btn(toolbar, "Para", lambda: self.wrap_text('<p class="article-text">', '</p>'), tip="Wrap text in a Paragraph")
        make_btn(toolbar, "List", self.insert_list, tip="Insert a bullet list")
        make_btn(toolbar, "{ } Code", self.insert_code_block, bg="#1e293b", tip="Insert a code block with syntax highlighting")
        make_btn(toolbar, "ℹ️ Info", self.insert_callout, bg="#0ea5e9", tip="Insert a blue Info/Note box")
        make_btn(toolbar, "🖼️ Image", self.prompt_image_source, bg="#8b5cf6", tip="Upload and insert an image from your computer")
        
        tk.Label(toolbar, text="|", bg="#f8fafc").pack(side=tk.LEFT, padx=5)
        make_btn(toolbar, "Left", lambda: self.wrap_alignment('left'), bg="#64748b", tip="Align text Left")
        make_btn(toolbar, "Center", lambda: self.wrap_alignment('center'), bg="#64748b", tip="Align text Center")
        make_btn(toolbar, "Right", lambda: self.wrap_alignment('right'), bg="#64748b", tip="Align text Right")

        self.editor = scrolledtext.ScrolledText(right_frame, font=("Consolas", 11), wrap=tk.WORD, undo=True, padx=10, pady=10)
        self.editor.pack(fill=tk.BOTH, expand=True)
        self.editor.insert(tk.END, "<!-- Content goes here -->\n")

    # ==========================================
    # TAB 2: MANAGE UI
    # ==========================================
    def _init_manage_tab(self):
        # Header
        top_frame = tk.Frame(self.tab_manage, bg="white", pady=20, padx=20)
        top_frame.pack(fill=tk.X)
        
        ttk.Label(top_frame, text="Existing Articles", style="Header.TLabel", background="white").pack(side=tk.LEFT)
        tk.Button(top_frame, text="🔄 Refresh List", command=self.load_articles_list).pack(side=tk.RIGHT)

        # Listbox
        self.tree = ttk.Treeview(self.tab_manage, columns=("Date", "Title", "Slug"), show='headings', height=20)
        self.tree.heading("Date", text="Date")
        self.tree.heading("Title", text="Title")
        self.tree.heading("Slug", text="Slug (ID)")
        
        self.tree.column("Date", width=120)
        self.tree.column("Title", width=400)
        self.tree.column("Slug", width=300)
        
        self.tree.pack(fill=tk.BOTH, expand=True, padx=20)

        # Actions
        btn_frame = tk.Frame(self.tab_manage, bg="white", pady=20, padx=20)
        btn_frame.pack(fill=tk.X)
        
        tk.Button(btn_frame, text="✏️ EDIT SELECTED", bg="#2563eb", fg="white", font=("Segoe UI", 10, "bold"), padx=20, pady=10, command=self.edit_selected).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="🗑️ DELETE SELECTED", bg="#ef4444", fg="white", font=("Segoe UI", 10, "bold"), padx=20, pady=10, command=self.delete_selected).pack(side=tk.LEFT, padx=5)

        # Initial Load
        self.load_articles_list()

    # ==========================================
    # LOGIC METHODS
    # ==========================================

    def parse_video_id(self, event=None):
        text = self.txt_youtube.get("1.0", tk.END)
        match = re.search(r'(?:v=|\/|embed\/)([0-9A-Za-z_-]{11})', text)
        if match: self.var_video_id.set(match.group(1))

    def wrap_text(self, start, end):
        try:
            self.editor.insert(self.editor.index(tk.SEL_FIRST), start)
            self.editor.insert(self.editor.index(tk.SEL_LAST), end)
        except:
            self.editor.insert(tk.INSERT, f"{start}Text{end}")

    def insert_list(self):
        self.editor.insert(tk.INSERT, '\n<ul class="article-list">\n    <li>Item 1</li>\n    <li>Item 2</li>\n</ul>\n')

    def insert_code_block(self):
        self.editor.insert(tk.INSERT, '\n<pre class="code-block language-apex"><code>\n// Your code here\n</code></pre>\n')

    def insert_callout(self):
        self.editor.insert(tk.INSERT, '\n<div class="callout info">\n    <span class="callout-title">ℹ️ Note</span>\n    <p style="margin:0;">Note text...</p>\n</div>\n')

    # --- NEW IMAGE LOGIC ---
    def prompt_image_source(self):
        popup = tk.Toplevel(self.root)
        popup.title("Insert Image")
        popup.geometry("300x160")
        popup.configure(bg="#f8fafc")
        
        ttk.Label(popup, text="Choose Image Source:", font=("Segoe UI", 10, "bold"), background="#f8fafc").pack(pady=10)
        
        def from_file():
            popup.destroy()
            self._insert_image_file()
            
        def from_url():
            popup.destroy()
            self._insert_image_url()
            
        btn_style = {"bg":"#3b82f6", "fg":"white", "relief":tk.FLAT, "pady":5}
        tk.Button(popup, text="📁 Upload from Computer", command=from_file, **btn_style).pack(fill=tk.X, padx=20, pady=5)
        tk.Button(popup, text="🔗 Paste Image URL", command=from_url, **btn_style).pack(fill=tk.X, padx=20, pady=5)

    def _insert_image_file(self):
        file_path = filedialog.askopenfilename(title="Select Image", filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.webp")])
        if not file_path: return
        dest_dir = os.path.join('static', 'images')
        os.makedirs(dest_dir, exist_ok=True)
        filename = os.path.basename(file_path)
        dest_path = os.path.join(dest_dir, filename)
        try: shutil.copy2(file_path, dest_path)
        except: pass
        self._insert_image_html(f"{{{{ url_for('static', filename='images/{filename}') }}}}")

    def _insert_image_url(self):
        url = simpledialog.askstring("Image URL", "Paste the full image URL:")
        if url: self._insert_image_html(url)

    def _insert_image_html(self, src):
        caption = simpledialog.askstring("Image Caption", "Enter caption (optional):") or ""
        html = f'\n<figure>\n    <img src="{src}" class="article-img" alt="{caption}">\n    <figcaption class="img-caption">{caption}</figcaption>\n</figure>\n'
        self.editor.insert(tk.INSERT, html)

    def wrap_alignment(self, align):
        try:
            start, end = self.editor.index(tk.SEL_FIRST), self.editor.index(tk.SEL_LAST)
            txt = self.editor.get(start, end)
            self.editor.delete(start, end)
            self.editor.insert(start, f'<div style="text-align:{align};">\n{txt}\n</div>')
        except:
            self.editor.insert(tk.INSERT, f'<div style="text-align:{align};">\n    Content\n</div>')

    # --- DATA MANAGEMENT ---

    def load_articles_list(self):
        for row in self.tree.get_children(): self.tree.delete(row)
        if os.path.exists(ARTICLES_DB):
            with open(ARTICLES_DB, 'r') as f:
                articles = json.load(f)
                for art in articles: self.tree.insert("", tk.END, values=(art.get('date'), art.get('title'), art.get('slug')))

    def clear_form(self):
        self.var_title.set("")
        self.var_slug.set("")
        self.var_video_id.set("")
        self.var_category.set("SALESFORCE")
        self.txt_youtube.delete("1.0", tk.END)
        self.txt_desc.delete("1.0", tk.END)
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", "<!-- Content -->\n")
        self.entry_slug.config(state='normal')

    def edit_selected(self):
        sel = self.tree.selection()
        if not sel: return
        slug = self.tree.item(sel[0])['values'][2]
        with open(ARTICLES_DB, 'r') as f:
            articles = json.load(f)
            article = next((a for a in articles if a['slug'] == slug), None)
        if not article: return
        self.clear_form()
        self.var_title.set(article['title'])
        self.var_slug.set(article['slug'])
        self.var_video_id.set(article['video_id'])
        self.var_category.set(article['category'])
        self.txt_desc.insert("1.0", article['description'])
        html_path = os.path.join(TEMPLATE_DIR, f"{slug}.html")
        if os.path.exists(html_path):
            with open(html_path, 'r', encoding='utf-8') as f:
                content = f.read()
                match = re.search(r'{% block article_body %}(.*?){% endblock %}', content, re.DOTALL)
                if match:
                    self.editor.delete("1.0", tk.END)
                    self.editor.insert("1.0", match.group(1).strip())
        self.notebook.select(self.tab_editor)

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel: return
        item = self.tree.item(sel[0])['values']
        slug, title = item[2], item[1]
        if not messagebox.askyesno("Confirm", f"Delete '{title}'?"): return
        
        # Update JSON
        with open(ARTICLES_DB, 'r') as f: articles = json.load(f)
        articles = [a for a in articles if a['slug'] != slug]
        with open(ARTICLES_DB, 'w') as f: json.dump(articles, f, indent=2)
        
        # Delete HTML File
        html_path = os.path.join(TEMPLATE_DIR, f"{slug}.html")
        if os.path.exists(html_path):
            try:
                os.remove(html_path)
            except Exception as e:
                messagebox.showerror("Error", f"Could not delete file: {e}")
        
        self.load_articles_list()
        messagebox.showinfo("Deleted", "Article removed successfully.")

    def publish_article(self):
        if not self.var_title.get() or not self.var_slug.get() or not self.var_video_id.get():
            messagebox.showerror("Error", "Required fields missing!")
            return
        slug = self.var_slug.get().strip()
        data = {
            "title": self.var_title.get(),
            "slug": slug,
            "video_id": self.var_video_id.get(),
            "date": datetime.now().strftime("%b %d, %Y"),
            "category": self.var_category.get(),
            "description": self.txt_desc.get("1.0", tk.END).strip()
        }
        if not os.path.exists(ARTICLES_DB): articles = []
        else:
            with open(ARTICLES_DB, 'r') as f: articles = json.load(f)
        idx = next((i for i, item in enumerate(articles) if item["slug"] == slug), -1)
        if idx >= 0: articles[idx] = data
        else: articles.insert(0, data)
        with open(ARTICLES_DB, 'w') as f: json.dump(articles, f, indent=2)
        
        html_content = f"""{{% extends 'article_layout.html' %}}
{{% block title %}}{data['title']} - CodeWme{{% endblock %}}
{{% block meta_description %}}{data['description']}{{% endblock %}}
{{% block article_header %}}{data['title']}{{% endblock %}}
{{% block video_id %}}{data['video_id']}{{% endblock %}}
{{% block article_body %}}
{self.editor.get("1.0", tk.END)}
{{% endblock %}}"""
        os.makedirs(TEMPLATE_DIR, exist_ok=True)
        with open(os.path.join(TEMPLATE_DIR, f"{slug}.html"), 'w', encoding='utf-8') as f: f.write(html_content)
        messagebox.showinfo("Success", f"Article Saved: {slug}")
        self.load_articles_list()

if __name__ == "__main__":
    root = tk.Tk()
    app = ArticleAutomator(root)
    root.mainloop()