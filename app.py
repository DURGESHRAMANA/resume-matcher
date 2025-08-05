import os
from flask import Flask, render_template, request, redirect, url_for, send_file
from werkzeug.utils import secure_filename
from matcher import (
    extract_text_from_file,
    remove_contact_info,
    extract_sections,
    sectionwise_smart_match,
    export_results_to_file
)

app = Flask(__name__)
UPLOAD_FOLDER = "temp"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Store paths temporarily
custom_resume_text = ""
comparison_results = []
result_file_path = ""


@app.route("/")
def index():
    return render_template("index.html", extracted_text=None)


@app.route("/upload_custom", methods=["POST"])
def upload_custom():
    global custom_resume_text
    file = request.files.get("custom_resume")
    if not file:
        return redirect(url_for("index"))

    filename = secure_filename(file.filename)
    custom_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(custom_path)

    try:
        raw_text = extract_text_from_file(custom_path)
        clean_text = remove_contact_info(raw_text)
        custom_resume_text = extract_sections(clean_text)
        return render_template("index.html", extracted_text=raw_text)
    except Exception as e:
        return f"Error extracting custom resume: {str(e)}"


@app.route("/input")
def input_page():
    return render_template("input.html")


@app.route("/upload_folder", methods=["POST"])
def upload_folder():
    global comparison_results
    uploaded_files = request.files.getlist("folder_files")
    if not uploaded_files:
        return redirect(url_for("input_page"))

    comparison_results = []

    for file in uploaded_files:
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)

        try:
            raw_text = extract_text_from_file(file_path)
            clean_text = remove_contact_info(raw_text)
            applied_resume_sections = extract_sections(clean_text)
            match_score, section_scores = sectionwise_smart_match(custom_resume_text, applied_resume_sections)

            comparison_results.append({
                "Resume": filename,
                "Match_Percentage": match_score,
                "Skills_Match": section_scores.get("Skills", 0),
                "Experience_Match": section_scores.get("Experience", 0),
                "Education_Match": section_scores.get("Education", 0),
                "Projects_Match": section_scores.get("Projects", 0),
                "Certifications_Match": section_scores.get("Certifications", 0)
            })

        except Exception as e:
            comparison_results.append({
                "Resume": filename,
                "Match_Percentage": 0,
                "Skills_Match": 0,
                "Experience_Match": 0,
                "Education_Match": 0,
                "Projects_Match": 0,
                "Certifications_Match": 0,
                "Error": str(e)
            })

    # Default sort by Match_Percentage
    comparison_results.sort(key=lambda x: x["Match_Percentage"], reverse=True)
    return render_template("output.html", results=comparison_results, sort_by="Match_Percentage")


@app.route("/sort_results", methods=["POST"])
def sort_results():
    global comparison_results
    sort_key = request.form.get("sort_by", "Match_Percentage")

    try:
        comparison_results.sort(key=lambda x: x.get(sort_key, 0), reverse=True)
    except:
        pass

    return render_template("output.html", results=comparison_results, sort_by=sort_key)


@app.route("/download/<filetype>")
def download(filetype):
    global result_file_path
    sort_by = request.args.get("sort_by", "Match_Percentage")
    result_file_path = export_results_to_file(comparison_results, sort_key=sort_by, filetype=filetype)
    return send_file(result_file_path, as_attachment=True)

@app.route("/view/<filename>")
def view_resume(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        return send_file(filepath)
    return f"File {filename} not found.", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


