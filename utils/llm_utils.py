from firebase_init import db, SERVER_TIMESTAMP
import os
from dotenv import load_dotenv
import json
import fitz
import requests
from google.cloud import storage
from repositories.topic_repository import create_topic_with_questions
from utils.enum import QuestionType
from utils.prompts import prompt_default, prompt_multiple_choice, prompt_short_answer, prompt_true_false

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
LLM_MODEL = "mistralai/mistral-7b-instruct:free"


def extract_text_from_pdf(pdf_url):
    """Extract plain text from a PDF file hosted online"""
    response = requests.get(pdf_url)
    response.raise_for_status()

    doc = fitz.open(stream=response.content, filetype="pdf")

    text = ""
    for page in doc:
        text += page.get_text()

    return text


def generate_prompt_questions(text, topic, qty, qtype):
    """Generate the proper prompt depending on the question type"""
    switch = {
        QuestionType.MULTIPLE_CHOICE: prompt_multiple_choice,
        QuestionType.TRUE_FALSE: prompt_true_false,
    }

    prompt_fn = switch.get(qtype, prompt_default)
    return prompt_fn(topic, text, qty)


def send_to_openrouter(prompt):
    """Send the prompt to OpenRouter API and return the response"""
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "Referer": "https://replit.com/@marcgc21",  # replace with your own if needed
            "X-Title": "Discord Quiz Bot"
        }

        payload = {
            "model": LLM_MODEL,
            "messages": [{
                "role": "user",
                "content": prompt
            }],
            "temperature": 0.7
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print("⚠️ ERROR IN OPENROUTER REQUEST:", e)


def save_questions_json(topic_name, topic_id, questions_str, guild_id, document_url, qty, qtype):
    """Save generated questions in Firestore and also locally in a JSON file"""
    try:
        new_questions = json.loads(questions_str)
        if isinstance(new_questions, list):
            new_questions = new_questions[:qty]
    except json.JSONDecodeError:
        print("⚠️ Error parsing generated JSON. Check the model output.")
        return

    create_topic_with_questions(
        guild_id, topic_name, topic_id, new_questions, document_url, qty, qtype)

    print(f"✅ {len(new_questions)} questions saved in Firestore for guild {guild_id} and topic '{topic_name}'")

    if os.path.exists("questions.json"):
        with open("questions.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    if topic_name not in data:
        data[topic_name] = []

    for i, question in enumerate(new_questions, start=1):
        question["id"] = str(len(data[topic_name]) + i)
        data[topic_name].append(question)

    with open("questions.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def generate_questions_from_pdf(topic_name, topic_id, guild_id, pdf_url, qty, qtype):
    """Full pipeline: extract text, generate questions with LLM, and save results"""
    text = extract_text_from_pdf(pdf_url)
    prompt = generate_prompt_questions(text, topic_name, qty, qtype)
    result = send_to_openrouter(prompt)
    save_questions_json(topic_name, topic_id, result,
                        guild_id, pdf_url, qty, qtype)
