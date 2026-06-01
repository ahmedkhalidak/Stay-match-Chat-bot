import json
from pathlib import Path


def load_faq_documents() -> list[dict]:
    file_path = (
        Path(__file__).resolve().parent.parent
        / "data"
        / "knowledge_base.json"
    )
    with open(file_path, "r", encoding="utf-8") as f:
        kb = json.load(f)

    docs = []
    for section_name, items in kb.items():
        for i, item in enumerate(items):
            doc_id = f"{section_name}_{i}"
            q = item["question"]
            a = item["answer"]
            # Rich bilingual embedding text for better cross-language matching
            text = f"سؤال: {q} جواب: {a} Question: {q} Answer: {a}"
            docs.append({
                "id": doc_id,
                "text": text,
                "answer": a,
                "answer_en": item.get("answer_en", a),
                "question": q,
                "question_en": item.get("question_en", q),
                "section": section_name,
            })

    return docs