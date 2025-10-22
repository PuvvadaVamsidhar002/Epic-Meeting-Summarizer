import streamlit as st

def main():
    st.set_page_config(page_title="Epic Meeting Summarizer", page_icon="🚀", layout="wide")

    import json, re, os, smtplib, time
    from datetime import datetime, timedelta
    import spacy
    import pandas as pd
    from transformers import pipeline
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from email.mime.text import MIMEText
    import matplotlib.pyplot as plt
    from streamlit_extras.add_vertical_space import add_vertical_space
    import streamlit.components.v1 as components

    # Cache models
    @st.cache_resource
    def load_models():
        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            os.system("python -m spacy download en_core_web_sm")
            nlp = spacy.load("en_core_web_sm")
        summarizer = pipeline("summarization", model="facebook/bart-large-cnn", max_length=50, min_length=10, do_sample=False)
        asr = pipeline("automatic-speech-recognition", model="openai/whisper-base")
        return nlp, summarizer, asr

    nlp, summarizer, asr = load_models()

    # Google Calendar setup
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    service = build('calendar', 'v3', credentials=creds)

    # Helper functions
    def resolve_relative_date(date_text, current_date=datetime.now()):
        date_text = date_text.lower().strip()
        if "tomorrow" in date_text:
            return (current_date + timedelta(days=1)).strftime("%Y-%m-%d")
        elif "next monday" in date_text:
            days_to_monday = (0 - current_date.weekday() + 7) % 7 + 1
            return (current_date + timedelta(days=days_to_monday)).strftime("%Y-%m-%d")
        elif "friday" in date_text:
            days_to_friday = (4 - current_date.weekday()) % 7
            if days_to_friday == 0:
                days_to_friday = 7
            return (current_date + timedelta(days=days_to_friday)).strftime("%Y-%m-%d")
        try:
            return datetime.strptime(date_text, "%B %d, %Y").strftime("%Y-%m-%d")
        except:
            return date_text

    def assign_priority(deadline, current_date=datetime.now()):
        try:
            deadline_date = datetime.strptime(deadline, "%Y-%m-%d")
            days_left = (deadline_date - current_date).days
            if days_left <= 1: return "High"
            elif days_left <= 5: return "Medium"
            else: return "Low"
        except:
            return "Unknown"

    def preprocess_text(text): return " ".join(text.split())

    def generate_summary(text):
        return summarizer(preprocess_text(text), max_length=50, min_length=10, do_sample=False)[0]['summary_text']

    def extract_tasks_deadlines_assignments(segments):
        tasks = []
        for seg in segments:
            doc = nlp(seg)
            task, person, deadline = None, "Unassigned", "No deadline"
            for token in doc:
                if token.dep_ == "ROOT" and token.pos_ == "VERB":
                    task = token.text
                    for child in token.children:
                        if child.dep_ in ["dobj", "attr"]:
                            task += f" {child.text}"
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    person = ent.text
                elif ent.label_ in ["DATE", "TIME"]:
                    deadline = resolve_relative_date(ent.text)
            person_match = re.match(r'([A-Za-z\s]+),', seg.strip())
            if person_match: person = person_match.group(1).strip()
            if task:
                priority = assign_priority(deadline)
                tasks.append({"Task": task.capitalize(), "Assigned To": person, "Deadline": deadline,
                              "Priority": priority, "Progress": "Not Started"})
        return tasks

    def get_time_left(deadline, current_date=datetime.now()):
        try:
            deadline_date = datetime.strptime(deadline, "%Y-%m-%d")
            days_left = (deadline_date - current_date).days
            hours_left = (deadline_date - current_date).seconds // 3600
            return f"{days_left} days, {hours_left} hours" if days_left >= 0 else "Overdue! 🚨"
        except:
            return "N/A"

    def process_input(file_path, save_output=False):
        if file_path.lower().endswith(('.mp3', '.wav')):
            transcript = asr(file_path)["text"]
        else:
            with open(file_path, 'r', encoding='utf-8') as file:
                transcript = file.read()
        segments = transcript.split('. ')
        summary = generate_summary(transcript)
        tasks = extract_tasks_deadlines_assignments(segments)
        result = {"Summary": summary, "To-Do List": tasks}

        st.write("### 🎤 Meeting Summary Spotlight")
        st.json(result)

        df = pd.DataFrame(tasks)
        st.write("### 📋 To-Do Command Center")
        st.table(df.style.set_properties(**{'background-color': "#00d0ff", 'border-color': '#333'}))

        st.write("### ⏳ Mission Countdown")
        for task in tasks:
            if task['Deadline'] != "No deadline":
                time_left = get_time_left(task['Deadline'])
                color = "red" if "Overdue" in time_left else "green" if "0 days" in time_left else "orange"
                st.write(f"**{task['Task']}** (Assigned to **{task['Assigned To']}**): "
                         f"<span style='color:{color}'>{time_left}</span>", unsafe_allow_html=True)

        progress_counts = df['Progress'].value_counts()
        fig, ax = plt.subplots()
        ax.bar(progress_counts.index, progress_counts.values, color=['#ff6f61', '#6b5b95', '#88b04b'])
        ax.set_title("🌟 Team Progress Galaxy", fontsize=14, pad=15)
        ax.set_ylabel("Task Count", fontsize=12)
        for i, v in enumerate(progress_counts.values):
            ax.text(i, v + 0.5, str(v), ha='center', fontsize=12)
        st.pyplot(fig)

        if save_output:
            with open('meeting_summary.json', 'w') as f:
                json.dump(result, f, indent=2)
            st.success("📥 Results saved successfully!")

    # UI
    st.markdown("<h1 style='text-align: center; color: #42a5f5;'>Epic Meeting Summarizer 🌀</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #757575;'>Unleash your team's potential with AI-powered magic! 🎩</p>", unsafe_allow_html=True)

    uploaded_file = st.file_uploader("📂 Upload your meeting file (.txt, .mp3, .wav)", type=["txt", "mp3", "wav"])
    save_output = st.checkbox("💾 Save results to meeting_summary.json")
    if uploaded_file:
        with open("temp_input", "wb") as f:
            f.write(uploaded_file.getbuffer())
        process_input("temp_input", save_output)
        os.remove("temp_input")

    add_vertical_space(2)

if __name__ == "__main__":
    main()
