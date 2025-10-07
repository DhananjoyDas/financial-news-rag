"""Small Gradio UI wrapper that calls the API `/chat` endpoint and renders
the model answer and citations.

This module is intentionally tiny: `ask_news` performs the HTTP call and
formats a short markdown citations list for display in the UI.
"""

import os

import gradio as gr
import requests

# API base used by the UI. Override with the NEWS_API_BASE env var.
API_BASE = os.getenv("NEWS_API_BASE", "http://localhost:8000")


def ask_news(question: str) -> tuple[str, str]:
    """Query the backend `/chat` endpoint and return (answer, citations_md).

    Returns a tuple of (answer_text, citations_markdown). On errors the answer
    contains an explanatory message and citations_md is the literal "—".
    """
    question = (question or "").strip()
    if not question:
        return "Please enter a question about the provided news dataset.", "—"

    try:
        resp = requests.post(
            f"{API_BASE}/chat", json={"question": question}, timeout=30
        )
        if resp.status_code != 200:
            return f"Error: {resp.status_code} {resp.text}", "—"
        try:
            js = resp.json()
        except ValueError:
            # Non-JSON response from the API
            return f"Error: non-JSON response from {API_BASE}/chat", "—"

        answer = js.get("answer", "").strip() or "(no answer)"
        cits = js.get("citations", []) or []

        # Build a friendly citations markdown
        if cits:
            lines = []
            for i, c in enumerate(cits, 1):
                t = c.get("title", "Untitled")
                u = c.get("link", "#")
                k = c.get("ticker", "")
                suffix = f" — {k}" if k else ""
                lines.append(f"{i}. [{t}]({u}){suffix}")
            citations_md = "**Sources**\n\n" + "\n".join(lines)
        else:
            citations_md = "No sources returned."

        return answer, citations_md
    except requests.RequestException as e:
        return f"Network error calling {API_BASE}/chat: {e}", "—"


with gr.Blocks(title="News RAG Chat") as demo:
    gr.Markdown(
        "### Financial News Q&A (RAG)\nAsk a question about the dataset; the app calls `/chat` and shows the model’s answer + sources."
    )
    with gr.Row():
        q = gr.Textbox(
            label="Your question",
            placeholder="e.g., What’s new with Apple this quarter?",
            lines=3,
        )
    with gr.Row():
        a = gr.Textbox(label="Answer (read-only)", lines=8, interactive=False)
    cites = gr.Markdown()

    btn = gr.Button("Ask")
    btn.click(fn=ask_news, inputs=q, outputs=[a, cites])

    gr.Examples(
        examples=[
            "What’s new with Apple this quarter?",
            "Summarize Amazon-related AI announcements.",
            "Summarize Amazon related announcements.",
            "Any recent IBM partnerships mentioned?",
        ],
        inputs=q,
    )

if __name__ == "__main__":
    # Launch on all interfaces so the app is reachable from a container.
    # In containers we bind to 0.0.0.0 and use port 7860 by default.
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
