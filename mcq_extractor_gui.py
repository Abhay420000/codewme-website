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
    # These are capable of handling the file uploads and generating JSON.
    supported_models = [
        # Latest Experimental & High Performance
        "models/gemini-2.0-flash-exp",
        "models/gemini-2.0-flash",
        "models/gemini-2.0-flash-001",
        "models/gemini-2.0-flash-lite",
        "models/gemini-2.0-flash-lite-preview-02-05",
        "models/gemini-2.0-flash-lite-preview",
        "models/gemini-2.0-flash-lite-001",
        "models/gemini-exp-1206",
        "models/deep-research-pro-preview-12-2025",
        
        # Gemini 2.5 Series
        "models/gemini-2.5-flash",
        "models/gemini-2.5-pro",
        "models/gemini-2.5-flash-lite",
        "models/gemini-2.5-flash-preview-09-2025",
        "models/gemini-2.5-flash-lite-preview-09-2025",
        "models/gemini-2.5-computer-use-preview-10-2025",
        
        # Gemini 3 Preview (Future Proofing)
        "models/gemini-3-pro-preview",
        
        # Latest Aliases
        "models/gemini-flash-latest",
        "models/gemini-flash-lite-latest",
        "models/gemini-pro-latest",
        
        # Standard Pro/Flash/Legacy
        "models/gemini-1.5-pro",
        "models/gemini-1.5-flash",
        "models/gemini-1.5-flash-8b",
        
        # Robotics/Specialized (Might work for logic)
        "models/gemini-robotics-er-1.5-preview",
        "models/nano-banana-pro-preview",
    ]

    # --- PRIORITY 2: UNSUPPORTED / WRONG MODALITY MODELS ---
    # These are included as requested, but placed last because they will likely 
    # fail on PDF extraction (Gemma = text only, Imagen = image gen, Embedding = vectors).
    unsupported_models = [
        # Gemma (Text Only - Often fails file upload headers)
        "models/gemma-3-1b-it",
        "models/gemma-3-4b-it",
        "models/gemma-3-12b-it",
        "models/gemma-3-27b-it",
        "models/gemma-3n-e4b-it",
        "models/gemma-3n-e2b-it",
        
        # Image/Video Generation (Will not output Text/JSON)
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
        
        # Audio / TTS Specific (Wrong modality for PDF reading)
        "models/gemini-2.5-flash-preview-tts",
        "models/gemini-2.5-pro-preview-tts",
        "models/gemini-2.5-flash-native-audio-latest",
        "models/gemini-2.5-flash-native-audio-preview-09-2025",
        
        # Embeddings (Cannot generate text)
        "models/embedding-gecko-001",
        "models/embedding-001",
        "models/text-embedding-004",
        "models/gemini-embedding-exp-03-07",
        "models/gemini-embedding-exp",
        "models/gemini-embedding-001",
        
        # Other
        "models/aqa"
    ]
    
    # Combine lists: Supported first, Unsupported last
    all_models = supported_models + unsupported_models
            
    return all_models

def build_model_queue(available_models):
    """
    Builds the execution queue.
    """
    queue = []
    for m in available_models:
        # Determine strict JSON mode support (Gemini usually supports it, Gemma/Imagen do not)
        is_gemini = "gemini" in m.lower() and "image" not in m.lower() and "audio" not in m.lower()
        
        # Sleep logic: Flash is fast (2s), Pro is slow (10s), Others (2s)
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
    Catches '400 Modality' errors (for Gemma/Imagen) and moves to next.
    """
    
    # 1. Upload File (Required for Image PDFs)
    file_ref = None
    try:
        file_ref = genai.upload_file(file_path)
        # Wait for ACTIVE
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

    # 2. Try Models
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

            # Attempt to generate content with the FILE
            # This will naturally fail for text-only models (Gemma) or image-gen models (Imagen)
            # The Try/Except block will catch it and move to the next model.
            response = model.generate_content([file_ref, prompt])
            
            # Parse Response
            text_resp = clean_json_text(response.text) if not config["json_mode"] else response.text
            data = json.loads(text_resp)
            
            # Success! Delete file and return
            try: genai.delete_file(file_ref.name)
            except: pass
            
            time.sleep(config["sleep"])
            return data

        except Exception as e:
            err_msg = str(e).lower()
            
            # --- ERROR HANDLING ---
            # 1. Modality Error (Gemma/Imagen vs PDF)
            if "400" in err_msg and ("modality" in err_msg or "multimodal" in err_msg):
                 # Skip quietly (expected for unsupported models)
                 continue
            
            # 2. Method Not Found (Embeddings don't have generateContent)
            elif "attributeerror" in err_msg or "not found" in err_msg:
                continue

            # 3. Quota Error (Run out of free tier)
            elif "429" in err_msg or "quota" in err_msg:
                log_func(f"⚠️ Quota hit on {config['name']}, switching...")
                continue 
            
            # 4. Other Errors
            else:
                log_func(f"⚠️ Error on {config['name']}: {e}")
                
    # If all models fail
    try: genai.delete_file(file_ref.name)
    except: pass
    return []

# --- GUI APPLICATION ---

class MCQExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto PDF to MCQ Extractor (Max Quota)")
        self.root.geometry("750x800")
        
        self.pdf_path = tk.StringVar()
        self.json_path = tk.StringVar(value="mcqs.json")
        
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
        ttk.Label(frame_top, text="PDF to MCQ Automator", font=("Arial", 16, "bold")).pack(side="left")
        self.lbl_api_status = ttk.Label(frame_top, text="Checking API Key...", foreground="gray")
        self.lbl_api_status.pack(side="right")

        frame_files = ttk.LabelFrame(self.root, text="Files", padding=10)
        frame_files.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(frame_files, text="Select PDF Input", command=self.browse_pdf).grid(row=0, column=0, pady=5, sticky="w")
        ttk.Entry(frame_files, textvariable=self.pdf_path, state="readonly", width=50).grid(row=0, column=1, padx=5, sticky="ew")
        
        ttk.Button(frame_files, text="Select JSON Output", command=self.browse_json).grid(row=1, column=0, pady=5, sticky="w")
        ttk.Entry(frame_files, textvariable=self.json_path, width=50).grid(row=1, column=1, padx=5, sticky="ew")
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

    def browse_json(self):
        f = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")], initialfile="mcqs.json")
        if f: self.json_path.set(f)

    def start_thread(self):
        if not self.pdf_path.get():
            messagebox.showerror("Error", "Please select a PDF file first.")
            return
        self.is_running = True
        self.start_btn.config(state="disabled", text="Processing...")
        threading.Thread(target=self.run_process, daemon=True).start()

    def run_process(self):
        try:
            genai.configure(api_key=self.env_api_key)
            self.log("Initializing Model Registry...")
            models = get_available_models()
            model_queue = build_model_queue(models)
            self.log(f"Queued {len(model_queue)} models (Vision First, Unsupported Last).")

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
            
            out_file = self.json_path.get()
            final_data = []
            if os.path.exists(out_file):
                try:
                    with open(out_file, "r", encoding="utf-8") as f: final_data = json.load(f)
                    self.log(f"Loaded {len(final_data)} previous questions.")
                except: pass
            
            new_q_count = 0
            
            for i, chunk_path in enumerate(chunk_files):
                self.log(f"Processing Chunk {i+1}...")
                extracted_list = extract_chunk(chunk_path, model_queue, self.log)
                
                if extracted_list:
                    self.log(f"  > Success! {len(extracted_list)} questions found.")
                    for q in extracted_list:
                        set_offset = new_q_count // 20
                        current_set_id = self.start_set_id.get() + set_offset
                        formatted_q = {
                            "id": str(uuid.uuid4())[:8],
                            "set_id": current_set_id,
                            "category": self.category.get(),
                            "tag": self.tag.get(),
                            "description": self.description.get(),
                            "question": q.get("question", "Unknown"),
                            "options": q.get("options", []),
                            "correct": q.get("correct", []),
                            "explanation": q.get("explanation", "")
                        }
                        final_data.append(formatted_q)
                        new_q_count += 1
                
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(final_data, f, indent=2, ensure_ascii=False)
                
                try: os.remove(chunk_path)
                except: pass
                
                self.progress["value"] = i + 1
                self.root.update_idletasks()

            self.log("--------------------------------")
            self.log(f"COMPLETE. Total: {len(final_data)} questions.")
            messagebox.showinfo("Success", f"Extraction Complete!\nSaved to: {out_file}")

        except Exception as e:
            self.log(f"CRITICAL ERROR: {e}")
            messagebox.showerror("Error", str(e))
        finally:
            self.start_btn.config(state="normal", text="▶ START EXTRACTION")
            self.is_running = False

if __name__ == "__main__":
    root = tk.Tk()
    app = MCQExtractorApp(root)
    root.mainloop()