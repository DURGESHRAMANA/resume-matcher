# ✅ SECTION-WISE RESUME MATCHER (BACKEND FOR VS CODE)
# 🔧 Required installations:
# pip install flask sentence-transformers pdfplumber pymupdf python-docx easyocr torch torchvision torchaudio openpyxl pandas

import os
import re
import pdfplumber
import fitz
import docx
import easyocr
import pandas as pd
from PIL import Image
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file
from sentence_transformers import SentenceTransformer, util
from difflib import SequenceMatcher

app = Flask(__name__)

model = SentenceTransformer('all-MiniLM-L6-v2')
reader = easyocr.Reader(['en'], gpu=True)

UPLOAD_FOLDER = 'temp'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 📄 Extract text from file

def extract_text_from_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.pdf':
        try:
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            if len(text.strip()) < 100:
                raise ValueError("pdfplumber returned too little text.")
        except:
            text = ""
            doc = fitz.open(file_path)
            for page in doc:
                text += page.get_text()
        return text

    elif ext == '.docx':
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])

    elif ext in ['.jpg', '.jpeg', '.png']:
        result = reader.readtext(file_path, detail=0, paragraph=True)
        return " ".join(result)

    elif ext == '.txt':
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    else:
        raise ValueError(f"Unsupported file format: {ext}")

# 🔧 Clean contact info

def remove_contact_info(text):
    text = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "", text)
    text = re.sub(r"\+?\d[\d\-\s]{8,}", "", text)
    text = re.sub(r"[A-Z][a-z]+\s[A-Z][a-z]+", "", text, count=1)
    return text

# 📑 Extract sections

def extract_sections(text):
    sections = {
        "Contact Info": "",
        "Skills": "",
        "Experience": "",
        "Education": "",
        "Projects": "",
        "Certifications": "",
        "Others": ""
    }

    text = text.replace('\n', ' ').replace('\r', ' ')
    text = re.sub(r'\s+', ' ', text)
    lowered = text.lower()

    patterns = {
        "Skills": r"(skills|technical skills|key skills|core competencies|technologies|areas of expertise)[\s:•\-]*",
        "Experience": r"(experience|work experience|employment|professional background|career summary)[\s:•\-]*",
        "Education": r"(education|qualifications|academic background|academics|educational background)[\s:•\-]*",
        "Projects": r"(projects|academic projects|notable projects|major projects|project highlights)[\s:•\-]*",
        "Certifications": r"(certifications|certificates|licenses|credentials)[\s:•\-]*",
    }

    found = {}
    for sec, pat in patterns.items():
        match = re.search(pat, lowered)
        if match:
            found[sec] = match.start()

    sorted_sec = sorted(found.items(), key=lambda x: x[1])
    for i, (sec, start_idx) in enumerate(sorted_sec):
        end_idx = sorted_sec[i + 1][1] if i + 1 < len(sorted_sec) else len(text)
        sections[sec] = text[start_idx:end_idx].strip()

    sections["Contact Info"] = text[:500]

    for sec in sections:
        if not sections[sec]:
            sections[sec] = "[Not Found]"
    return sections

# 🧠 Section-wise matcher

def sectionwise_smart_match(sec1, sec2):
    total_score = 0
    active_weights = 0
    per_section_scores = {}

    weights = {
        "Skills": 0.3,
        "Experience": 0.3,
        "Education": 0.2,
        "Projects": 0.1,
        "Certifications": 0.1
    }

    for sec, weight in weights.items():
        t1, t2 = sec1[sec], sec2[sec]
        if "[Not Found]" in (t1, t2):
            continue

        exact_ratio = SequenceMatcher(None, t1, t2).ratio()
        if exact_ratio > 0.97:
            score = 1.0
        else:
            emb = model.encode([t1, t2], convert_to_tensor=True)
            score = util.pytorch_cos_sim(emb[0], emb[1]).item()

        total_score += weight * score
        active_weights += weight
        per_section_scores[sec] = round(score * 100, 2)

    final_score = round((total_score / active_weights) * 100, 2) if active_weights else 0
    return final_score, per_section_scores

# 🔄 Save results to Excel/CSV

def save_results_to_file(results, filename):
    df = pd.DataFrame(results)
    path = os.path.join(UPLOAD_FOLDER, filename)
    if filename.endswith(".csv"):
        df.to_csv(path, index=False)
    elif filename.endswith(".xlsx"):
        df.to_excel(path, index=False)
    return path
# ✅ Export results for download (with sorting)
def export_results_to_file(results, sort_key="Match_Percentage", filetype="csv"):
    df = pd.DataFrame(results)
    
    # Ensure the sort_key is valid
    if sort_key not in df.columns:
        sort_key = "Match_Percentage"

    df.sort_values(by=sort_key, ascending=False, inplace=True)

    output_path = os.path.join(UPLOAD_FOLDER, f"results_output.{filetype}")
    
    if filetype == "csv":
        df.to_csv(output_path, index=False)
    elif filetype == "xlsx":
        df.to_excel(output_path, index=False)

    return output_path
