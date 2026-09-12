import asyncio
import json
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete

from db import async_session
from main import app
from plugins.quiz.chat_handler import _quiz_request, matches
from plugins.quiz.models import QuizQuestion, SavedQuiz
from plugins.quiz.router import QuizRequest, _extract_json_array, _validate_generated_questions
from services.claude_service import claude_service


def test_quiz_json_validation_accepts_qcm():
    request = QuizRequest(theme="Histoire", question_type="qcm", difficulty="facile", count=1)
    raw = """```json
    [{"question":"En quelle année débute la Révolution française ?",
      "choices":["1789","1815","1914","1945"],
      "correct_answer":"1789",
      "explanation":"La Révolution française débute en 1789."}]
    ```"""

    questions = _validate_generated_questions(_extract_json_array(raw), request)

    assert questions[0]["correct_answer"] == "1789"
    assert len(questions[0]["choices"]) == 4


def test_quiz_chat_request_extracts_configuration():
    request = _quiz_request("Fais-moi un quiz d'histoire difficile de 10 questions en vrai ou faux")

    assert matches("Je voudrais un quiz")
    assert request.theme.lower() == "histoire"
    assert request.difficulty == "difficile"
    assert request.question_type == "true_false"
    assert request.count == 10


def test_generate_quiz_stores_questions(monkeypatch):
    from config import settings

    theme = f"Test-{uuid4()}"
    generated = [
        {
            "question": "La Terre tourne-t-elle autour du Soleil ?",
            "choices": ["Vrai", "Faux"],
            "correct_answer": "Vrai",
            "explanation": "La Terre effectue sa révolution autour du Soleil.",
        }
    ]

    class FakeMessages:
        async def create(self, **_kwargs):
            return SimpleNamespace(
                content=[SimpleNamespace(text=json.dumps(generated, ensure_ascii=False))]
            )

    monkeypatch.setattr(settings, "AI_PROVIDER", "anthropic")
    monkeypatch.setattr(claude_service, "client", SimpleNamespace(messages=FakeMessages()))

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/quiz/generate",
                json={
                    "theme": theme,
                    "question_type": "true_false",
                    "difficulty": "facile",
                    "count": 1,
                },
            )
            assert response.status_code == 200
            assert response.json()["stored"] == 1

            catalog = client.get("/api/quiz/catalog")
            assert catalog.status_code == 200
            saved_quiz = next(
                entry for entry in catalog.json()["entries"] if entry["theme"] == theme
            )
            assert saved_quiz["count"] == 1

            saved_replay = client.get(f"/api/quiz/saved/{saved_quiz['id']}")
            assert saved_replay.status_code == 200
            assert saved_replay.json()["questions"][0]["correct_answer"] == "Vrai"

            next_series = client.post(
                "/api/quiz/next",
                json={
                    "theme": theme,
                    "question_type": "true_false",
                    "difficulty": "facile",
                    "count": 1,
                },
            )
            assert next_series.status_code == 200
            assert next_series.json()["source"] == "saved"
            assert next_series.json()["quiz"]["id"] == saved_quiz["id"]

            replay = client.get(
                "/api/quiz/play",
                params={
                    "theme": theme,
                    "question_type": "true_false",
                    "difficulty": "facile",
                    "count": 1,
                },
            )
            assert replay.status_code == 200
            assert replay.json()["questions"][0]["correct_answer"] == "Vrai"
    finally:
        async def cleanup():
            async with async_session() as session:
                await session.execute(delete(QuizQuestion).where(QuizQuestion.theme == theme))
                await session.execute(delete(SavedQuiz).where(SavedQuiz.theme == theme))
                await session.commit()

        asyncio.run(cleanup())
