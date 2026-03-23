import discord
import os
from utils.llm_utils import generate_questions_from_pdf
import json
import random

DOCS_PATH = "docs"


async def handle_upload(ctx, topic_name):
    if not ctx.message.attachments:
        await ctx.send("❌ Please attach a PDF file along with the command.")
        return

    file = ctx.message.attachments[0]

    if not file.filename.endswith(".pdf"):
        await ctx.send("❌ Only PDF files are allowed.")
        return

    await ctx.send(f"📥 Receiving the file for topic: **{topic_name}**...")

    os.makedirs(DOCS_PATH, exist_ok=True)
    pdf_path = os.path.join(DOCS_PATH, f"{topic_name}.pdf")
    await file.save(pdf_path)
    await ctx.send(f"✅ PDF saved as `{topic_name}.pdf` in the `/docs` folder.")

    # Generate questions directly from PDF
    try:
        generate_questions_from_pdf(topic_name)
        await ctx.send("🧠 Questions successfully generated from the PDF.")
    except Exception as e:
        await ctx.send(f"❌ Error generating questions: {e}")


async def handle_quiz(ctx, topic_name):
    print('asdasdasdasd');
    if not os.path.exists("questions.json"):
        await ctx.send("❌ The file `questions.json` was not found.")
        return

    with open("questions.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    if topic_name not in data:
        await ctx.send(f"❌ No questions registered for topic `{topic_name}`.")
        return

    questions = random.sample(data[topic_name], min(10, len(data[topic_name])))

    quiz_text = "📝 Answer with T or F (for example: `TFTFTFTFTF`):\n"
    for idx, q in enumerate(questions):
        quiz_text += f"\n{idx+1}. {q['question']}"

    await ctx.send(quiz_text)

    def check(m):
        return (
            m.author == ctx.author
            and m.channel == ctx.channel
            and len(m.content) == len(questions)
        )

    try:
        answer = await ctx.bot.wait_for('message', check=check, timeout=60.0)
    except:
        await ctx.send("⏰ Time is up. Try again.")
        return

    result_text = "\n📊 Results:\n"
    correct = 0
    for i, r in enumerate(answer.content.upper()):
        correct_answer = questions[i]['answer'].upper()
        if r == correct_answer:
            result_text += f"✅ {i+1}. Correct\n"
            correct += 1
        else:
            result_text += f"❌ {i+1}. Incorrect (Correct answer: {correct_answer})\n"

    result_text += f"\n🏁 You got {correct} out of {len(questions)} questions right."
    await ctx.send(result_text)
