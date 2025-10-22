# 🚀 Epic Meeting Summarizer 🌀

An AI-powered Streamlit app that **transcribes**, **summarizes**, and **organizes meeting discussions** into actionable tasks with **deadlines, priorities**, and **Google Calendar integration**.

---

## 🌟 Features

- 🎙️ **Speech-to-Text:** Converts `.wav` or `.mp3` meeting audio to text using Whisper.
- 🧠 **Summarization:** Generates concise summaries using BART transformer.
- ✅ **Task Extraction:** Detects tasks, assignees, and deadlines with spaCy NLP.
- 📅 **Calendar Sync:** Automatically adds tasks to Google Calendar.
- 📧 **Email Alerts:** Sends task reminders to teammates.
- 🎮 **Gamified Progress:** Track task completion and earn points.
- 📊 **Visual Dashboard:** Bar chart of task progress and deadlines.

---

## 🧰 Tech Stack

- **Frontend:** Streamlit  
- **Backend:** Python (Transformers, spaCy, Google API)  
- **Speech Recognition:** OpenAI Whisper  
- **Summarization Model:** Facebook BART-large-CNN  

---

## ⚙️ Installation

1. **Clone the repo**
   ```bash
   git clone https://github.com/<your-username>/Epic-Meeting-Summarizer.git
   cd Epic-Meeting-Summarizer
