from firebase_init import db, SERVER_TIMESTAMP
import os
from dotenv import load_dotenv
import json
import asyncio
import aiohttp
import fitz
from google.cloud import storage
from repositories.topic_repository import create_topic_with_questions
from utils.enum import QuestionType
from utils.prompts import prompt_default, prompt_multiple_choice, prompt_short_answer, prompt_true_false

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Primary free model + optional comma-separated fallbacks in .env
# Example: OPENROUTER_FALLBACK_MODELS=meta-llama/llama-3.3-8b-instruct:free,google/gemma-3-27b-it:free
LLM_MODEL = os.getenv("OPENROUTER_MODEL", "mistralai/mistral-small-3.1-24b-instruct:free")
FALLBACK_MODELS = [
    model.strip() for model in os.getenv("OPENROUTER_FALLBACK_MODELS", "").split(",") if model.strip()
]
OPENROUTER_MODELS = list(dict.fromkeys([LLM_MODEL, *FALLBACK_MODELS]))

QUESTIONS_JSON_FILE = "questions.json"
MAX_PDF_TEXT_CHARS = 24000


async def _make_api_request_with_retry(url, headers, payload, max_retries=3, base_wait=2):
    """Make API request to OpenRouter with exponential backoff on 429 errors.
    
    Args:
        url: API endpoint URL
        headers: Request headers
        payload: Request payload
        max_retries: Maximum number of retry attempts
        base_wait: Base wait time in seconds (will be exponentially increased)
    
    Returns:
        Response object or None on failure
    """
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for attempt in range(max_retries + 1):
            try:
                async with session.post(url, headers=headers, json=payload) as response:
                    status = response.status
                    body_text = await response.text()

                    if status == 402:
                        print("⛔ OpenRouter returned 402 Payment Required.")
                        print("   Your current model/plugin request requires credits or paid access.")
                        print(f"   Response: {body_text}")
                        return status, body_text

                    # Handle 429 (Too Many Requests) with retry
                    if status == 429:
                        if attempt < max_retries:
                            wait_time = base_wait * (2 ** attempt)
                            print(f"⚠️ Rate limited. Waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                            await asyncio.sleep(wait_time)
                            continue
                        print("⛔ OpenRouter rate limit exceeded after max retries")
                        return status, body_text

                    if status >= 500:
                        if attempt < max_retries:
                            wait_time = base_wait * (2 ** attempt)
                            print(f"⚠️ OpenRouter server error ({status}). Retrying in {wait_time}s...")
                            await asyncio.sleep(wait_time)
                            continue
                        return status, body_text

                    return status, body_text

            except asyncio.TimeoutError:
                if attempt < max_retries:
                    wait_time = base_wait * (2 ** attempt)
                    print(f"⚠️ Request timeout. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                return None, "timeout"
            except aiohttp.ClientError as e:
                if attempt < max_retries:
                    wait_time = base_wait * (2 ** attempt)
                    print(f"⚠️ Network error ({type(e).__name__}). Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                return None, str(e)
    
    return None


async def send_to_openrouter(messages):
    """Send messages to OpenRouter API with support for PDFs and text.
    
    Args:
        messages: Either a string (legacy text prompt) or a list of message dicts
                  with new format supporting files and content arrays.
    
    Includes retry logic with exponential backoff to handle rate limiting (429 errors).
    """
    try:
        if not OPENROUTER_API_KEY:
            print("⚠️ ERROR: OPENROUTER_API_KEY is not set in .env")
            return None

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "Referer": "https://replit.com/@marcgc21",
            "X-Title": "Discord Quiz Bot"
        }

        # Support both legacy (string) and new (list) formats
        if isinstance(messages, str):
            messages = [{
                "role": "user",
                "content": messages
            }]

        for model in OPENROUTER_MODELS:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.7
            }

            status, body_text = await _make_api_request_with_retry(url, headers, payload)

            if status is None:
                print(f"⚠️ Model '{model}' failed due to network/timeout; trying next fallback if available.")
                continue

            if status == 402:
                print(f"⚠️ Model '{model}' denied due to billing restrictions (HTTP 402).")
                continue

            if status == 404:
                print(f"⚠️ Model '{model}' not found (HTTP 404). Trying next fallback.")
                continue

            if status >= 400:
                print(f"⚠️ Model '{model}' returned HTTP {status}. Trying next fallback.")
                print(f"   - Response: {body_text}")
                continue

            data = json.loads(body_text)
            if "choices" not in data or len(data["choices"]) == 0:
                print(f"⚠️ Invalid response from model '{model}': {data}")
                continue

            return data["choices"][0]["message"]["content"]

        print(f"⛔ All configured models failed: {OPENROUTER_MODELS}")
        return None
        
    except aiohttp.ClientError as e:
        print(f"⚠️ ERROR IN OPENROUTER REQUEST: {type(e).__name__}")
        print(f"   Details: {e}")
        return None
    except Exception as e:
        print(f"⚠️ ERROR IN OPENROUTER REQUEST: {type(e).__name__}")
        print(f"   Details: {e}")
        return None


def _extract_balanced_json_block(text, opener, closer):
    start = text.find(opener)
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(text)):
        char = text[i]

        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue

        if char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return text[start:i + 1]

    return None


def _parse_questions_json(raw_text):
    """Parse model output robustly (pure JSON, fenced JSON, or JSON wrapped in text)."""
    if not raw_text:
        return None

    stripped = raw_text.strip()

    # Try exact JSON first
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # Strip markdown fences (```json ... ```)
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 2 and lines[-1].strip().startswith("```"):
            fenced_body = "\n".join(lines[1:-1]).strip()
            try:
                return json.loads(fenced_body)
            except json.JSONDecodeError:
                pass

    # Extract first balanced array/object from text
    candidates = [
        _extract_balanced_json_block(stripped, "[", "]"),
        _extract_balanced_json_block(stripped, "{", "}"),
    ]

    for candidate in candidates:
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    return None


def _extract_text_from_pdf_bytes(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        pages_text = []
        for page in doc:
            pages_text.append(page.get_text("text"))
        return "\n".join(pages_text).strip()
    finally:
        doc.close()


async def extract_text_from_pdf_url(pdf_url):
    timeout = aiohttp.ClientTimeout(total=60)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(pdf_url) as response:
                if response.status != 200:
                    print(f"⚠️ Could not download PDF (HTTP {response.status})")
                    return None

                pdf_bytes = await response.read()

        text = await asyncio.to_thread(_extract_text_from_pdf_bytes, pdf_bytes)
        if not text:
            print("⚠️ PDF text extraction returned empty content")
            return None

        return text[:MAX_PDF_TEXT_CHARS]
    except Exception as e:
        print(f"⚠️ ERROR extracting text from PDF URL: {type(e).__name__}: {e}")
        return None


def save_questions_json(topic_name, topic_id, questions_str, guild_id, document_url, qty, qtype):
    """Save generated questions in Firestore and also locally in a JSON file"""
    parsed = _parse_questions_json(questions_str)
    if parsed is None:
        print("⚠️ Error parsing generated JSON. Model output was not valid JSON.")
        return False

    if isinstance(parsed, dict):
        for key in ("questions", "items", "data"):
            if isinstance(parsed.get(key), list):
                parsed = parsed[key]
                break

    if not isinstance(parsed, list):
        print("⚠️ Parsed JSON does not contain a list of questions.")
        return False

    new_questions = parsed[:qty]

    create_topic_with_questions(
        guild_id, topic_name, topic_id, new_questions, document_url, qty, qtype)

    print(f"✅ {len(new_questions)} questions saved in Firestore for guild {guild_id} and topic '{topic_name}'")

    if os.path.exists(QUESTIONS_JSON_FILE):
        with open(QUESTIONS_JSON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    if topic_name not in data:
        data[topic_name] = []

    for i, question in enumerate(new_questions, start=1):
        question["id"] = str(len(data[topic_name]) + i)
        data[topic_name].append(question)

    with open(QUESTIONS_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return True


async def generate_questions_from_pdf(topic_name, topic_id, guild_id, pdf_url, qty, qtype):
    """Full pipeline: extract PDF text locally and generate questions with free model."""
    try:
        extracted_text = await extract_text_from_pdf_url(pdf_url)
        if not extracted_text:
            print(f"⚠️ FAILED: Could not extract text from PDF for topic '{topic_name}'")
            return False

        # Get the appropriate prompt template
        switch = {
            QuestionType.MULTIPLE_CHOICE: prompt_multiple_choice,
            QuestionType.TRUE_FALSE: prompt_true_false,
        }
        prompt_fn = switch.get(qtype, prompt_default)
        prompt_text = prompt_fn(topic_name, extracted_text, qty)

        # Free-only path: send plain text, no file-parser plugin
        messages = [
            {
                "role": "user",
                "content": prompt_text
            }
        ]
        
        result = await send_to_openrouter(messages)

        if result is None:
            print(f"⚠️ FAILED: Could not generate questions for topic '{topic_name}' in guild {guild_id}")
            return False

        return save_questions_json(topic_name, topic_id, result,
                                   guild_id, pdf_url, qty, qtype)
    except Exception as e:
        print(f"⚠️ ERROR in generate_questions_from_pdf: {type(e).__name__}: {e}")
        return False
