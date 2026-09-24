
import json
import os
import re
from pathlib import Path
from typing import Literal

import wikipedia
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from groq import Groq
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="Wikipedia Research & Quick Summary Assistant")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

wikipedia.set_lang("en")
wikipedia.set_user_agent("WikiStudyAssistant/1.0 (student project; sslkdfkp33@gmail.com)")
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "openai/gpt-oss-120b"  

Mode = Literal["beginner", "academic"]

PERSONA = {
    "beginner": {
        "temperature": 0.6,
        "style": (
            "Explain like I'm five. Use short sentences, everyday words, and "
            "simple analogies. If you must use a technical term, define it "
            "in plain language right after."
        ),
    },
    "academic": {
        "temperature": 0.3,
        "style": (
            "Write for a university research audience. Use precise, "
            "field-appropriate vocabulary and be rigorous and specific."
        ),
    },
}



class ResearchRequest(BaseModel):
    topic: str
    mode: Mode = "beginner"


class ExplainRequest(BaseModel):
    topic: str
    article_text: str
    mode: Mode = "beginner"


class QuizRequest(BaseModel):
    topic: str
    article_text: str
    mode: Mode = "beginner"
    num_questions: int = 5


class ExportRequest(BaseModel):
    topic: str
    summary: str
    reading_metrics: dict
    related_topics: list[str] = []
    takeaways: list[str] = []
    vocabulary: list[dict] = []
    quiz: list[dict] = []




def wikipedia_search(topic: str) -> dict:
    try:
        page = wikipedia.page(topic, auto_suggest=True, redirect=True)
    except wikipedia.exceptions.DisambiguationError as e:
        page = wikipedia.page(e.options[0], auto_suggest=False)
    except wikipedia.exceptions.PageError:
        raise HTTPException(404, f"No Wikipedia page found for '{topic}'.")

    return {
        "title": page.title,
        "summary": wikipedia.summary(page.title, sentences=5, auto_suggest=False),
        "content": page.content,
        "url": page.url,
    }




def calculate_reading_metrics(text: str) -> dict:
    words = re.findall(r"\b\w+\b", text)
    word_count = len(words)
    reading_time_minutes = max(1, round(word_count / 200))  # 200 WPM

    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    avg_word_len = (sum(len(w) for w in words) / word_count) if word_count else 0
    avg_sentence_len = (word_count / len(sentences)) if sentences else 0

    if avg_sentence_len < 15 and avg_word_len < 5:
        complexity = "Easy"
    elif avg_sentence_len < 25 and avg_word_len < 6:
        complexity = "Medium"
    else:
        complexity = "Hard"

    return {
        "word_count": word_count,
        "reading_time_minutes": reading_time_minutes,
        "complexity": complexity,
    }




def fetch_related_wiki_topics(topic: str, limit: int = 5) -> list[str]:
    results = wikipedia.search(topic, results=limit + 1)
    return [r for r in results if r.lower() != topic.lower()][:limit]




def generate_persona_explanation(topic: str, article_text: str, mode: Mode) -> dict:
    persona = PERSONA[mode]
    prompt = f"""You are rewriting a Wikipedia article on "{topic}" for a reader.
{persona['style']}

Base everything strictly on the article text below — do not add outside facts.

Return ONLY valid JSON with these keys:
"summary": a {"short, friendly" if mode == "beginner" else "precise, academic"} paragraph (3-5 sentences).
"takeaways": a list of 4-6 short bullet-point strings, the key facts a student should remember.
"vocabulary": a list of 3-5 objects {{"term": ..., "definition": ...}}, the most important
terms in the article, defined {"in plain simple language" if mode == "beginner" else "with precise technical accuracy"}.

Article:
\"\"\"{article_text[:6000]}\"\"\"
"""
    response = groq_client.chat.completions.create(
        model=MODEL,
        temperature=persona["temperature"],
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()

    try:
        explanation = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(502, "The model didn't return valid explanation JSON. Try again.")
    return explanation



def generate_study_quiz(article_text: str, mode: Mode, num_questions: int = 5) -> list[dict]:
    persona = PERSONA[mode]
    prompt = f"""You write multiple-choice study quizzes strictly grounded in the
article text given below. Do not use outside knowledge. {persona['style']}

Return ONLY valid JSON — a list of exactly {num_questions} objects, each with:
"question" (string), "options" (list of 4 strings), "answer" (the correct
option, copied exactly from options), "explanation" (1-2 sentences, grounded
in the article).

Article:
\"\"\"{article_text[:6000]}\"\"\"
"""
    response = groq_client.chat.completions.create(
        model=MODEL,
        temperature=persona["temperature"],
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()

    try:
        quiz = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(502, "The model didn't return valid quiz JSON. Try again.")
    return quiz




def export_study_deck_markdown(data: ExportRequest) -> str:
    lines = [f"# Study Deck: {data.topic}", ""]

    lines += ["## Summary", data.summary, ""]

    if data.takeaways:
        lines += ["## Key Takeaways"]
        lines += [f"- {t}" for t in data.takeaways]
        lines += [""]

    if data.vocabulary:
        lines += ["## Key Vocabulary"]
        lines += [f"- **{v.get('term', '')}**: {v.get('definition', '')}" for v in data.vocabulary]
        lines += [""]

    m = data.reading_metrics
    lines += [
        "## Reading Metrics",
        f"- Word count: {m.get('word_count', '—')}",
        f"- Estimated reading time: {m.get('reading_time_minutes', '—')} min",
        f"- Complexity: {m.get('complexity', '—')}",
        "",
    ]

    if data.related_topics:
        lines += ["## Related Topics"]
        lines += [f"- {t}" for t in data.related_topics]
        lines += [""]

    if data.quiz:
        lines += ["## Quiz", ""]
        for i, q in enumerate(data.quiz, 1):
            lines.append(f"**Q{i}. {q.get('question', '')}**")
            for opt in q.get("options", []):
                lines.append(f"- {opt}")
            lines.append(f"> **Answer:** {q.get('answer', '')}")
            if q.get("explanation"):
                lines.append(f"> {q['explanation']}")
            lines.append("")

    return "\n".join(lines)




@app.post("/api/research")
def research(req: ResearchRequest):
    page = wikipedia_search(req.topic)
    metrics = calculate_reading_metrics(page["content"])
    related = fetch_related_wiki_topics(page["title"])
    return {
        "title": page["title"],
        "summary": page["summary"],
        "content": page["content"],
        "url": page["url"],
        "reading_metrics": metrics,
        "related_topics": related,
    }


@app.post("/api/explain")
def explain(req: ExplainRequest):
    if not os.getenv("GROQ_API_KEY"):
        raise HTTPException(500, "GROQ_API_KEY is not set on the server (.env file).")
    return generate_persona_explanation(req.topic, req.article_text, req.mode)


@app.post("/api/quiz")
def quiz(req: QuizRequest):
    if not os.getenv("GROQ_API_KEY"):
        raise HTTPException(500, "GROQ_API_KEY is not set on the server (.env file).")
    return {"quiz": generate_study_quiz(req.article_text, req.mode, req.num_questions)}


@app.post("/api/export")
def export(req: ExportRequest):
    markdown = export_study_deck_markdown(req)
    filename = re.sub(r"[^a-zA-Z0-9]+", "_", req.topic).strip("_") + "_study_deck.md"
    return PlainTextResponse(
        markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )




FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
