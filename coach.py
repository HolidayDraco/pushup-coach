# coach.py - LIVE SMS PUSH-UP COACH
import yaml
import csv
import os
from datetime import datetime
from flask import Flask, request
from twilio.rest import Client
from openai import OpenAI

app = Flask(__name__)

# === CONFIG & SECRETS ===
CONFIG_FILE = "config.yaml"
TASKS_FILE = "tasks.csv"

# Load config (with error handling)
def load_config():
    if not os.path.exists(CONFIG_FILE):
        # Default config if missing
        default_config = {
            "goal": "Do 100 push-ups in a row in 90 days",
            "user_name": "Alex"
        }
        with open(CONFIG_FILE, 'w') as f:
            yaml.dump(default_config, f)
        return default_config
    with open(CONFIG_FILE, 'r') as f:
        return yaml.safe_load(f)

CONFIG = load_config()

# Twilio & xAI (env vars)
TWILIO_SID = os.getenv('TWILIO_SID')
TWILIO_TOKEN = os.getenv('TWILIO_TOKEN')
TWILIO_NUMBER = os.getenv('TWILIO_NUMBER')
USER_PHONE = os.getenv('USER_PHONE')
XAI_API_KEY = os.getenv('XAI_API_KEY')

if not all([TWILIO_SID, TWILIO_TOKEN, TWILIO_NUMBER, USER_PHONE, XAI_API_KEY]):
    print("Missing env vars! Check Render settings.")
    exit(1)

twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)
xai_client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")

# === TASKS ===
def load_tasks():
    if not os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["date","day","task_sent","user_response","ai_feedback","completed","reps_done"])
        return []
    with open(TASKS_FILE, 'r') as f:
        reader = csv.DictReader(f)
        return list(reader)

def save_task(task):
    with open(TASKS_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            task['date'], task['day'], task['task_sent'],
            task['user_response'], task['ai_feedback'],
            task['completed'], task.get('reps_done', '')
        ])

# === GROK AI ===
def ask_grok(prompt):
    try:
        resp = xai_client.chat.completions.create(
            model="grok-beta",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Fallback: Great job! Keep going. (Error: {str(e)})"

# === DAILY TASK ===
def send_daily_task():
    tasks = load_tasks()
    today = datetime.now().strftime("%Y-%m-%d")
    if any(t['date'] == today for t in tasks):
        return "Already sent today."

    day = len(tasks) + 1
    history = "\n".join([f"Day {t['day']}: {t.get('user_response', 'No reply')}" for t in tasks[-3:]])

    prompt = f"""
    Goal: {CONFIG['goal']}
    Today is Day {day}. User name: {CONFIG['user_name']}.
    Recent replies:
    {history or 'No history yet'}

    Generate ONE short, motivating push-up task for today.
    Progressive to 100 in a row. 3 sets max. Include reps.
    Example: "3 sets of 5 push-ups. Rest 60s. Reply 'Done 15'"
    Keep under 140 characters for SMS.
    """

    task = ask_grok(prompt)
    if len(task) > 140:
        task = task[:137] + "..."

    message = f"Push-up Coach Day {day}\n{task}\nReply to log."

    twilio_client.messages.create(
        body=message,
        from_=TWILIO_NUMBER,
        to=USER_PHONE
    )

    save_task({
        'date': today,
        'day': day,
        'task_sent': task,
        'user_response': '',
        'ai_feedback': '',
        'completed': 'No'
    })
    return f"Sent: {message}"

# === SMS REPLY WEBHOOK ===
@app.route('/sms', methods=['POST'])
def sms_reply():
    incoming = request.values.get('Body', '').strip()
    from_num = request.values.get('From')

    if from_num != USER_PHONE:
        return "Unauthorized", 403

    tasks = load_tasks()
    today = datetime.now().strftime("%Y-%m-%d")
    today_task = next((t for t in tasks if t['date'] == today), None)
    if not
