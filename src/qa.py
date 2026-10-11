"""Hỏi–đáp pháp luật trên nền RAG.

Quy trình: truy hồi điều luật liên quan, dựng prompt kèm trích dẫn, sinh câu trả lời bằng LLM.
Prompt ràng buộc mô hình chỉ trả lời theo trích đoạn và luôn dẫn nguồn (hạn chế bịa).
"""
import os, sys
from pathlib import Path
# Chạy được từ thư mục bất kỳ: nạp mã nguồn trong src/ và lấy gốc dự án làm thư mục làm việc.
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
os.chdir(_ROOT)

import json
import urllib.request
from rag import Retriever

PROMPT_TEMPLATE = """Bạn là trợ lý pháp luật lao động Việt Nam. Chỉ trả lời dựa trên các trích đoạn luật dưới đây.
Nếu không đủ căn cứ, trả lời "Không tìm thấy căn cứ trong tài liệu". Luôn dẫn nguồn theo định dạng (Văn bản, Điều X).
Không suy diễn số điều hoặc nội dung ngoài trích đoạn.

TRÍCH ĐOẠN LUẬT:
{context}

CÂU HỎI: {question}

TRẢ LỜI (ngắn gọn, kèm dẫn nguồn):"""


def build_prompt(question, hits):
    context = "\n".join(
        f"[{i+1}] ({h['doc']}, Điều {h['dieu']} — {h['tieu_de']}) {h['text']}"
        for i, h in enumerate(hits)
    )
    return PROMPT_TEMPLATE.format(context=context, question=question)


def ollama_generate(prompt, model="qwen2.5:7b", host="http://localhost:11434"):
    """Gọi mô hình cục bộ qua Ollama. temperature=0 để kết quả ổn định."""
    req = urllib.request.Request(
        host + "/api/generate",
        data=json.dumps({
            "model": model, "prompt": prompt, "stream": False,
            "options": {"temperature": 0},
        }).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())["response"].strip()


def answer(question, retriever, k=3, model=None):
    hits = retriever.search(question, k=k)
    prompt = build_prompt(question, hits)
    cites = [f"({h['doc']}, Điều {h['dieu']})" for h in hits]
    if model:
        return {"answer": ollama_generate(prompt, model), "cites": cites, "hits": hits}
    return {"answer": None, "prompt": prompt, "cites": cites, "hits": hits}


if __name__ == "__main__":
    retriever = Retriever(backend="st").build("data/law/chunks_v3.json")
    q = "Thời gian thử việc tối đa cho vị trí yêu cầu trình độ đại học là bao nhiêu?"
    res = answer(q, retriever, k=6, model="qwen2.5:7b")
    print("CÂU HỎI:", q)
    print("\nCĂN CỨ:", ", ".join(res["cites"]))
    print("\nTRẢ LỜI:\n", res["answer"] if res.get("answer") else res["prompt"])
