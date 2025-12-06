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
    def __init__(self, widget, text='widget info'):
        self.waittime = 500     
        self.wraplength = 180   
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
        self.tw = tk.Toplevel(self.widget)
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

# --- SCROLLABLE FRAME CLASS ---
class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0, bg="#f0f2f5")
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#f0f2f5", padx=15, pady=15)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.window_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Ensure the inner frame resizes with the canvas
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Mousewheel binding
        self.scrollable_frame.bind('<Enter>', lambda _: self.canvas.bind_all("<MouseWheel>", self._on_mousewheel))
        self.scrollable_frame.bind('<Leave>', lambda _: self.canvas.unbind_all("<MouseWheel>"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.window_id, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

class ArticleAutomator:
    def __init__(self, root):
        self.root = root
        self.root.title("CodeWme CMS & Builder")
        self.root.geometry("1200x850")
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TLabel", background="#f0f2f5", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground="#1e293b", background="#f0f2f5")
        style.configure("Card.TFrame", background="white", relief="raised")

        # --- TABS ---
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Editor
        self.tab_editor = tk.Frame(self.notebook, bg="#e2e8f0")
        self.notebook.add(self.tab_editor, text="  📝 Editor  ")
        self._init_editor_tab()

        # Tab 2: Manager
        self.tab_manage = tk.Frame(self.notebook, bg="white")
        self.notebook.add(self.tab_manage, text="  📂 Manage Articles  ")
        self._init_manage_tab()

    # ==========================================
    # TAB 1: EDITOR UI (Responsive Split)
    # ==========================================
    def _init_editor_tab(self):
        # Main Splitter
        paned = tk.PanedWindow(self.tab_editor, orient=tk.HORIZONTAL, sashwidth=4, bg="#cbd5e1")
        paned.pack(fill=tk.BOTH, expand=True)

        # --- LEFT PANEL CONTAINER ---
        left_main = tk.Frame(paned, bg="#f0f2f5", width=400)
        
        # 1. Scrollable Form Area
        form_wrapper = ScrollableFrame(left_main)
        form_wrapper.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        left_content = form_wrapper.scrollable_frame # We add widgets here

        # 2. Fixed Bottom Area (Publish Button)
        bottom_bar = tk.Frame(left_main, bg="#e2e8f0", padx=15, pady=15, borderwidth=1, relief="solid")
        bottom_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # --- RIGHT PANEL CONTAINER ---
        right_main = tk.Frame(paned, bg="white", padx=20, pady=20)

        paned.add(left_main, minsize=350)
        paned.add(right_main, minsize=400)

        # === FILL LEFT PANEL (Form) ===
        ttk.Label(left_content, text="Article Metadata", style="Header.TLabel").pack(anchor="w", pady=(0, 15))
        
        tk.Button(left_content, text="Reset Form / New Article", bg="#64748b", fg="white", relief="flat", padx=10, pady=5, command=self.clear_form).pack(fill=tk.X, pady=(0,20))

        def add_field(label, tooltip):
            frame = tk.Frame(left_content, bg="#f0f2f5")
            frame.pack(anchor="w", fill=tk.X, pady=(5, 0))
            ttk.Label(frame, text=label).pack(side=tk.LEFT)
            lbl = tk.Label(frame, text="ⓘ", bg="#f0f2f5", fg="#3b82f6", font=("Segoe UI", 10), cursor="hand2")
            lbl.pack(side=tk.LEFT, padx=5)
            CreateToolTip(lbl, tooltip)
            return frame

        # Inputs
        add_field("Paste YouTube Iframe (Optional):", "Copy embed code from YouTube. Leave blank for text-only articles.")
        self.txt_youtube = tk.Text(left_content, height=3, font=("Consolas", 9), wrap=tk.WORD, borderwidth=1, relief="solid")
        self.txt_youtube.pack(fill=tk.X, pady=(2, 10))
        self.txt_youtube.bind('<KeyRelease>', self.parse_video_id)

        self.var_video_id = tk.StringVar()
        tk.Entry(left_content, textvariable=self.var_video_id, state="readonly", bg="#e2e8f0", font=("Consolas", 9)).pack(fill=tk.X, pady=(0, 15))

        add_field("Article Title:", "Main H1 title.")
        self.var_title = tk.StringVar()
        tk.Entry(left_content, textvariable=self.var_title, font=("Segoe UI", 10), borderwidth=1, relief="solid").pack(fill=tk.X, pady=(2, 15), ipady=3)

        add_field("URL Slug (Unique ID):", "e.g. my-article-name")
        self.var_slug = tk.StringVar()
        self.entry_slug = tk.Entry(left_content, textvariable=self.var_slug, font=("Consolas", 10, "bold"), borderwidth=1, relief="solid")
        self.entry_slug.pack(fill=tk.X, pady=(2, 15), ipady=3)

        add_field("Category:", "e.g. SALESFORCE, PYTHON")
        self.var_category = tk.StringVar(value="SALESFORCE")
        tk.Entry(left_content, textvariable=self.var_category, font=("Segoe UI", 10), borderwidth=1, relief="solid").pack(fill=tk.X, pady=(2, 15), ipady=3)

        add_field("Placeholder Text (Optional):", "Custom text shown on card if no video/image exists.")
        self.var_placeholder = tk.StringVar()
        tk.Entry(left_content, textvariable=self.var_placeholder, font=("Segoe UI", 10), borderwidth=1, relief="solid").pack(fill=tk.X, pady=(2, 15), ipady=3)

        add_field("Short Description:", "Summary for the homepage card.")
        self.txt_desc = tk.Text(left_content, height=4, font=("Segoe UI", 10), wrap=tk.WORD, borderwidth=1, relief="solid")
        self.txt_desc.pack(fill=tk.X, pady=(2, 20))

        # === FILL BOTTOM BAR (Fixed Publish Button) ===
        tk.Button(bottom_bar, text="💾 PUBLISH ARTICLE", bg="#22c55e", fg="white", font=("Segoe UI", 11, "bold"), pady=8, relief="flat", cursor="hand2", command=self.publish_article).pack(fill=tk.X)

        # === FILL RIGHT PANEL (Editor) ===
        ttk.Label(right_main, text="Content Editor", style="Header.TLabel", background="white").pack(anchor="w", pady=(0, 10))
        
        # Toolbar Container
        toolbar_frame = tk.Frame(right_main, bg="#f1f5f9", padx=5, pady=5, relief="flat")
        toolbar_frame.pack(fill=tk.X, pady=(0, 10))

        def make_btn(parent, text, cmd, bg="#3b82f6", fg="white", tip=None):
            btn = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, relief="flat", padx=10, pady=4, font=("Segoe UI", 9))
            btn.pack(side=tk.LEFT, padx=3, pady=2)
            if tip: CreateToolTip(btn, tip)

        # Formatting Buttons
        make_btn(toolbar_frame, "H2", lambda: self.wrap_text('<h2 class="article-h2">', '</h2>'), tip="Insert Heading 2")
        make_btn(toolbar_frame, "H3", lambda: self.wrap_text('<h3 class="article-h3">', '</h3>'), tip="Insert Heading 3")
        make_btn(toolbar_frame, "¶", lambda: self.wrap_text('<p class="article-text">', '</p>'), tip="Paragraph")
        make_btn(toolbar_frame, "• List", self.insert_list, tip="Insert List")
        
        # Special Blocks
        tk.Frame(toolbar_frame, width=1, bg="#cbd5e1").pack(side=tk.LEFT, fill=tk.Y, padx=5) # Spacer
        make_btn(toolbar_frame, "{ } Code", self.insert_code_block, bg="#1e293b", tip="Code Block")
        make_btn(toolbar_frame, "ℹ️ Info", self.insert_callout, bg="#0ea5e9", tip="Info Box")
        make_btn(toolbar_frame, "🖼️ Image", self.prompt_image_source, bg="#8b5cf6", tip="Insert Image")
        
        # Alignment
        tk.Frame(toolbar_frame, width=1, bg="#cbd5e1").pack(side=tk.LEFT, fill=tk.Y, padx=5) # Spacer
        make_btn(toolbar_frame, "L", lambda: self.wrap_alignment('left'), bg="#64748b", tip="Align Left")
        make_btn(toolbar_frame, "C", lambda: self.wrap_alignment('center'), bg="#64748b", tip="Align Center")
        make_btn(toolbar_frame, "R", lambda: self.wrap_alignment('right'), bg="#64748b", tip="Align Right")

        # Main Text Editor
        self.editor = scrolledtext.ScrolledText(right_main, font=("Consolas", 11), wrap=tk.WORD, undo=True, padx=15, pady=15, borderwidth=1, relief="solid")
        self.editor.pack(fill=tk.BOTH, expand=True)
        self.editor.insert(tk.END, "<!-- Content goes here -->\n")

    # ==========================================
    # TAB 2: MANAGE UI
    # ==========================================
    def _init_manage_tab(self):
        # 1. Header (Top)
        top_frame = tk.Frame(self.tab_manage, bg="white", pady=20, padx=20)
        top_frame.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(top_frame, text="Manage Articles", style="Header.TLabel", background="white").pack(side=tk.LEFT)
        tk.Button(top_frame, text="🔄 Refresh", command=self.load_articles_list, relief="flat", bg="#e2e8f0", padx=10).pack(side=tk.RIGHT)

        # 2. Buttons (Bottom) - Pack FIRST to ensure visibility
        btn_frame = tk.Frame(self.tab_manage, bg="white", pady=20, padx=20)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        tk.Button(btn_frame, text="✏️ EDIT SELECTED", bg="#2563eb", fg="white", font=("Segoe UI", 10, "bold"), padx=20, pady=10, relief="flat", command=self.edit_selected).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="🗑️ DELETE SELECTED", bg="#ef4444", fg="white", font=("Segoe UI", 10, "bold"), padx=20, pady=10, relief="flat", command=self.delete_selected).pack(side=tk.LEFT, padx=5)

        # 3. Listbox (Middle)
        list_frame = tk.Frame(self.tab_manage, bg="white")
        list_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=20, pady=10)

        style = ttk.Style()
        style.configure("Treeview", rowheight=30, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

        self.tree = ttk.Treeview(list_frame, columns=("Date", "Title", "Slug"), show='headings', height=20)
        self.tree.heading("Date", text="Date")
        self.tree.heading("Title", text="Title")
        self.tree.heading("Slug", text="Slug (ID)")
        self.tree.column("Date", width=120)
        self.tree.column("Title", width=400)
        self.tree.column("Slug", width=300)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.load_articles_list()

    # --- LOGIC METHODS ---
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
        self.var_placeholder.set("") # Clear placeholder
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
        self.var_placeholder.set(article.get('placeholder_text', '')) # Load placeholder
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
        
        # 1. Update JSON
        if os.path.exists(ARTICLES_DB):
            with open(ARTICLES_DB, 'r') as f: articles = json.load(f)
            articles = [a for a in articles if a['slug'] != slug]
            with open(ARTICLES_DB, 'w') as f: json.dump(articles, f, indent=2)
        
        # 2. Delete HTML & IMAGES (The Fix)
        html_path = os.path.join(TEMPLATE_DIR, f"{slug}.html")
        if os.path.exists(html_path):
            try:
                # Read content to find and delete images first
                with open(html_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Regex matches filename='images/xyz.png'
                images = re.findall(r"filename='images/([^']+)'", content)
                for img in images:
                    img_path = os.path.join('static', 'images', img)
                    if os.path.exists(img_path):
                        os.remove(img_path)
                        print(f"Deleted image: {img_path}")

                os.remove(html_path)
                print(f"Deleted file: {html_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not delete file: {e}")
        
        self.load_articles_list()
        messagebox.showinfo("Deleted", "Article removed successfully.")

    def publish_article(self):
        if not self.var_title.get() or not self.var_slug.get():
            messagebox.showerror("Error", "Title and Slug are required!")
            return
        slug = self.var_slug.get().strip()
        
        # Prepare Data
        data = {
            "title": self.var_title.get(),
            "slug": slug,
            "video_id": self.var_video_id.get(),
            "placeholder_text": self.var_placeholder.get().strip(), # Save placeholder
            "date": datetime.now().strftime("%b %d, %Y"),
            "category": self.var_category.get(),
            "description": self.txt_desc.get("1.0", tk.END).strip()
        }

        # Update JSON
        if not os.path.exists(ARTICLES_DB): articles = []
        else:
            with open(ARTICLES_DB, 'r') as f: articles = json.load(f)
        idx = next((i for i, item in enumerate(articles) if item["slug"] == slug), -1)
        if idx >= 0: articles[idx] = data
        else: articles.insert(0, data)
        with open(ARTICLES_DB, 'w') as f: json.dump(articles, f, indent=2)
        
        # Generate HTML (Jinja handles empty video_id automatically)
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