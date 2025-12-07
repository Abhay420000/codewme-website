import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog, filedialog
import json
import os
import re
import shutil
import uuid
from datetime import datetime

# --- CONFIGURATION ---
ARTICLES_DB = 'articles.json'
MCQS_DB = 'mcqs.json'
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
    def __init__(self, container, bg_color="#f0f2f5", *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0, bg=bg_color)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=bg_color, padx=15, pady=15)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.window_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
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
        self.root.geometry("1300x900")
        
        # Internal Styling
        self.BG_APP = "#f0f2f5"
        self.BG_PANEL = "white"
        self.BG_READONLY = "#e2e8f0"
        self.BTN_PRIMARY = "#3b82f6"
        self.BTN_SUCCESS = "#22c55e"
        self.BTN_DANGER = "#ef4444"
        self.BTN_NEUTRAL = "#64748b"
        self.BTN_CODE = "#1e293b"
        self.BTN_INFO = "#0ea5e9"
        self.BTN_IMAGE = "#8b5cf6"
        self.BTN_LINK = "#0d9488"
        self.BTN_ALIGN = "#64748b"
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TLabel", background=self.BG_APP, font=("Segoe UI", 10), foreground="#334155")
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground="#1e293b", background=self.BG_APP)
        style.configure("PanelHeader.TLabel", font=("Segoe UI", 14, "bold"), foreground="#1e293b", background=self.BG_PANEL)
        style.configure("Treeview", rowheight=30, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

        # --- TABS ---
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Editor
        self.tab_editor = tk.Frame(self.notebook, bg=self.BG_READONLY)
        self.notebook.add(self.tab_editor, text="  📝 Editor  ")
        self._init_editor_tab()

        # Tab 2: Manage Articles
        self.tab_manage = tk.Frame(self.notebook, bg=self.BG_PANEL)
        self.notebook.add(self.tab_manage, text="  📂 Manage Articles  ")
        self._init_manage_tab()

        # Tab 3: Manage MCQs
        self.tab_mcq = tk.Frame(self.notebook, bg=self.BG_PANEL)
        self.notebook.add(self.tab_mcq, text="  ✅ Manage MCQs  ")
        self._init_mcq_tab()

    # ==========================================
    # TAB 1: EDITOR UI
    # ==========================================
    def _init_editor_tab(self):
        paned = tk.PanedWindow(self.tab_editor, orient=tk.HORIZONTAL, sashwidth=4, bg="#cbd5e1")
        paned.pack(fill=tk.BOTH, expand=True)

        # --- LEFT PANEL ---
        left_main = tk.Frame(paned, bg=self.BG_APP, width=400)
        
        form_wrapper = ScrollableFrame(left_main, bg_color=self.BG_APP)
        form_wrapper.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        left_content = form_wrapper.scrollable_frame 

        bottom_bar = tk.Frame(left_main, bg=self.BG_READONLY, padx=15, pady=15, borderwidth=1, relief="solid")
        bottom_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # --- RIGHT PANEL ---
        right_main = tk.Frame(paned, bg=self.BG_PANEL, padx=20, pady=20)

        paned.add(left_main, minsize=350)
        paned.add(right_main, minsize=400)

        # === LEFT PANEL (Form) ===
        ttk.Label(left_content, text="Article Metadata", style="Header.TLabel").pack(anchor="w", pady=(0, 15))
        
        tk.Button(left_content, text="Reset Form / New Article", bg=self.BTN_NEUTRAL, fg="white", relief="flat", padx=10, pady=5, command=self.clear_form).pack(fill=tk.X, pady=(0,20))

        def add_field(label, tooltip):
            frame = tk.Frame(left_content, bg=self.BG_APP)
            frame.pack(anchor="w", fill=tk.X, pady=(5, 0))
            ttk.Label(frame, text=label).pack(side=tk.LEFT)
            lbl = tk.Label(frame, text="ⓘ", bg=self.BG_APP, fg=self.BTN_PRIMARY, font=("Segoe UI", 10), cursor="hand2")
            lbl.pack(side=tk.LEFT, padx=5)
            CreateToolTip(lbl, tooltip)
            return frame

        add_field("Paste YouTube Iframe (Optional):", "Copy embed code from YouTube. Leave blank for text-only articles.")
        self.txt_youtube = tk.Text(left_content, height=3, font=("Consolas", 9), wrap=tk.WORD, borderwidth=1, relief="solid")
        self.txt_youtube.pack(fill=tk.X, pady=(2, 10))
        self.txt_youtube.bind('<KeyRelease>', self.parse_video_id)

        self.var_video_id = tk.StringVar()
        tk.Entry(left_content, textvariable=self.var_video_id, state="readonly", bg=self.BG_READONLY, font=("Consolas", 9)).pack(fill=tk.X, pady=(0, 15))

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

        # === BOTTOM BAR (Fixed Publish Button) ===
        tk.Button(bottom_bar, text="💾 PUBLISH ARTICLE", bg=self.BTN_SUCCESS, fg="white", font=("Segoe UI", 11, "bold"), pady=8, relief="flat", cursor="hand2", command=self.publish_article).pack(fill=tk.X)

        # === RIGHT PANEL (Editor) ===
        ttk.Label(right_main, text="Content Editor", style="PanelHeader.TLabel", background=self.BG_PANEL).pack(anchor="w", pady=(0, 10))
        
        toolbar_frame = tk.Frame(right_main, bg=self.BG_APP, padx=5, pady=5, relief="flat")
        toolbar_frame.pack(fill=tk.X, pady=(0, 10))

        def make_btn(parent, text, cmd, bg=self.BTN_PRIMARY, fg="white", tip=None):
            btn = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, relief="flat", padx=10, pady=4, font=("Segoe UI", 9))
            btn.pack(side=tk.LEFT, padx=3, pady=2)
            if tip: CreateToolTip(btn, tip)

        make_btn(toolbar_frame, "H2", lambda: self.wrap_text('<h2 class="article-h2">', '</h2>'), tip="Insert Heading 2")
        make_btn(toolbar_frame, "H3", lambda: self.wrap_text('<h3 class="article-h3">', '</h3>'), tip="Insert Heading 3")
        make_btn(toolbar_frame, "¶", lambda: self.wrap_text('<p class="article-text">', '</p>'), tip="Paragraph")
        make_btn(toolbar_frame, "🔗 Link", self.insert_link, bg=self.BTN_LINK, tip="Insert Link on selected text")
        make_btn(toolbar_frame, "• List", self.insert_list, tip="Insert List")
        
        tk.Frame(toolbar_frame, width=1, bg="#cbd5e1").pack(side=tk.LEFT, fill=tk.Y, padx=5) # Spacer
        make_btn(toolbar_frame, "{ } Code", self.insert_code_block, bg=self.BTN_CODE, tip="Code Block")
        make_btn(toolbar_frame, "ℹ️ Info", self.insert_callout, bg=self.BTN_INFO, tip="Info Box")
        make_btn(toolbar_frame, "🖼️ Image", self.prompt_image_source, bg=self.BTN_IMAGE, tip="Insert Image")
        
        tk.Frame(toolbar_frame, width=1, bg="#cbd5e1").pack(side=tk.LEFT, fill=tk.Y, padx=5) # Spacer
        make_btn(toolbar_frame, "L", lambda: self.wrap_alignment('left'), bg=self.BTN_ALIGN, tip="Align Left")
        make_btn(toolbar_frame, "C", lambda: self.wrap_alignment('center'), bg=self.BTN_ALIGN, tip="Align Center")
        make_btn(toolbar_frame, "R", lambda: self.wrap_alignment('right'), bg=self.BTN_ALIGN, tip="Align Right")

        self.editor = scrolledtext.ScrolledText(right_main, font=("Consolas", 11), wrap=tk.WORD, undo=True, padx=15, pady=15, borderwidth=1, relief="solid")
        self.editor.pack(fill=tk.BOTH, expand=True)
        self.editor.insert(tk.END, "\n")

    # ==========================================
    # TAB 2: MANAGE ARTICLES UI
    # ==========================================
    def _init_manage_tab(self):
        top_frame = tk.Frame(self.tab_manage, bg=self.BG_PANEL, pady=20, padx=20)
        top_frame.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(top_frame, text="Manage Articles", style="PanelHeader.TLabel", background=self.BG_PANEL).pack(side=tk.LEFT)
        tk.Button(top_frame, text="🔄 Refresh", command=self.load_articles_list, relief="flat", bg=self.BG_READONLY, padx=10).pack(side=tk.RIGHT)

        btn_frame = tk.Frame(self.tab_manage, bg=self.BG_PANEL, pady=20, padx=20)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Button(btn_frame, text="✏️ EDIT SELECTED", bg=self.BTN_PRIMARY, fg="white", font=("Segoe UI", 10, "bold"), padx=20, pady=10, relief="flat", command=self.edit_selected).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="🗑️ DELETE SELECTED", bg=self.BTN_DANGER, fg="white", font=("Segoe UI", 10, "bold"), padx=20, pady=10, relief="flat", command=self.delete_selected).pack(side=tk.LEFT, padx=5)

        list_frame = tk.Frame(self.tab_manage, bg=self.BG_PANEL)
        list_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.tree = ttk.Treeview(list_frame, columns=("Date", "Title", "Slug"), show='headings', height=20)
        self.tree.heading("Date", text="Date")
        self.tree.heading("Title", text="Title")
        self.tree.heading("Slug", text="Slug (ID)")
        self.tree.column("Date", width=120)
        self.tree.column("Title", width=400)
        self.tree.column("Slug", width=300)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.load_articles_list()

    # ==========================================
    # TAB 3: MANAGE MCQS (NEW & ENHANCED)
    # ==========================================
    def _init_mcq_tab(self):
        paned = tk.PanedWindow(self.tab_mcq, orient=tk.HORIZONTAL, sashwidth=4, bg="#cbd5e1")
        paned.pack(fill=tk.BOTH, expand=True)

        # --- LEFT PANEL (FORM) ---
        left_main = tk.Frame(paned, bg=self.BG_APP, width=450)
        
        form_wrapper = ScrollableFrame(left_main, bg_color=self.BG_APP)
        form_wrapper.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        mcq_form = form_wrapper.scrollable_frame 
        
        # --- RIGHT PANEL (LIST) ---
        right_main = tk.Frame(paned, bg=self.BG_PANEL)

        paned.add(left_main, minsize=400)
        paned.add(right_main, minsize=500)

        # === MCQ FORM HEADER ===
        ttk.Label(mcq_form, text="MCQ Editor", style="Header.TLabel").pack(anchor="w", pady=(0, 15))
        
        # Action Buttons
        btn_box = tk.Frame(mcq_form, bg=self.BG_APP)
        btn_box.pack(fill=tk.X, pady=(0, 15))
        
        tk.Button(btn_box, text="Reset Form (New Set)", command=self.reset_full_mcq_form, bg=self.BTN_NEUTRAL, fg="white", relief="flat", pady=5).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_box, text="💾 SAVE QUESTION", command=self.save_mcq, bg=self.BTN_SUCCESS, fg="white", relief="flat", font=("Segoe UI", 9, "bold"), pady=5).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        # Status Label (Feedback without popup)
        self.lbl_mcq_status = tk.Label(mcq_form, text="", bg=self.BG_APP, fg=self.BTN_SUCCESS, font=("Segoe UI", 9, "bold"))
        self.lbl_mcq_status.pack(anchor="w", pady=(0, 5))

        # Variables
        self.mcq_var_id = tk.StringVar()
        self.mcq_var_cat = tk.StringVar(value="Salesforce Agentforce") # Title/Category
        self.mcq_var_tag = tk.StringVar(value="Salesforce")          # Broader Tag
        self.mcq_var_set = tk.IntVar(value=1)
        self.mcq_var_desc = tk.StringVar(value="Practice questions for this set.") # Set Description
        self.mcq_var_image_url = tk.StringVar()
        
        # Multiple correct flags
        self.mcq_var_correct_flags = [tk.BooleanVar() for _ in range(5)]
        self.mcq_opts = [tk.StringVar() for _ in range(5)]

        # 1. Category (Title) & Tag & Set
        row1 = tk.Frame(mcq_form, bg=self.BG_APP)
        row1.pack(fill=tk.X, pady=5)
        
        # Col 1: Category (Title)
        f_cat = tk.Frame(row1, bg=self.BG_APP)
        f_cat.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(f_cat, text="Card Title:", bg=self.BG_APP, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Entry(f_cat, textvariable=self.mcq_var_cat, width=20, font=("Segoe UI", 10)).pack(fill=tk.X, padx=(0, 5))

        # Col 2: Tag
        f_tag = tk.Frame(row1, bg=self.BG_APP)
        f_tag.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(f_tag, text="Card Tag:", bg=self.BG_APP, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Entry(f_tag, textvariable=self.mcq_var_tag, width=15, font=("Segoe UI", 10)).pack(fill=tk.X, padx=(0, 5))

        # Col 3: Set
        f_set = tk.Frame(row1, bg=self.BG_APP)
        f_set.pack(side=tk.LEFT)
        tk.Label(f_set, text="Set #:", bg=self.BG_APP, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Spinbox(f_set, textvariable=self.mcq_var_set, from_=1, to=100, width=5, font=("Segoe UI", 10)).pack()

        # 2. Set Description (NEW)
        tk.Label(mcq_form, text="Set Description (On Card):", bg=self.BG_APP, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10, 0))
        tk.Entry(mcq_form, textvariable=self.mcq_var_desc, font=("Segoe UI", 10), bg="white").pack(fill=tk.X, pady=(2, 5))

        # 3. Image URL
        tk.Label(mcq_form, text="Image URL (Optional):", bg=self.BG_APP, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10, 0))
        tk.Entry(mcq_form, textvariable=self.mcq_var_image_url, font=("Segoe UI", 10), bg="white").pack(fill=tk.X, pady=(2, 5))

        # 4. Question Text
        tk.Label(mcq_form, text="Question:", bg=self.BG_APP, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10, 0))
        self.txt_mcq_question = tk.Text(mcq_form, height=5, font=("Segoe UI", 10), wrap=tk.WORD, borderwidth=1, relief="solid")
        self.txt_mcq_question.pack(fill=tk.X, pady=5)

        # 5. Options
        tk.Label(mcq_form, text="Options (Check box if Correct):", bg=self.BG_APP, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10, 5))
        
        opt_labels = ["A", "B", "C", "D", "E"]
        for i in range(5):
            f = tk.Frame(mcq_form, bg=self.BG_APP)
            f.pack(fill=tk.X, pady=2)
            
            # Checkbutton for multiple correct answers
            cb = tk.Checkbutton(f, variable=self.mcq_var_correct_flags[i], bg=self.BG_APP, cursor="hand2")
            cb.pack(side=tk.LEFT)
            CreateToolTip(cb, "Mark as Correct")
            
            tk.Label(f, text=f"{opt_labels[i]}.", bg=self.BG_APP, width=3, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
            tk.Entry(f, textvariable=self.mcq_opts[i], relief="solid", borderwidth=1, font=("Segoe UI", 10)).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 6. Explanation
        tk.Label(mcq_form, text="Explanation (Shown after answering):", bg=self.BG_APP, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(15, 0))
        self.txt_mcq_expl = tk.Text(mcq_form, height=4, font=("Segoe UI", 10), wrap=tk.WORD, borderwidth=1, relief="solid")
        self.txt_mcq_expl.pack(fill=tk.X, pady=5)

        # === MCQ LIST ===
        top_bar = tk.Frame(right_main, bg=self.BG_PANEL, padx=10, pady=10)
        top_bar.pack(fill=tk.X)
        
        tk.Button(top_bar, text="🔄 Reload List", command=self.load_mcq_list, relief="flat", bg=self.BG_READONLY).pack(side=tk.RIGHT)
        
        tk.Button(top_bar, text="✏️ Edit", command=self.edit_mcq, bg=self.BTN_PRIMARY, fg="white", relief="flat", padx=15).pack(side=tk.LEFT, padx=5)
        tk.Button(top_bar, text="🗑️ Delete", command=self.delete_mcq, bg=self.BTN_DANGER, fg="white", relief="flat", padx=15).pack(side=tk.LEFT, padx=5)

        # Treeview
        columns = ("Set", "Tag", "Title", "Question")
        self.tree_mcq = ttk.Treeview(right_main, columns=columns, show='headings', height=25)
        
        self.tree_mcq.heading("Set", text="Set")
        self.tree_mcq.heading("Tag", text="Tag")
        self.tree_mcq.heading("Title", text="Title")
        self.tree_mcq.heading("Question", text="Question Preview")
        
        self.tree_mcq.column("Set", width=40, anchor="center")
        self.tree_mcq.column("Tag", width=80)
        self.tree_mcq.column("Title", width=120)
        self.tree_mcq.column("Question", width=350)
        
        scrollbar_mcq = ttk.Scrollbar(right_main, orient="vertical", command=self.tree_mcq.yview)
        self.tree_mcq.configure(yscrollcommand=scrollbar_mcq.set)
        
        self.tree_mcq.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar_mcq.pack(side=tk.RIGHT, fill=tk.Y, pady=10)

        self.load_mcq_list()


    # ==========================================
    # LOGIC METHODS (ARTICLE)
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

    def insert_link(self):
        url = simpledialog.askstring("Insert Link", "Enter the URL:")
        if not url: return
        
        link_html_start = f'<a href="{url}" class="article-link" target="_blank">'
        link_html_end = '</a>'
        
        try:
            sel_start = self.editor.index(tk.SEL_FIRST)
            sel_end = self.editor.index(tk.SEL_LAST)
            selected_text = self.editor.get(sel_start, sel_end)
            self.editor.delete(sel_start, sel_end)
            self.editor.insert(sel_start, f"{link_html_start}{selected_text}{link_html_end}")
        except tk.TclError:
            self.editor.insert(tk.INSERT, f"{link_html_start}Link Text{link_html_end}")

    def insert_list(self):
        self.editor.insert(tk.INSERT, '\n<ul class="article-list">\n    <li>Item 1</li>\n    <li>Item 2</li>\n</ul>\n')

    def insert_code_block(self):
        self.editor.insert(tk.INSERT, '\n<pre class="code-block language-apex"><code>\n// Your code here\n</code></pre>\n')

    def insert_callout(self):
        self.editor.insert(tk.INSERT, '\n<div class="callout info">\n    <span class="callout-title">ℹ️ Note</span>\n    <p style="margin:0;">Note text...</p>\n</div>\n')

    # --- IMAGE LOGIC ---
    def prompt_image_source(self):
        popup = tk.Toplevel(self.root)
        popup.title("Insert Image")
        popup.geometry("300x160")
        popup.configure(bg=self.BG_APP)
        
        ttk.Label(popup, text="Choose Image Source:", font=("Segoe UI", 10, "bold"), background=self.BG_APP).pack(pady=10)
        
        def from_file():
            popup.destroy()
            self._insert_image_file()
            
        def from_url():
            popup.destroy()
            self._insert_image_url()
            
        btn_style = {"bg":self.BTN_PRIMARY, "fg":"white", "relief":tk.FLAT, "pady":5}
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

    # --- DATA MANAGEMENT (ARTICLES) ---

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
        self.var_placeholder.set("") 
        self.txt_youtube.delete("1.0", tk.END)
        self.txt_desc.delete("1.0", tk.END)
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", "\n")
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
        self.var_placeholder.set(article.get('placeholder_text', ''))
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
        
        # 2. Delete HTML & Images
        html_path = os.path.join(TEMPLATE_DIR, f"{slug}.html")
        if os.path.exists(html_path):
            try:
                with open(html_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                images = re.findall(r"filename='images/([^']+)'", content)
                for img in images:
                    img_path = os.path.join('static', 'images', img)
                    if os.path.exists(img_path):
                        os.remove(img_path)

                os.remove(html_path)
            except Exception as e:
                messagebox.showerror("Error", f"Could not delete file: {e}")
        
        self.load_articles_list()
        messagebox.showinfo("Deleted", "Article removed successfully.")

    def publish_article(self):
        if not self.var_title.get() or not self.var_slug.get():
            messagebox.showerror("Error", "Title and Slug are required!")
            return
        slug = self.var_slug.get().strip()
        data = {
            "title": self.var_title.get(),
            "slug": slug,
            "video_id": self.var_video_id.get(),
            "placeholder_text": self.var_placeholder.get().strip(),
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

    # ==========================================
    # LOGIC METHODS (MCQ) - UPDATED FOR MULTIPLE CORRECT, IMAGES, TAGS & DESCRIPTION
    # ==========================================
    def load_mcq_list(self):
        for row in self.tree_mcq.get_children(): self.tree_mcq.delete(row)
        if not os.path.exists(MCQS_DB): return
        
        try:
            with open(MCQS_DB, 'r', encoding='utf-8') as f:
                mcqs = json.load(f)
        except: return

        # Sort by Category, then Set, then ID
        mcqs.sort(key=lambda x: (x.get('category', ''), x.get('set_id', 0)))

        for q in mcqs:
            # Display Set, Tag, Title(Category), Question
            tag = q.get('tag', 'General')
            cat = q.get('category', 'Uncategorized')
            self.tree_mcq.insert("", tk.END, iid=q.get('id'), values=(q.get('set_id'), tag, cat, q.get('question')))

    # Only resets specific fields (keeps Category, Tag, Set & Description)
    def clear_question_fields_only(self):
        self.mcq_var_id.set("")
        self.mcq_var_image_url.set("") 
        
        # Reset checkboxes
        for v in self.mcq_var_correct_flags:
            v.set(False)
            
        self.txt_mcq_question.delete("1.0", tk.END)
        self.txt_mcq_expl.delete("1.0", tk.END)
        for v in self.mcq_opts: v.set("")

    # Full reset for "Reset Form" button
    def reset_full_mcq_form(self):
        self.mcq_var_cat.set("Salesforce Agentforce")
        self.mcq_var_tag.set("Salesforce")
        self.mcq_var_desc.set("Practice questions for this set.")
        self.mcq_var_set.set(1)
        self.clear_question_fields_only()
        self.lbl_mcq_status.config(text="Form Reset.", fg="black")

    def save_mcq(self):
        # 1. Validation
        q_text = self.txt_mcq_question.get("1.0", tk.END).strip()
        options = [v.get().strip() for v in self.mcq_opts if v.get().strip()]
        
        if not q_text:
            messagebox.showerror("Error", "Question text cannot be empty.")
            return
        if len(options) < 2:
            messagebox.showerror("Error", "Please provide at least 2 options.")
            return

        # 2. Determine Correct Answers
        correct_list = []
        for i in range(5):
            if self.mcq_var_correct_flags[i].get() and self.mcq_opts[i].get().strip():
                correct_list.append(self.mcq_opts[i].get().strip())
        
        if not correct_list:
            messagebox.showerror("Error", "Please mark at least one option as correct.")
            return

        # 3. Generate ID if new
        q_id = self.mcq_var_id.get()
        if not q_id:
            q_id = uuid.uuid4().hex[:8]

        current_set = self.mcq_var_set.get()
        current_cat = self.mcq_var_cat.get().strip()
        current_tag = self.mcq_var_tag.get().strip()
        current_desc = self.mcq_var_desc.get().strip()

        data = {
            "id": q_id,
            "set_id": current_set,
            "category": current_cat, # Title
            "tag": current_tag,       # Tag
            "description": current_desc, # Description (Set level)
            "question": q_text,
            "image_url": self.mcq_var_image_url.get().strip(),
            "options": options,
            "correct": correct_list,
            "explanation": self.txt_mcq_expl.get("1.0", tk.END).strip()
        }

        # 4. Load & Update JSON
        if os.path.exists(MCQS_DB):
            try:
                with open(MCQS_DB, 'r', encoding='utf-8') as f:
                    mcqs = json.load(f)
            except: mcqs = []
        else:
            mcqs = []

        idx = next((i for i, item in enumerate(mcqs) if item["id"] == q_id), -1)
        if idx >= 0:
            mcqs[idx] = data
        else:
            mcqs.append(data)

        # SYNC: Update all other questions in the same set with new Tag/Description
        for q in mcqs:
            if q.get('set_id') == current_set and q.get('category') == current_cat:
                q['tag'] = current_tag
                q['description'] = current_desc

        with open(MCQS_DB, 'w', encoding='utf-8') as f:
            json.dump(mcqs, f, indent=2)

        # 5. UI Updates
        self.load_mcq_list()
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.lbl_mcq_status.config(text=f"✅ Saved & Synced! ({timestamp})", fg=self.BTN_SUCCESS)
        self.clear_question_fields_only()
        self.txt_mcq_question.focus_set()

    def edit_mcq(self):
        sel = self.tree_mcq.selection()
        if not sel: return
        q_id = sel[0]

        with open(MCQS_DB, 'r', encoding='utf-8') as f:
            mcqs = json.load(f)
            
        found = next((q for q in mcqs if q['id'] == q_id), None)
        if not found: return

        # Populate Form
        self.clear_question_fields_only()
        self.mcq_var_id.set(found['id'])
        self.mcq_var_cat.set(found.get('category', ''))
        self.mcq_var_tag.set(found.get('tag', 'Salesforce')) 
        self.mcq_var_desc.set(found.get('description', 'Practice questions...'))
        self.mcq_var_set.set(found['set_id'])
        self.mcq_var_image_url.set(found.get('image_url', ''))
        self.txt_mcq_question.insert("1.0", found['question'])
        self.txt_mcq_expl.insert("1.0", found.get('explanation', ''))

        opts = found['options']
        for i, txt in enumerate(opts):
            if i < 5: self.mcq_opts[i].set(txt)
        
        # Handle correct checkboxes
        correct_data = found.get('correct')
        if isinstance(correct_data, str):
            correct_data = [correct_data]
        
        if correct_data:
            for i, txt in enumerate(opts):
                if txt in correct_data:
                    self.mcq_var_correct_flags[i].set(True)
            
        self.lbl_mcq_status.config(text="Editing Question...", fg="blue")

    def delete_mcq(self):
        sel = self.tree_mcq.selection()
        if not sel: return
        q_id = sel[0]

        if not messagebox.askyesno("Confirm", "Delete this question?"): return

        with open(MCQS_DB, 'r', encoding='utf-8') as f:
            mcqs = json.load(f)
        
        new_mcqs = [q for q in mcqs if q['id'] != q_id]
        
        with open(MCQS_DB, 'w', encoding='utf-8') as f:
            json.dump(new_mcqs, f, indent=2)
            
        self.load_mcq_list()
        self.clear_question_fields_only()
        self.lbl_mcq_status.config(text="Question Deleted.", fg="red")

if __name__ == "__main__":
    root = tk.Tk()
    app = ArticleAutomator(root)
    root.mainloop()