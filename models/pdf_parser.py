import fitz
from PIL import Image
import pytesseract
import re
import io
import json

def extract_text_from_pdf(file_path):
    text = ""
    ocr_used = False
    doc = fitz.open(file_path)
    for page in doc:
        page_text = page.get_text().strip()
        if page_text:
            text += page_text + "\n"
        else:
            ocr_used = True
            pix = page.get_pixmap(dpi=300)
            img = Image.open(io.BytesIO(pix.tobytes()))
            ocr_text = pytesseract.image_to_string(img)
            text += ocr_text + "\n"
    return text, ocr_used

def split_sections(text):
    lines = [line.strip() for line in text.splitlines()]
    section_headers = {
        'experience': ['experience', 'work experience', 'professional experience'],
        'education': ['education', 'academic qualifications', 'qualifications'],
        'skills': ['skills', 'technical skills', 'key skills', 'core competencies'],
        'certifications': ['certifications', 'certification', 'achievements'],
        'projects': ['projects', 'project experience', 'personal projects', 'project']
    }
    sections = {key: "" for key in section_headers}
    current_section = None
    
    for line in lines:
        if not line:
            continue
        lower_line = line.lower()
        found_header = False
        for sec, headers in section_headers.items():
            for header in headers:
                header = header.lower()
                if (lower_line.startswith(header) or 
                    lower_line.endswith(header) or 
                    header in lower_line):
                    current_section = sec
                    found_header = True
                    break
            if found_header:
                break
        if found_header:
            continue
        if current_section:
            sections[current_section] += line + "\n"
    return sections

def parse_skills(section_text, ocr_used=False):
    if not section_text.strip():
        return None, 0.0
    
    # Try comma/pipe separated format
    if re.search(r"[,|]", section_text):
        skills = re.split(r"\s*[,|]\s*", section_text)
        cleaned = [s.strip() for s in skills if s.strip()]
        if cleaned:
            return cleaned, 1.0
    
    # Try line break separated format
    lines = [line.strip() for line in section_text.splitlines() if line.strip()]
    if lines:
        return lines, 1.0
    
    # Fallback to skills.json lookup
    try:
        with open("skills.json", "r") as f:
            skills_list = json.load(f)
    except FileNotFoundError:
        skills_list = []
    
    found_skills = []
    text_lower = section_text.lower()
    for skill in skills_list:
        if re.search(rf"\b{re.escape(skill.lower())}\b", text_lower):
            found_skills.append(skill)
    
    return found_skills or None, 0.8 if found_skills else 0.0

def parse_experience(section_text, ocr_used=False):
    if not section_text.strip():
        return None, 0.0
    lines = [line for line in section_text.splitlines() if line.strip()]
    exp_lines = []
    for line in lines:
        if re.search(r"\b(project|skill)\b", line, re.IGNORECASE):
            continue
        exp_lines.append(line)
    if not exp_lines:
        return None, 0.0
    value = "\n".join(exp_lines).strip()
    confidence = 0.9 if ocr_used else 1.0
    return value, confidence

def parse_education(section_text, ocr_used=False):
    if not section_text.strip():
        return None, 0.0
    lines = [line for line in section_text.splitlines() if line.strip()]
    value = "\n".join(lines).strip()
    confidence = 0.9 if ocr_used else 1.0
    return value, confidence

def parse_certifications(section_text, ocr_used=False):
    if not section_text.strip():
        return None, 0.0
    lines = [line for line in section_text.splitlines() if line.strip()]
    value = "\n".join(lines).strip()
    confidence = 0.9 if ocr_used else 1.0
    return value, confidence

def parse_projects(section_text, ocr_used=False):
    if not section_text.strip():
        return None, 0.0
    lines = [line for line in section_text.splitlines() if line.strip()]
    projects = []
    current_proj = {"title": "", "description": ""}
    for line in lines:
        if re.match(r'(.*\d{4}.*|.*present.*|.*github.*)', line, re.IGNORECASE):
            if current_proj["title"]:
                projects.append(current_proj)
            current_proj = {"title": line.strip(), "description": ""}
        else:
            current_proj["description"] += line + " "
    if current_proj["title"]:
        projects.append(current_proj)
    result = []
    for proj in projects:
        title = proj["title"]
        desc = proj["description"].strip()
        entry = f"{title}: {desc}" if desc else title
        result.append(entry)
    return "\n".join(result) if result else None, 0.9 if ocr_used else 1.0

def parse_header_fields(text):
    lines = [line.strip() for line in text.splitlines()]
    header_idx = len(lines)
    section_keywords = ["objective", "summary", "experience", "education", 
                        "project", "skill", "certification", "interests"]
    
    # Find first section header
    for i, line in enumerate(lines):
        if any(kw in line.lower() for kw in section_keywords):
            header_idx = i
            break

    # Fixed regex pattern with proper parenthesis
    name = ""
    for line in lines[:min(header_idx, 8)]:  # Check first 8 lines before sections
        if not line:
            continue
            
        # Improved regex pattern
        if re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]*)*$', line):  # Fixed pattern
            name = line
            break
            
        # Fallback for ALL-CAPS names
        if re.match(r'^[A-Z\s]{3,}$', line) and len(line.split()) >= 2:
            name = line.title()
            break

    # Rest of the contact info parsing remains the same
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    phone_match = re.search(r'(?:\+?(\d{1,3}))?[-. (]*(\d{3})[-. )]*(\d{3})[-. ]*(\d{4})', text)
    linkedin_match = re.search(r'(https?://)?(www\.)?linkedin\.com/in/[\w-]+', text)

    return {
        "name": {"value": name or None, "confidence": 0.99 if name else 0.0},
        "email": {"value": email_match.group(0) if email_match else None, "confidence": 0.99 if email_match else 0.0},
        "phone": {"value": phone_match.group(0) if phone_match else None, "confidence": 0.99 if phone_match else 0.0},
        "linkedin": {"value": linkedin_match.group(0) if linkedin_match else None, "confidence": 0.99 if linkedin_match else 0.0},
    }

def parse_resume(file_path):
    text, ocr_used = extract_text_from_pdf(file_path)
    sections = split_sections(text)
    header_data = parse_header_fields(text)

    # Parse all sections
    exp_val, exp_conf = parse_experience(sections.get('experience', ''), ocr_used)
    edu_val, edu_conf = parse_education(sections.get('education', ''), ocr_used)
    skills_val, skills_conf = parse_skills(sections.get('skills', ''), ocr_used)
    proj_val, proj_conf = parse_projects(sections.get('projects', ''), ocr_used)
    cert_val, cert_conf = parse_certifications(sections.get('certifications', ''), ocr_used)

    # Combine results
    result = {
        **header_data,
        "skills": {"value": skills_val, "confidence": skills_conf},
        "experience": {"value": exp_val, "confidence": exp_conf},
        "education": {"value": edu_val, "confidence": edu_conf},
        "projects": {"value": proj_val, "confidence": proj_conf},
        "certifications": {"value": cert_val, "confidence": cert_conf},
    }
    
    return result