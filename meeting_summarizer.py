import streamlit as st
import pyaudio
import wave

def main():
    st.set_page_config(page_title="Epic Meeting Summarizer", page_icon="🚀", layout="wide")  # First command

    # Import other libraries and load models after set_page_config
    import argparse
    import json
    import re
    from datetime import datetime, timedelta
    import spacy
    from transformers import pipeline
    import pandas as pd
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    import os
    import smtplib
    from email.mime.text import MIMEText
    import time
    import matplotlib.pyplot as plt
    from streamlit_extras.add_vertical_space import add_vertical_space
    import streamlit.components.v1 as components

    # Load models with caching, now inside main
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

    # Google Calendar API setup
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

    def resolve_relative_date(date_text, current_date=datetime.now()):
        date_text = date_text.lower().strip()
        if "tomorrow" in date_text:
            return (current_date + timedelta(days=1)).strftime("%Y-%m-%d")
        elif "next monday" in date_text:
            days_to_monday = (0 - current_date.weekday() + 7) % 7 + 1
            return (current_date + timedelta(days=days_to_monday)).strftime("%Y-%m-%d")
        elif "friday" in date_text:
            days_to_friday = (4 - current_date.weekday()) % 7
            if days_to_friday == 0: days_to_friday = 7
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

    def preprocess_text(text):
        return " ".join(text.split())

    def generate_summary(text):
        summary = summarizer(preprocess_text(text), max_length=50, min_length=10, do_sample=False)[0]['summary_text']
        return summary

    def extract_tasks_deadlines_assignments(segments):
        tasks = []
        for seg in segments:
            doc = nlp(seg)
            task = None
            person = "Unassigned"
            deadline = "No deadline"
            
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
            if person_match:
                person = person_match.group(1).strip()
            
            if task:
                priority = assign_priority(deadline)
                tasks.append({"Task": task.capitalize(), "Assigned To": person, "Deadline": deadline, "Priority": priority, "Progress": "Not Started"})
        
        return tasks

    def add_to_google_calendar(event_details):
        event = {
            'summary': event_details['summary'],
            'start': {
                'date': event_details['date'],
                'timeZone': 'Asia/Kolkata',
            },
            'end': {
                'date': event_details['date'],
                'timeZone': 'Asia/Kolkata',
            },
            'description': event_details.get('description', ''),
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 24 * 60},  # 1-day reminder
                ],
            },
        }
        event = service.events().insert(calendarId='primary', body=event).execute()
        print(f"Event created: {event.get('htmlLink')}")

    def send_task_email(task, sender_email="vamsidhar.puvvada002@gmail.com", receiver_email=None):
        if receiver_email is None:
            receiver_email = task["Assigned To"].lower().replace(" ", ".") + "@gmail.com"
        time_left = get_time_left(task['Deadline'])
        msg = MIMEText(f"Subject: 🚀 Task Alert - {task['Task']}!\n\nHi {task['Assigned To']} 🌟,\n\nTime to shine! You’ve got this task:\n- Task: {task['Task']} 🎯\n- Deadline: {task['Deadline']} ⏰\n- Priority: {task['Priority']} ⚡\n- Time Left: {time_left} 🕒\n\nUpdate your progress (Not Started/In Progress/Completed) to earn points! 🎮\n\nCheers,\nThe Epic Meeting Squad 🔥")
        msg['Subject'] = f"🚀 Task Alert - {task['Task']}!"
        msg['From'] = sender_email
        msg['To'] = receiver_email

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, "pybc jxct sbqk ztan")
            server.send_message(msg)
        print(f"Email blasted to {receiver_email} for task: {task['Task']} 🎉")

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
            try:
                transcript = asr(file_path)["text"]
            except Exception as e:
                st.error(f"Error processing audio: {str(e)}. Please ensure the file is valid and not corrupted.")
                return
        else:
            with open(file_path, 'r', encoding='utf-8') as file:
                transcript = file.read()
        
        segments = transcript.split('. ')
        summary = generate_summary(transcript)
        tasks = extract_tasks_deadlines_assignments(segments)
        
        calendar_events = []
        current_date = datetime.now().strftime("%Y-%m-%d")
        for task in tasks:
            if task['Deadline'] != "No deadline" and re.match(r'^\d{4}-\d{2}-\d{2}$', task['Deadline']):
                event = {
                    'summary': f"🎯 {task['Task']} - {task['Assigned To']}",
                    'date': task['Deadline'],
                    'description': f"Priority: {task['Priority']}"
                }
                calendar_events.append(event)
        
        result = {
            "Summary": summary,
            "To-Do List": tasks
        }
        st.write("### 🎤 Meeting Summary Spotlight")
        st.json(result)
        
        df = pd.DataFrame(tasks)
        st.write("### 📋 To-Do Command Center")
        st.table(df.style.set_properties(**{'background-color': "#00d0ff", 'border-color': '#333'}))
        
        if calendar_events:
            st.write("### 🌐 Mission Control: Calendar Sync")
            for i, event in enumerate(calendar_events, 1):
                st.write(f"{i}. {event['summary']} on {event['date']} (Priority: {event['description'].split(': ')[1]})")
            if st.button("🚀 Launch to Google Calendar"):
                for event in calendar_events:
                    add_to_google_calendar(event)
                st.success("Missions logged in Google Calendar! 🗓️")
            
            if st.button("📧 Send Epic Task Alerts"):
                for task in tasks:
                    send_task_email(task)
                st.success("Alerts dispatched to the team! 📬")
        
        if save_output:
            with open('meeting_summary.json', 'w') as f:
                json.dump(result, f, indent=2)
            st.write("📥 Results saved to meeting_summary.json like a boss!")
        
        # Interactive task completion with gamification
        if st.button("🎮 Mark Heroes for Victory"):
            total_points = 0
            for task in tasks:
                if task['Deadline'] != "No deadline":
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.checkbox(f"🏆 Mark {task['Task']} as Completed (Deadline: {task['Deadline']})", key=task['Task']):
                            task['Progress'] = "Completed"
                            total_points += 10
                            st.write(f"🎉 {task['Task']} conquered! +10 points!")
                            components.html("""
                                <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.5.1/dist/confetti.browser.min.js"></script>
                                <script>
                                    setTimeout(() => {
                                        confetti({
                                            particleCount: 100,
                                            spread: 70,
                                            origin: { y: 0.6 }
                                        });
                                    }, 500);
                                </script>
                            """, height=0)
                    with col2:
                        if task['Progress'] == "Completed":
                            st.write(f"Points: {total_points}")
            st.write("### 📊 Updated Heroic To-Do List")
            df_updated = pd.DataFrame(tasks)
            st.table(df_updated.style.set_properties(**{'background-color': "#00e1ff", 'border-color': '#00695c'}))
        
        # Task reminder countdown with urgency
        st.write("### ⏳ Mission Countdown")
        for task in tasks:
            if task['Deadline'] != "No deadline":
                time_left = get_time_left(task['Deadline'])
                color = "red" if "Overdue" in time_left else "green" if "0 days" in time_left else "orange"
                st.write(f"**{task['Task']}** (Assigned to **{task['Assigned To']}**): <span style='color:{color}'>{time_left}</span>", unsafe_allow_html=True)
        
        # Progress Dashboard with flair
        progress_counts = df['Progress'].value_counts()
        fig, ax = plt.subplots()
        ax.bar(progress_counts.index, progress_counts.values, color=['#ff6f61', '#6b5b95', '#88b04b'])
        ax.set_title("🌟 Team Progress Galaxy", fontsize=14, pad=15)
        ax.set_ylabel("Task Count", fontsize=12)
        for i, v in enumerate(progress_counts.values):
            ax.text(i, v + 0.5, str(v), ha='center', fontsize=12)
        st.pyplot(fig)

    st.markdown("<h1 style='text-align: center; color: #42a5f5;'>Epic Meeting Summarizer 🌀</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #757575;'>Unleash your team's potential with AI-powered magic! 🎩</p>", unsafe_allow_html=True)
    
    # Either upload or record
    input_method = st.radio("Choose input method:", ("📁 Upload File", "🎙️ Live Record"))
    
    save_output = st.checkbox("💾 Save epic results to meeting_summary.json")
    
    if input_method == "📁 Upload File":
        uploaded_file = st.file_uploader("📂 Upload your mission file (e.g., .txt, .mp3, .wav)", type=["txt", "mp3", "wav"], help="Drag & drop up to 200MB!")
        if uploaded_file is not None:
            with open("temp_input", "wb") as f:
                f.write(uploaded_file.getbuffer())
            process_input("temp_input", save_output)
            os.remove("temp_input")
    
    elif input_method == "🎙️ Live Record":
        st.write("### 🎤 Live Recording")
        if st.button("🎤 Start Recording"):
            st.write("Recording started... Speak your meeting notes!")
            st.session_state.recording = True
        if 'recording' in st.session_state and st.session_state.recording:
            if st.button("⏹️ Stop Recording"):
                st.write("Recording stopped. Processing audio...")
                # Record audio using pyaudio
                CHUNK = 1024
                FORMAT = pyaudio.paInt16
                CHANNELS = 1
                RATE = 44100
                RECORD_SECONDS = 5  # Adjust recording duration as needed
                p = pyaudio.PyAudio()
                stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
                frames = []
                for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                    data = stream.read(CHUNK)
                    frames.append(data)
                stream.stop_stream()
                stream.close()
                p.terminate()
                with wave.open("temp_recording.wav", 'wb') as wf:
                    wf.setnchannels(CHANNELS)
                    wf.setsampwidth(p.get_sample_size(FORMAT))
                    wf.setframerate(RATE)
                    wf.writeframes(b''.join(frames))
                process_input("temp_recording.wav", save_output)
                os.remove("temp_recording.wav")
                st.session_state.recording = False
    
    add_vertical_space(2)

if __name__ == "__main__":
    main()