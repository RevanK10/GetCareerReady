import pytest

import cover
import db
import fit
import interviewer
import review
import tailor


class FakeLLM:
    """Stands in for LLMClient. Queue replies (or Exceptions to raise) and inspect what was sent."""

    text_replies = []
    json_replies = []
    prompts = []
    messages = []
    text_default = "stub reply"
    json_default = {}

    @classmethod
    def reset(cls):
        cls.text_replies, cls.json_replies = [], []
        cls.prompts, cls.messages = [], []
        cls.text_default, cls.json_default = "stub reply", {}

    @staticmethod
    def _next(queue, default):
        item = queue.pop(0) if queue else default
        if isinstance(item, Exception):
            raise item
        return item

    def generate(self, prompt, temperature=0.7):
        FakeLLM.prompts.append(prompt)
        return self._next(FakeLLM.text_replies, FakeLLM.text_default)

    def chat(self, messages, temperature=0.7):
        FakeLLM.messages.append(messages)
        return self._next(FakeLLM.text_replies, FakeLLM.text_default)

    def generate_json(self, prompt, temperature=0.2):
        FakeLLM.prompts.append(prompt)
        return self._next(FakeLLM.json_replies, FakeLLM.json_default)


@pytest.fixture
def fake_llm(monkeypatch):
    FakeLLM.reset()
    for module in (fit, tailor, review, cover, interviewer):
        monkeypatch.setattr(module, "LLMClient", FakeLLM)
    return FakeLLM


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    db.save_profile({"full_name": "Jane Doe", "resume_text": "resume " * 40})
    return db
