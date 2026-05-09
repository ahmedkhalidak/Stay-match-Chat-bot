import json
import difflib

from pathlib import Path


class KnowledgeService:

    def __init__(self):

        file_path = (
            Path(__file__)
            .resolve()
            .parent.parent
            / "data"
            / "knowledge_base.json"
        )

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:

            self.knowledge = json.load(
                file
            )

        self.questions = []

        self.question_answer_map = {}

        self._prepare_knowledge()

    # ──────────────────────────────────────
    # Prepare Knowledge
    # ──────────────────────────────────────

    def _prepare_knowledge(self):

        for section in (
            self.knowledge.values()
        ):

            for item in section:

                question = (
                    item["question"]
                    .lower()
                    .strip()
                )

                answer = (
                    item["answer"]
                )

                self.questions.append(
                    question
                )

                self.question_answer_map[
                    question
                ] = answer

    # ──────────────────────────────────────
    # Search Answer
    # ──────────────────────────────────────

    def find_answer(
        self,
        message: str,
    ):

        message = (
            message
            .lower()
            .strip()
        )

        matches = (
            difflib.get_close_matches(
                message,
                self.questions,
                n=1,
                cutoff=0.55,
            )
        )

        if not matches:

            return None

        best_match = matches[0]

        return (
            self.question_answer_map[
                best_match
            ]
        )