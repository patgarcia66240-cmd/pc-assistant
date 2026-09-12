"""Chat integration for interactive, reusable quizzes."""
import re

from plugins.quiz.router import QuizRequest, _question_payload, generate_and_store_quiz


def matches(message: str) -> bool:
    return bool(re.search(r"\bquiz(?:z)?\b", message, flags=re.IGNORECASE))


def _quiz_request(message: str) -> QuizRequest:
    lowered = message.lower()
    count_match = re.search(r"\b([1-9]|1\d|20)\s+questions?\b", lowered)
    count = int(count_match.group(1)) if count_match else 5
    question_type = "true_false" if re.search(r"vrai\s*(?:ou|/)\s*faux|oui\s*(?:ou|/)\s*non", lowered) else "qcm"
    difficulty = next(
        (value for value in ("facile", "moyen", "difficile") if value in lowered),
        "facile",
    )

    theme = "Culture générale"
    theme_match = re.search(
        r"\bquiz(?:z)?\s+(?:sur\s+|de\s+|d['’]\s*)([^,.!?]+)",
        message,
        flags=re.IGNORECASE,
    )
    if theme_match:
        candidate = re.split(
            r"\b(?:facile|moyen|difficile|qcm|vrai\s*(?:ou|/)\s*faux|oui\s*(?:ou|/)\s*non|\d+\s+questions?)\b",
            theme_match.group(1),
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip(" -")
        if candidate:
            theme = candidate[:80]

    return QuizRequest(
        theme=theme,
        question_type=question_type,
        difficulty=difficulty,
        count=count,
    )


async def handle(message: str, context: dict) -> dict:
    request = _quiz_request(message)
    questions = await generate_and_store_quiz(request)
    return {
        "response": (
            f"Voici un quiz interactif de {request.count} questions sur « {request.theme} » "
            f"({request.difficulty}). Sélectionne une réponse pour commencer."
        ),
        "data": {
            "config": request.model_dump(),
            "questions": [_question_payload(question) for question in questions],
        },
        "source": "local",
        "source_type": "quiz",
    }
