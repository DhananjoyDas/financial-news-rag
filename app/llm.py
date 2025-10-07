"""LLM adapter layer.

Provides a deterministic `MockLLM` for tests and a thin `OpenAILLM` wrapper
for production usage when `LLM_PROVIDER=openai` is set.
"""

import os
from abc import ABC, abstractmethod
from typing import Optional

# Optionally import OpenAI only if needed
try:
    from openai import OpenAI  # openai>=1.0 style
except Exception:
    OpenAI = None  # keeps local tests clean

class LLMClient(ABC):
    """Abstract LLM interface so the app and tests don't care about the provider."""
    @abstractmethod
    def complete(self, prompt: str, *, system: Optional[str] = None) -> str:
        ...

class MockLLM(LLMClient):
    """
    Deterministic offline LLM:
    - If 'CONTEXT' contains lines, it returns a short answer that quotes the first sentence fragment
      and then formats 2–3 Sources based on a simple pattern we pass in.
    - If context looks empty, returns the fallback.
    """
    def complete(self, prompt: str, *, system: Optional[str] = None) -> str:
        # Extremely simple parse: find CONTEXT section and harvest up to 3 titles/links.
        ctx = prompt.split("CONTEXT", 1)[-1]
        lines = [l.strip() for l in ctx.splitlines() if l.strip()]
        # Detect empty/low-signal context
        if len(lines) < 2:
            return "Sorry, I don’t know based on the provided (cleaned) news dataset."
        # Find the first non-header content line to quote
        content_line = next((l for l in lines if l and not l.upper().startswith("CONTEXT")), "")
        quote = content_line[:80].strip().strip(":;,.")
        # Gather sources from lines starting with [Title] pattern (our retriever will provide that)
        sources = []
        for l in lines:
            if l.startswith("[") and "]" in l:
                # expected format: [Title] some text ... (link: URL)
                title = l.split("]", 1)[0].lstrip("[").strip()
                link = ""
                if "(link:" in l:
                    link = l.split("(link:", 1)[-1].split(")", 1)[0].strip()
                sources.append((title, link))
        sources = sources[:3] or [("Dataset", "#")]
        src_str = "\n".join(f"- {t} — {u or '#'}" for t, u in sources)

        return f"""{quote}
Sources:
{src_str}"""

class OpenAILLM(LLMClient):
    """
    Thin OpenAI wrapper. Flip via env:
      LLM_PROVIDER=openai
      OPENAI_API_KEY=...
    """
    def __init__(self, model: str = None):
        if OpenAI is None:
            raise RuntimeError("OpenAI SDK not available. Install openai>=1.0.")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        self.client = OpenAI(api_key=api_key)
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def complete(self, prompt: str, *, system: Optional[str] = None) -> str:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        # Debug: persist the outgoing messages payload (no API key written)
        try:
            import json

            open("/tmp/last_openai_messages.json", "w", encoding="utf-8").write(
                json.dumps({"model": self.model, "messages": msgs, "prompt_len": len(prompt)}, ensure_ascii=False, indent=2)
            )
        except Exception:
            pass

        resp = self.client.chat.completions.create(model=self.model, messages=msgs, temperature=0.2)
        # Persist the model's raw response for debugging (avoid writing secrets)
        try:
            content = resp.choices[0].message.content.strip()
        except Exception:
            # Fallback if shape is unexpected
            try:
                content = str(resp)
            except Exception:
                content = ""

        try:
            import json

            wrapper = {"content": content}
            # Attempt to include a JSON-serializable version of resp if available
            if hasattr(resp, "model_dump"):
                try:
                    wrapper["resp_json"] = resp.model_dump()
                except Exception:
                    wrapper["resp_repr"] = repr(resp)
            else:
                wrapper["resp_repr"] = repr(resp)

            open("/tmp/last_openai_response.json", "w", encoding="utf-8").write(json.dumps(wrapper, ensure_ascii=False, indent=2))
            open("/tmp/last_openai_response.txt", "w", encoding="utf-8").write(content)
        except Exception:
            pass

        return content
