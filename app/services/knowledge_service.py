import json
import difflib
from pathlib import Path
from app.utils.logger import debug_log


class KnowledgeService:

    def __init__(self):
        file_path = (
            Path(__file__).resolve().parent.parent
            / "data"
            / "knowledge_base.json"
        )
        with open(file_path, "r", encoding="utf-8") as f:
            self.knowledge = json.load(f)

        self.questions: list[str] = []
        self.answer_map: dict[str, str] = {}
        self._prepare()

    def _prepare(self):
        for section in self.knowledge.values():
            for item in section:
                q = item["question"].lower().strip()
                self.questions.append(q)
                self.answer_map[q] = item["answer"]

    def _normalize(self, text: str) -> str:
        return (
            text.lower().strip()
            .replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
            .replace("ة", "ه").replace("ى", "ي")
        )

    def find_answer(self, message: str) -> str | None:
        msg_norm = self._normalize(message)

        # 1. Exact / substring match أسرع وأدق
        for q in self.questions:
            if msg_norm in q or q in msg_norm:
                debug_log("KNOWLEDGE EXACT", q)
                return self.answer_map[q]

        # 2. Keyword overlap — كام كلمة مشتركة
        msg_words = set(msg_norm.split())
        best_q = None
        best_overlap = 0

        for q in self.questions:
            q_words = set(q.split())
            overlap = len(msg_words & q_words)
            if overlap > best_overlap:
                best_overlap = overlap
                best_q = q

        if best_overlap >= 2:
            debug_log("KNOWLEDGE KEYWORD", best_q)
            return self.answer_map[best_q]

        # 3. Fuzzy match كـ fallback بـ  أعلى (0.65)
        matches = difflib.get_close_matches(
            msg_norm,
            self.questions,
            n=1,
            cutoff=0.65,  
        )

        if matches:
            debug_log("KNOWLEDGE FUZZY", matches[0])
            return self.answer_map[matches[0]]

        return None
