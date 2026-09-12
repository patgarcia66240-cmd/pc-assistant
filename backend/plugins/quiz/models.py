"""Database models for reusable quiz questions."""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text

from models.conversation import Base


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(String, primary_key=True)
    theme = Column(String, nullable=False, index=True)
    question_type = Column(String, nullable=False, index=True)
    difficulty = Column(String, nullable=False, index=True)
    prompt = Column(Text, nullable=False)
    choices = Column(Text, nullable=False)
    correct_answer = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False, default="")
    times_used = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class SavedQuiz(Base):
    __tablename__ = "saved_quizzes"

    id = Column(String, primary_key=True)
    theme = Column(String, nullable=False, index=True)
    question_type = Column(String, nullable=False, index=True)
    difficulty = Column(String, nullable=False, index=True)
    question_ids = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
