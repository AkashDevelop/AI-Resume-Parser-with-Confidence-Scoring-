import streamlit as st
from pdf_parser import parse_resume

st.set_page_config(page_title="Resume Parser", layout="centered")
st.title("Resume Parser")

uploaded_file = st.file_uploader("Upload your resume (PDF)", type=["pdf"])
if uploaded_file:
    with open("temp_resume.pdf", "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    try:
        result = parse_resume("temp_resume.pdf")
    except Exception as e:
        st.error(f"Error parsing resume: {str(e)}")
        st.stop()

    # Prepare structured output
    structured_output = {
        "name": result.get("name", {}).get("value"),
        "email": result.get("email", {}).get("value"),
        "phone": result.get("phone", {}).get("value"),
        "linkedin": result.get("linkedin", {}).get("value"),
        "skills": result.get("skills", {}).get("value") or [],
        "education": result.get("education", {}).get("value"),
        "experience": result.get("experience", {}).get("value"),
        "projects": result.get("projects", {}).get("value"),
        "certifications": result.get("certifications", {}).get("value"),
    }

    # Display results
    st.subheader("Parsed Resume Data")
    st.json(structured_output)

    st.subheader("Detailed Analysis")
    fields = [
        ("Personal Info", ["name", "email", "phone", "linkedin"]),
        ("Skills", ["skills"]),
        ("Professional History", ["experience", "projects"]),
        ("Education & Certifications", ["education", "certifications"])
    ]

    for category, field_keys in fields:
        st.markdown(f"### {category}")
        cols = st.columns(2)
        for i, field in enumerate(field_keys):
            data = result.get(field, {})
            value = data.get("value", "NIL")
            conf = data.get("confidence", 0)
            
            if value == "NIL" or conf == 0:
                cols[i%2].error(f"{field.title()}: Not detected")
            elif conf < 0.7:
                cols[i%2].warning(f"{field.title()}: {value} (Confidence: {conf:.0%})")
            else:
                cols[i%2].success(f"{field.title()}: {value} (Confidence: {conf:.0%})")