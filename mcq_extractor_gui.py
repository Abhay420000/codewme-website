import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import google.generativeai as genai
from pypdf import PdfReader, PdfWriter
import json
import os
import time
import uuid
import re
import sqlite3  # <--- ADDED: Database support

# --- BACKEND LOGIC ---

def get_api_key():
    """Fetches API key strictly from Environment Variable."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    return api_key

def get_available_models():
    """
    Returns the specific list of models provided, prioritized by capability.
    1. Supported (Gemini 2.0/2.5/Pro/Flash - Vision & PDF capable)
    2. Unsupported/Incompatible (Gemma, Embeddings, Imagen, Veo, Audio)
    """
    
    # --- PRIORITY 1: SUPPORTED MODELS (Vision, PDF, Long Context) ---
    supported_models = [
        "models/gemini-2.0-flash-exp",
        "models/gemini-2.0-flash",
        "models/gemini-2.0-flash-001",
        "models/gemini-2.0-flash-lite",
        "models/gemini-2.0-flash-lite-preview-02-05",
        "models/gemini-2.0-flash-lite-preview",
        "models/gemini-2.0-flash-lite-001",
        "models/gemini-exp-1206",
        "models/deep-research-pro-preview-12-2025",
        "models/gemini-2.5-flash",
        "models/gemini-2.5-pro",
        "models/gemini-2.5-flash-lite",
        "models/gemini-2.5-flash-preview-09-2025",
        "models/gemini-2.5-flash-lite-preview-09-2025",
        "models/gemini-2.5-computer-use-preview-10-2025",
        "models/gemini-3-pro-preview",
        "models/gemini-flash-latest",
        "models/gemini-flash-lite-latest",
        "models/gemini-pro-latest",
        "models/gemini-1.5-pro",
        "models/gemini-1.5-flash",
        "models/gemini-1.5-flash-8b",
        "models/gemini-robotics-er-1.5-preview",
        "models/nano-banana-pro-preview",
    ]

    # --- PRIORITY 2: UNSUPPORTED / WRONG MODALITY MODELS ---
    unsupported_models = [
        "models/gemma-3-1b-it",
        "models/gemma-3-4b-it",
        "models/gemma-3-12b-it",
        "models/gemma-3-27b-it",
        "models/gemma-3n-e4b-it",
        "models/gemma-3n-e2b-it",
        "models/gemini-2.0-flash-exp-image-generation",
        "models/gemini-2.5-flash-image-preview",
        "models/gemini-2.5-flash-image",
        "models/gemini-3-pro-image-preview",
        "models/imagen-4.0-generate-preview-06-06",
        "models/imagen-4.0-ultra-generate-preview-06-06",
        "models/imagen-4.0-generate-001",
        "models/imagen-4.0-ultra-generate-001",
        "models/imagen-4.0-fast-generate-001",
        "models/veo-2.0-generate-001",
        "models/veo-3.0-generate-001",
        "models/veo-3.0-fast-generate-001",
        "models/veo-3.1-generate-preview",
        "models/veo-3.1-fast-generate-preview",
        "models/gemini-2.5-flash-preview-tts",
        "models/gemini-2.5-pro-preview-tts",
        "models/gemini-2.5-flash-native-audio-latest",
        "models/gemini-2.5-flash-native-audio-preview-09-2025",
        "models/embedding-gecko-001",
        "models/embedding-001",
        "models/text-embedding-004",
        "models/gemini-embedding-exp-03-07",
        "models/gemini-embedding-exp",
        "models/gemini-embedding-001",
        "models/aqa"
    ]
    
    all_models = supported_models + unsupported_models
    return all_models

def build_model_queue(available_models):
    """
    Builds the execution queue.
    """
    queue = []
    for m in available_models:
        is_gemini = "gemini" in m.lower() and "image" not in m.lower() and "audio" not in m.lower()
        
        if "flash" in m or "gemma" in m:
            sleep_time = 2
        else:
            sleep_time = 10
        
        queue.append({
            "name": m, 
            "json_mode": is_gemini, 
            "sleep": sleep_time
        })
        
    return queue

def clean_json_text(text):
    """Robustly extracts JSON from Markdown or messy text."""
    if not text: return "[]"
    match = re.search(r"```json\s*(.*?)```", text, re.DOTALL)
    if match: return match.group(1)
    
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match: return match.group(0)
    
    return text

def extract_chunk(file_path, model_queue, log_func):
    """
    Uploads file and cycles through models.
    """
    file_ref = None
    try:
        file_ref = genai.upload_file(file_path)
        for _ in range(30):
            check = genai.get_file(file_ref.name)
            if check.state.name == "ACTIVE": break
            if check.state.name == "FAILED": 
                log_func(f"File upload failed: {file_path}")
                return []
            time.sleep(1)
    except Exception as e:
        log_func(f"Upload error: {e}")
        return []

    for config in model_queue:
        try:
            generation_config = {}
            if config["json_mode"]:
                generation_config["response_mime_type"] = "application/json"

            model = genai.GenerativeModel(
                model_name=config["name"],
                generation_config=generation_config
            )

            prompt = """
            Extract all multiple-choice questions from this document chunk.
            
            CRITICAL RULES:
            1. If the 'correct' answer is a letter (e.g. 'A'), REPLACE IT with the text of that option.
            2. If correct answer is not written or marked identify it, almost 99.99% times it will be their.
            3. Do not add instructions like 'Choose 2 answers' into the question
            4. Almost 60-70% of times every question will start after the text "1 of 60.", "2 of 60.", ...
               you need to properly identify and include the full question.
            5. Output a JSON list of objects with this schema:
            [{
              "id": null, 
              "question": "Question text",
              "options": ["Option A", "Option B"],
              "correct": ["Correct Option Text"],
              "explanation": "Text or null"
            }]
            """
            
            if not config["json_mode"]:
                prompt += "\nReturn ONLY raw JSON. No markdown."

            response = model.generate_content([file_ref, prompt])
            text_resp = clean_json_text(response.text) if not config["json_mode"] else response.text
            data = json.loads(text_resp)
            
            try: genai.delete_file(file_ref.name)
            except: pass
            
            time.sleep(config["sleep"])
            return data

        except Exception as e:
            err_msg = str(e).lower()
            if "400" in err_msg and ("modality" in err_msg or "multimodal" in err_msg):
                 continue
            elif "attributeerror" in err_msg or "not found" in err_msg:
                continue
            elif "429" in err_msg or "quota" in err_msg:
                log_func(f"⚠️ Quota hit on {config['name']}, switching...")
                continue 
            else:
                log_func(f"⚠️ Error on {config['name']}: {e}")
                
    try: genai.delete_file(file_ref.name)
    except: pass
    return []

# --- GUI APPLICATION ---

class MCQExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto PDF to MCQ Extractor (Database Edition)")
        self.root.geometry("750x800")
        
        self.pdf_path = tk.StringVar()
        self.db_path = tk.StringVar(value="mcqs.db") # <--- CHANGED: Default to .db
        
        self.start_set_id = tk.IntVar(value=1)
        self.category = tk.StringVar(value="General Knowledge")
        self.tag = tk.StringVar(value="Exam")
        self.description = tk.StringVar(value="Extracted Questions")
        
        self.env_api_key = get_api_key()
        self.is_running = False
        self._build_ui()
        self._check_api_key()

    def _check_api_key(self):
        if not self.env_api_key:
            messagebox.showerror("Error", "CRITICAL: 'GEMINI_API_KEY' not found in environment variables.")
            self.start_btn.config(state="disabled")
        else:
            masked = self.env_api_key[:4] + "*" * (len(self.env_api_key)-8) + self.env_api_key[-4:]
            self.lbl_api_status.config(text=f"API Key Active: {masked}", foreground="green")

    def _build_ui(self):
        frame_top = ttk.Frame(self.root, padding=10)
        frame_top.pack(fill="x")
        ttk.Label(frame_top, text="PDF to Database Automator", font=("Arial", 16, "bold")).pack(side="left")
        self.lbl_api_status = ttk.Label(frame_top, text="Checking API Key...", foreground="gray")
        self.lbl_api_status.pack(side="right")

        frame_files = ttk.LabelFrame(self.root, text="Files", padding=10)
        frame_files.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(frame_files, text="Select PDF Input", command=self.browse_pdf).grid(row=0, column=0, pady=5, sticky="w")
        ttk.Entry(frame_files, textvariable=self.pdf_path, state="readonly", width=50).grid(row=0, column=1, padx=5, sticky="ew")
        
        # <--- CHANGED: Label and Command for Database
        ttk.Button(frame_files, text="Select Database Output", command=self.browse_db).grid(row=1, column=0, pady=5, sticky="w")
        ttk.Entry(frame_files, textvariable=self.db_path, width=50).grid(row=1, column=1, padx=5, sticky="ew")
        frame_files.columnconfigure(1, weight=1)

        frame_meta = ttk.LabelFrame(self.root, text="Metadata Configuration", padding=10)
        frame_meta.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(frame_meta, text="Start Set ID:").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(frame_meta, textvariable=self.start_set_id, width=10).grid(row=0, column=1, sticky="w", pady=2)
        
        ttk.Label(frame_meta, text="Category:").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(frame_meta, textvariable=self.category, width=30).grid(row=1, column=1, sticky="w", pady=2)
        
        ttk.Label(frame_meta, text="Tag:").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(frame_meta, textvariable=self.tag, width=30).grid(row=2, column=1, sticky="w", pady=2)
        
        ttk.Label(frame_meta, text="Description:").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Entry(frame_meta, textvariable=self.description, width=30).grid(row=3, column=1, sticky="w", pady=2)

        frame_logs = ttk.Frame(self.root, padding=10)
        frame_logs.pack(fill="both", expand=True)

        self.start_btn = ttk.Button(frame_logs, text="▶ START EXTRACTION", command=self.start_thread)
        self.start_btn.pack(fill="x", pady=5)

        self.progress = ttk.Progressbar(frame_logs, mode='determinate')
        self.progress.pack(fill="x", pady=5)

        self.log_area = scrolledtext.ScrolledText(frame_logs, height=15, state="disabled", font=("Consolas", 9))
        self.log_area.pack(fill="both", expand=True)

    def log(self, msg):
        self.log_area.config(state="normal")
        self.log_area.insert("end", f"> {msg}\n")
        self.log_area.see("end")
        self.log_area.config(state="disabled")

    def browse_pdf(self):
        f = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if f: self.pdf_path.set(f)

    # <--- CHANGED: Logic for selecting .db files
    def browse_db(self):
        f = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("SQLite DB", "*.db")], initialfile="mcqs.db")
        if f: self.db_path.set(f)

    def start_thread(self):
        if not self.pdf_path.get():
            messagebox.showerror("Error", "Please select a PDF file first.")
            return
        self.is_running = True
        self.start_btn.config(state="disabled", text="Processing...")
        threading.Thread(target=self.run_process, daemon=True).start()

    def run_process(self):
        conn = None
        try:
            genai.configure(api_key=self.env_api_key)
            self.log("Initializing Model Registry...")
            models = get_available_models()
            model_queue = build_model_queue(models)
            self.log(f"Queued {len(model_queue)} models (Vision First, Unsupported Last).")

            # <--- ADDED: Database Connection Logic
            db_file = self.db_path.get()
            self.log(f"Connecting to database: {db_file}")
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Ensure Table Exists
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS questions (
                    id TEXT PRIMARY KEY,
                    set_id INTEGER,
                    category TEXT,
                    tag TEXT,
                    description TEXT,
                    question TEXT,
                    image_url TEXT,
                    options TEXT,
                    correct TEXT,
                    explanation TEXT
                )
            ''')
            conn.commit()

            self.log("Chunking PDF...")
            reader = PdfReader(self.pdf_path.get())
            total_pages = len(reader.pages)
            chunk_files = []
            CHUNK_SIZE = 10
            
            for i in range(0, total_pages, CHUNK_SIZE):
                writer = PdfWriter()
                end = min(i + CHUNK_SIZE, total_pages)
                for p in range(i, end): writer.add_page(reader.pages[p])
                fname = f"temp_chunk_{i}.pdf"
                with open(fname, "wb") as f: writer.write(f)
                chunk_files.append(fname)
            
            self.progress["maximum"] = len(chunk_files)
            
            new_q_count = 0
            
            for i, chunk_path in enumerate(chunk_files):
                self.log(f"Processing Chunk {i+1}...")
                extracted_list = extract_chunk(chunk_path, model_queue, self.log)
                
                if extracted_list:
                    self.log(f"  > Success! {len(extracted_list)} questions found. Inserting into DB...")
                    
                    for q in extracted_list:
                        set_offset = new_q_count // 20
                        current_set_id = self.start_set_id.get() + set_offset
                        
                        # Prepare Data for SQLite
                        q_id = str(uuid.uuid4())[:8]
                        q_options = json.dumps(q.get("options", [])) # Serialize List
                        q_correct = json.dumps(q.get("correct", [])) # Serialize List
                        
                        try:
                            # <--- CHANGED: Insert into SQLite
                            cursor.execute('''
                                INSERT INTO questions 
                                (id, set_id, category, tag, description, question, image_url, options, correct, explanation)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                q_id,
                                current_set_id,
                                self.category.get(),
                                self.tag.get(),
                                self.description.get(),
                                q.get("question", "Unknown"),
                                "", # image_url
                                q_options,
                                q_correct,
                                q.get("explanation", "")
                            ))
                            new_q_count += 1
                        except Exception as insert_err:
                            self.log(f"  ⚠️ Insert Error: {insert_err}")
                    
                    conn.commit() # Commit after every chunk
                
                try: os.remove(chunk_path)
                except: pass
                
                self.progress["value"] = i + 1
                self.root.update_idletasks()

            self.log("--------------------------------")
            self.log(f"COMPLETE. Total: {new_q_count} questions added to database.")
            messagebox.showinfo("Success", f"Extraction Complete!\nDatabase: {db_file}")

        except Exception as e:
            self.log(f"CRITICAL ERROR: {e}")
            messagebox.showerror("Error", str(e))
        finally:
            if conn: conn.close() # Close DB connection
            self.start_btn.config(state="normal", text="▶ START EXTRACTION")
            self.is_running = False

if __name__ == "__main__":
    root = tk.Tk()
    app = MCQExtractorApp(root)
    root.mainloop()