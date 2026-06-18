import json
from pathlib import Path
from typing import Optional
from app.utils.logger import debug_log


class KnowledgeService:

    def __init__(self, max_question_length: int = 200):
        file_path = (
            Path(__file__).resolve().parent.parent
            / "data"
            / "knowledge_base.json"
        )
        with open(file_path, "r", encoding="utf-8") as f:
            self.knowledge = json.load(f)

        self.questions: list[str] = []
        self.answer_map: dict[str, dict[str, str]] = {}
        self.keywords_map: dict[str, set[str]] = {}
        self.priority_map: dict[str, str] = {}
        self.max_question_length = max_question_length
        self._prepare()

    def _prepare(self):
        for section in self.knowledge.values():
            for item in section:
                q = self._normalize(item["question"])
                self.questions.append(q)
                self.answer_map[q] = {
                    "ar": item["answer"],
                    "en": item.get("answer_en", item["answer"]),
                }
                # Store keywords if available
                keywords = item.get("keywords", [])
                if keywords:
                    self.keywords_map[q] = set(self._normalize(k) for k in keywords)

                # Store priority if available
                priority = item.get("priority", "medium")
                self.priority_map[q] = priority

                if item.get("question_en"):
                    q_en = self._normalize(item["question_en"])
                    self.questions.append(q_en)
                    self.answer_map[q_en] = self.answer_map[q]
                    if keywords:
                        self.keywords_map[q_en] = self.keywords_map[q]
                    self.priority_map[q_en] = priority

    def reload(self):
        """Reload knowledge_base.json without restarting the service."""
        file_path = (
            Path(__file__).resolve().parent.parent
            / "data"
            / "knowledge_base.json"
        )
        with open(file_path, "r", encoding="utf-8") as f:
            self.knowledge = json.load(f)

        self.questions.clear()
        self.answer_map.clear()
        self.keywords_map.clear()
        self.priority_map.clear()
        self._prepare()
        debug_log("KNOWLEDGE_RELOAD", "Knowledge base reloaded successfully")

    def _normalize(self, text: str) -> str:
        return (
            text.lower().strip()
            .replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
            .replace("ة", "ه").replace("ى", "ي")
        )

    def _answer_for(self, question: str, lang: str) -> str:
        answer = self.answer_map[question]
        return answer.get(lang) or answer["ar"]

    def find_answer(self, message: str, lang: str = "ar") -> Optional[str]:
        # Check max length - skip KB if question is too long
        if len(message) > self.max_question_length:
            debug_log("KNOWLEDGE SKIP", f"Question too long ({len(message)} chars)")
            return None

        msg_norm = self._normalize(message)

        # Priority order for matching
        priority_order = {"high": 0, "medium": 1, "low": 2}

        # Sort questions by priority
        sorted_questions = sorted(
            self.questions,
            key=lambda q: priority_order.get(self.priority_map.get(q, "medium"), 1)
        )

        # 1. Exact / substring match - fastest and most accurate
        for q in sorted_questions:
            if msg_norm in q or q in msg_norm:
                debug_log("KNOWLEDGE EXACT", q)
                return self._answer_for(q, lang)

        # 2. Keyword overlap using stored keywords
        msg_words = set(msg_norm.split())
        best_q = None
        best_overlap = 0

        # First try with explicit keywords, prioritized by question priority
        for q in sorted_questions:
            if q in self.keywords_map:
                keywords = self.keywords_map[q]
                overlap = len(msg_words & keywords)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_q = q

        if best_overlap >= 2:
            debug_log("KNOWLEDGE KEYWORD", best_q)
            return self._answer_for(best_q, lang)

        # 3. Fallback to question word overlap if no keywords matched
        for q in sorted_questions:
            q_words = set(q.split())
            overlap = len(msg_words & q_words)
            if overlap > best_overlap:
                best_overlap = overlap
                best_q = q

        if best_overlap >= 2:
            debug_log("KNOWLEDGE WORD_OVERLAP", best_q)
            return self._answer_for(best_q, lang)

        # No match found
        debug_log("KNOWLEDGE NO_MATCH", "No suitable match found")
        return None
