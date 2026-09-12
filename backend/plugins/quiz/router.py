"""Routes for generating, storing and replaying ARIA quizzes."""
import json
import logging
import re
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from config import settings
from db import async_session
from plugins.quiz.models import QuizQuestion, SavedQuiz
from services.claude_service import claude_service


logger = logging.getLogger(__name__)
router = APIRouter()

QuizType = Literal["qcm", "true_false"]
Difficulty = Literal["facile", "moyen", "difficile"]


class QuizRequest(BaseModel):
    theme: str = Field(min_length=2, max_length=80)
    question_type: QuizType = "qcm"
    difficulty: Difficulty = "facile"
    count: int = Field(default=5, ge=1, le=20)


def _extract_json_array(text: str) -> list[dict]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start < 0 or end <= start:
        raise ValueError("La réponse IA ne contient pas de tableau JSON")
    payload = json.loads(cleaned[start : end + 1])
    if not isinstance(payload, list):
        raise ValueError("Le quiz généré n'est pas une liste")
    return payload


def _validate_generated_questions(items: list[dict], request: QuizRequest) -> list[dict]:
    if len(items) != request.count:
        raise ValueError(f"ARIA a généré {len(items)} questions au lieu de {request.count}")

    expected_choices = ["Vrai", "Faux"] if request.question_type == "true_false" else None
    validated = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Question {index} invalide")
        prompt = str(item.get("question", "")).strip()
        explanation = str(item.get("explanation", "")).strip()
        choices = item.get("choices")
        correct_answer = str(item.get("correct_answer", "")).strip()
        if not prompt or not isinstance(choices, list):
            raise ValueError(f"Question {index} incomplète")
        choices = [str(choice).strip() for choice in choices if str(choice).strip()]
        if expected_choices:
            if choices != expected_choices:
                raise ValueError(f"Question {index} doit proposer Vrai puis Faux")
        elif len(choices) != 4 or len(set(choices)) != 4:
            raise ValueError(f"Question {index} doit proposer quatre réponses différentes")
        if correct_answer not in choices:
            raise ValueError(f"Réponse correcte absente des choix pour la question {index}")
        validated.append(
            {
                "question": prompt,
                "choices": choices,
                "correct_answer": correct_answer,
                "explanation": explanation,
            }
        )
    return validated


def _question_payload(question: QuizQuestion) -> dict:
    return {
        "id": question.id,
        "theme": question.theme,
        "question_type": question.question_type,
        "difficulty": question.difficulty,
        "question": question.prompt,
        "choices": json.loads(question.choices),
        "correct_answer": question.correct_answer,
        "explanation": question.explanation,
    }


def _saved_quiz_payload(quiz: SavedQuiz) -> dict:
    return {
        "id": quiz.id,
        "theme": quiz.theme,
        "question_type": quiz.question_type,
        "difficulty": quiz.difficulty,
        "count": len(json.loads(quiz.question_ids)),
        "created_at": quiz.created_at.isoformat(),
    }


async def _backfill_saved_quizzes(session) -> None:
    saved_quizzes = list((await session.scalars(select(SavedQuiz))).all())
    assigned_question_ids = {
        question_id
        for quiz in saved_quizzes
        for question_id in json.loads(quiz.question_ids)
    }
    questions = list(
        (
            await session.scalars(
                select(QuizQuestion)
                .where(QuizQuestion.id.not_in(assigned_question_ids))
                .order_by(QuizQuestion.created_at, QuizQuestion.id)
            )
        ).all()
    )
    if not questions:
        return

    groups: list[list[QuizQuestion]] = []
    for question in questions:
        if not groups:
            groups.append([question])
            continue
        previous = groups[-1][-1]
        same_quiz_config = (
            question.theme == previous.theme
            and question.question_type == previous.question_type
            and question.difficulty == previous.difficulty
        )
        created_together = (question.created_at - previous.created_at).total_seconds() <= 1
        if same_quiz_config and created_together:
            groups[-1].append(question)
        else:
            groups.append([question])

    session.add_all(
        [
            SavedQuiz(
                id=str(uuid4()),
                theme=group[0].theme,
                question_type=group[0].question_type,
                difficulty=group[0].difficulty,
                question_ids=json.dumps([question.id for question in group]),
                created_at=group[0].created_at,
            )
            for group in groups
        ]
    )
    await session.commit()


async def _generate_with_aria(request: QuizRequest) -> list[dict]:
    if not claude_service.is_configured():
        raise HTTPException(status_code=503, detail="Le fournisseur IA n'est pas configuré pour générer le quiz")

    choice_instruction = (
        'choices doit être exactement ["Vrai", "Faux"].'
        if request.question_type == "true_false"
        else "choices doit contenir exactement quatre réponses courtes et différentes."
    )
    prompt = f"""
Crée exactement {request.count} questions de quiz en français.
Thème : {request.theme}
Type : {request.question_type}
Difficulté : {request.difficulty}

Réponds uniquement avec un tableau JSON valide. Chaque élément doit avoir exactement ces clés :
question, choices, correct_answer, explanation.
{choice_instruction}
correct_answer doit reprendre exactement une valeur de choices.
Les questions doivent être factuelles, non ambiguës et sans doublon.
""".strip()
    response = await claude_service.generate(
        prompt,
        system="Tu crées des quiz factuels en français et tu réponds uniquement en JSON valide.",
        max_tokens=4096,
    )
    if not response:
        raise ValueError("ARIA n'a renvoyé aucun contenu")
    return _validate_generated_questions(_extract_json_array(response), request)


async def generate_and_store_quiz(request: QuizRequest) -> list[QuizQuestion]:
    try:
        generated = await _generate_with_aria(request)
    except HTTPException:
        raise
    except (AttributeError, json.JSONDecodeError, TypeError, ValueError) as error:
        logger.warning("Quiz ARIA invalide : %s", error)
        raise HTTPException(status_code=502, detail=f"Quiz généré invalide : {error}") from error

    theme = request.theme.strip()
    questions = [
        QuizQuestion(
            id=str(uuid4()),
            theme=theme,
            question_type=request.question_type,
            difficulty=request.difficulty,
            prompt=item["question"],
            choices=json.dumps(item["choices"], ensure_ascii=False),
            correct_answer=item["correct_answer"],
            explanation=item["explanation"],
        )
        for item in generated
    ]
    async with async_session() as session:
        session.add_all(questions)
        session.add(
            SavedQuiz(
                id=str(uuid4()),
                theme=theme,
                question_type=request.question_type,
                difficulty=request.difficulty,
                question_ids=json.dumps([question.id for question in questions]),
            )
        )
        await session.commit()
    return questions


@router.post("/generate")
async def generate_quiz(request: QuizRequest):
    questions = await generate_and_store_quiz(request)
    return {"questions": [_question_payload(question) for question in questions], "stored": len(questions)}


@router.get("/play")
async def play_stored_quiz(
    theme: str = Query(min_length=2, max_length=80),
    question_type: QuizType = "qcm",
    difficulty: Difficulty = "facile",
    count: int = Query(default=5, ge=1, le=20),
):
    async with async_session() as session:
        statement = (
            select(QuizQuestion)
            .where(
                func.lower(QuizQuestion.theme) == theme.strip().lower(),
                QuizQuestion.question_type == question_type,
                QuizQuestion.difficulty == difficulty,
            )
            .order_by(func.random())
            .limit(count)
        )
        questions = list((await session.scalars(statement)).all())
        if len(questions) < count:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Seulement {len(questions)} question(s) disponible(s). "
                    "Générez d'abord de nouvelles questions avec ARIA."
                ),
            )
        for question in questions:
            question.times_used += 1
        await session.commit()
    return {"questions": [_question_payload(question) for question in questions]}


@router.post("/next")
async def play_next_quiz(request: QuizRequest):
    async with async_session() as session:
        await _backfill_saved_quizzes(session)
        candidates = list(
            (
                await session.scalars(
                    select(SavedQuiz)
                    .where(
                        func.lower(SavedQuiz.theme) == request.theme.strip().lower(),
                        SavedQuiz.question_type == request.question_type,
                        SavedQuiz.difficulty == request.difficulty,
                    )
                    .order_by(func.random())
                )
            ).all()
        )
        quiz = next(
            (
                candidate
                for candidate in candidates
                if len(json.loads(candidate.question_ids)) == request.count
            ),
            None,
        )
        if quiz is not None:
            question_ids = json.loads(quiz.question_ids)
            questions = list(
                (
                    await session.scalars(
                        select(QuizQuestion).where(QuizQuestion.id.in_(question_ids))
                    )
                ).all()
            )
            questions_by_id = {question.id: question for question in questions}
            if all(question_id in questions_by_id for question_id in question_ids):
                ordered_questions = [questions_by_id[question_id] for question_id in question_ids]
                for question in ordered_questions:
                    question.times_used += 1
                await session.commit()
                return {
                    "source": "saved",
                    "quiz": _saved_quiz_payload(quiz),
                    "questions": [_question_payload(question) for question in ordered_questions],
                }

    questions = await generate_and_store_quiz(request)
    return {
        "source": "generated",
        "questions": [_question_payload(question) for question in questions],
    }


@router.get("/saved/{quiz_id}")
async def play_saved_quiz(quiz_id: str):
    async with async_session() as session:
        await _backfill_saved_quizzes(session)
        quiz = await session.get(SavedQuiz, quiz_id)
        if quiz is None:
            raise HTTPException(status_code=404, detail="Quiz sauvegardé introuvable")

        question_ids = json.loads(quiz.question_ids)
        questions = list(
            (
                await session.scalars(
                    select(QuizQuestion).where(QuizQuestion.id.in_(question_ids))
                )
            ).all()
        )
        questions_by_id = {question.id: question for question in questions}
        if any(question_id not in questions_by_id for question_id in question_ids):
            raise HTTPException(status_code=409, detail="Certaines questions de ce quiz sont introuvables")
        ordered_questions = [questions_by_id[question_id] for question_id in question_ids]
        for question in ordered_questions:
            question.times_used += 1
        await session.commit()
    return {"quiz": _saved_quiz_payload(quiz), "questions": [_question_payload(question) for question in ordered_questions]}


@router.get("/catalog")
async def quiz_catalog():
    async with async_session() as session:
        await _backfill_saved_quizzes(session)
        quizzes = list(
            (
                await session.scalars(
                    select(SavedQuiz).order_by(SavedQuiz.created_at.desc())
                )
            ).all()
        )
    return {"entries": [_saved_quiz_payload(quiz) for quiz in quizzes]}
