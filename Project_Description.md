# Wikipedia Research & Quick Summary Assistant — Project Description

## Overview

The Wikipedia Research & Quick Summary Assistant is an interactive study
tool that turns any Wikipedia article into a structured, personalized study
resource in seconds. A user enters a topic and chooses how they want it
explained — **Beginner (ELI5)** or **Academic** — and the system retrieves
the live article, rewrites it at the right depth, analyzes its readability,
surfaces related topics, and can generate a grounded multiple-choice quiz.
Everything can be exported as a single downloadable Markdown study deck.

## Problem it Solves

Wikipedia articles are dense, unstructured, and written for one generic
audience. Students who want a quick, level-appropriate overview — plus a way
to test what they've learned — have to do all of that manually: reading,
summarizing, defining terms, and writing their own quiz questions. This
project automates that entire workflow.

## Key Capabilities

| Capability | What it does |
|---|---|
| **Wikipedia Retrieval** | Fetches the live, full-text Wikipedia article for any topic, handling ambiguous or missing pages gracefully. |
| **Persona-Aware Explanation** | An LLM rewrites the article's summary, key takeaways, and vocabulary — in plain, everyday language for Beginner mode, or precise academic language for Academic mode. |
| **Reading Metrics** | A deterministic (non-AI) tool calculates word count, estimated reading time (200 WPM), and a complexity rating directly from the article text. |
| **Related Topics** | Surfaces 3–5 related Wikipedia topics to guide further exploration. |
| **Study Quiz Generation** | An LLM generates multiple-choice questions — with answer keys and explanations — strictly grounded in the retrieved article, so no outside or hallucinated facts. |
| **Exportable Study Deck** | Compiles the summary, takeaways, vocabulary, reading metrics, related topics, and quiz into one downloadable `.md` file. |

## How It Works

1. The user submits a topic and selects a mode (Beginner or Academic).
2. The **FastAPI backend** retrieves the article from Wikipedia and computes
   reading metrics and related topics locally — no AI involved for this part.
3. The backend calls the **Groq-hosted LLM** to generate a persona-styled
   summary, takeaways, and vocabulary, grounded strictly in the retrieved
   article.
4. On request, the same LLM generates a study quiz from the article.
5. The user can download everything as a single Markdown study deck.

## Tech Stack

- **AI & Agent Core:** Python, Groq API, Wikipedia library
- **Backend:** FastAPI, Pydantic, Uvicorn
- **Frontend:** Vanilla JavaScript (ES6+ / `fetch`), HTML5, CSS3

## Outcome

The result is a lightweight, self-contained full-stack application that
demonstrates practical use of LLM-backed content generation grounded in a
real, verifiable source — combined with fast, deterministic tooling where an
LLM isn't needed — to turn passive reading into an active study workflow.
