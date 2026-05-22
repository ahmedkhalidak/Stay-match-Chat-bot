
import json
from pathlib import Path
 
 
def load_faq_documents() -> list[dict]:
    """
    يحمّل knowledge_base.json ويرجع list من dicts:
    [{"id": "...", "text": "سؤال: ... جواب: ...", "answer": "..."}]
    """
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
            # نجمع السؤال والجواب في نص واحد عشان الـ embedding يكون أغنى
            text = f"سؤال: {item['question']} جواب: {item['answer']}"
            docs.append({
                "id": doc_id,
                "text": text,
                "answer": item["answer"],
                "question": item["question"],
                "section": section_name,
            })
 
    return docs
