def prompt_multiple_choice(topic, text, qty):
    return f"""
You are a question generator. Generate **exactly {qty}** multiple-choice questions based on the content below, and **do not generate any extra questions**.

Each question must have four options (A, B, C, D), and only one correct answer. The correct answer should be indicated by the letter.

Output format in JSON:
[
{{
    "question": "Question text...",
    "options": {{
        "A": "Option A",
        "B": "Option B",
        "C": "Option C",
        "D": "Option D"
    }},
    "answer": "B"
}},
...
]  # Exactly {qty} objects like this

Topic: {topic}

Content:
{text[:4000]}
"""


def prompt_true_false(topic, text, qty):
    return f"""
You are a question generator. Generate **exactly {qty}** true/false questions based on the content below, and **do not generate any extra questions**.

Output format in JSON:
[
{{
    "question": "Question text...",
    "answer": "True"  # or "False"
}},
...
]  # Exactly {qty} objects like this

Topic: {topic}

Content:
{text[:4000]}
"""


def prompt_short_answer(topic, text, qty):
    return f"""
You are a question generator. Based on the content below, generate **exactly {qty} short-answer questions**, and do not generate any extras. Only {qty}.
Return in JSON format like this:
[
{{
    "question": "...",
    "answer": "..."
}},
...
]

Topic: {topic}

Content:
{text[:4000]}
"""


def prompt_default(topic, text, qty):
    return f"""
You are a question generator. Based on the content below, generate **exactly {qty} varied questions**, and do not generate any extras. Only {qty}.
Return in JSON format like this:
[
{{
    "question": "...",
    "answer": "..."
}},
...
]

Topic: {topic}

Content:
{text[:4000]}
"""

def prompt_short_answer_grader(expected_answer, user_answer):
    return f"""
You are grading a student's short answer.

Expected answer:
{expected_answer}

Student answer:
{user_answer}

Decide if the student answer has the same meaning as the expected answer.
Be strict but fair:
- Accept paraphrases with equivalent meaning.
- Reject answers that change or omit key facts.
- Reject vague answers that do not clearly match.

Return ONLY valid JSON with this exact schema:
{{
  "is_correct": true,
  "reason": "short reason"
}}
"""
