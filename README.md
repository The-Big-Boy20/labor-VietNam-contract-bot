# Phát hiện sai phạm trong Hợp đồng lao động (HĐLĐ)

Hệ thống kiểm tra hợp đồng lao động Việt Nam theo hai tầng:

- **Tầng rule (Mốc 1)** — phát hiện Loại 1 (trái luật định lượng/từ khóa) và Loại 2 (thiếu điều khoản) bằng luật định lượng và từ khóa, kèm căn cứ pháp lý.
- **Tầng RAG + LLM (Mốc 2)** — truy hồi điều luật liên quan (retriever) để Hỏi–đáp có trích dẫn, và dùng mô hình ngôn ngữ cục bộ (Ollama/qwen2.5:7b) phát hiện Loại 3 (bất lợi) và Loại 4 (mập mờ).
- **Pipeline hybrid** — rule lo Loại 1–2, LLM lo Loại 3–4 trên những slot rule chưa gắn cờ.

## Cấu trúc thư mục

```
DAP_project/
├─ README.md                        tài liệu này
├─ requirements.txt                 thư viện Python cần cài
│
├─ config/
│  └─ thresholds.yaml               ngưỡng pháp lý (lương tối thiểu vùng, thử việc, làm thêm, thời hạn...)
│
├─ data/
│  ├─ contracts/
│  │  ├─ HD_001.docx … HD_050.docx  50 hợp đồng mẫu (đầu vào cho ingest)
│  │  ├─ HD_001.md   … HD_050.md    bản markdown nguồn của hợp đồng (ingest không dùng)
│  │  ├─ gold_answers.csv           nhãn chuẩn theo hợp đồng (bản trong contracts/)
│  │  └─ contracts_manifest.csv     phân loại hợp đồng + bucket (dùng chia dev/test)
│  ├─ law/
│  │  ├─ chunks_v3.json             kho điều luật đã cắt chunk (đầu vào cho retriever)
│  │  ├─ wage_zones_293.csv         bảng vùng lương tối thiểu theo NĐ 293/2025
│  │  ├─ law_sources.csv            danh mục văn bản luật nguồn
│  │  ├─ wage_zone_lookup.json, wage_zones_293_raw.txt, chunk_check.log   dữ liệu/log trung gian
│  ├─ gold_answers.csv              nhãn chuẩn (bản dùng trong code)
│  ├─ hdld_clauses_merged.csv       ngân hàng điều khoản gắn nhãn (few-shot cho LLM)
│  ├─ clauses_extracted.json        kết quả ingest đã lưu (sinh ra)
│  ├─ eda_summary.csv               số liệu khảo sát (sinh ra)
│  └─ error_analysis.csv            bảng lỗi từng ô (sinh ra bởi analysis.py / notebook)
│
├─ rule_engine/                     Tầng rule (Mốc 1)
│  ├─ ingest.py                     đọc .docx, cắt theo Điều
│  ├─ extract.py                    trích trường định lượng + ánh xạ slot + vùng lương
│  ├─ rules.py                      bộ rule (định lượng + từ khóa) + phân mốc rule
│  ├─ eval.py                       đánh giá P/R/F1, chia dev/test
│  ├─ analysis.py                   phân tích lỗi từng ô, xuất error_analysis.csv
│  ├─ build_nb.py                   dựng eval/eval_report.ipynb
│  └─ thresholds.yaml               bản sao ngưỡng (xem ghi chú trùng lặp bên dưới)
│
├─ src/                             Tầng RAG + LLM + hybrid (Mốc 2)
│  ├─ rag.py                        retriever (embedding tiếng Việt, lùi về TF-IDF)
│  ├─ qa.py                         Hỏi–đáp pháp luật có trích dẫn qua Ollama
│  ├─ detect_llm.py                 phát hiện mập mờ/bất lợi bằng LLM few-shot
│  ├─ analyze.py                    pipeline hybrid (rule + LLM) và đánh giá
│  └─ ingest.py, extract.py, rules.py, eval.py   dùng chung với rule_engine/ (xem ghi chú)
│
├─ eval/
│  ├─ eval_rag.py                   đo retriever: hit@1/hit@3/MRR
│  └─ eval_report.ipynb             báo cáo đánh giá rule engine (Mốc 1)
│
└─ notebook/
   ├─ 00_method_report.ipynb        báo cáo phương pháp: bài toán, I/O, workflow, thông số, tiêu chuẩn, baseline
   ├─ build_method_nb.py            script dựng lại 00_method_report.ipynb
   └─ eda_report.ipynb              khảo sát dữ liệu hợp đồng
```

## Cài đặt

```bash
pip install -r requirements.txt
# cho phần LLM: cài Ollama (https://ollama.com) rồi:
ollama pull qwen2.5:7b
```

## Cách chạy

Các script tự trỏ về gốc dự án nên chạy được từ thư mục bất kỳ.

```bash
# Tầng rule — đánh giá trên 50 hợp đồng (không cần Ollama)
python rule_engine/eval.py         # Precision/Recall/F1
python rule_engine/analysis.py     # phân tích lỗi, xuất data/error_analysis.csv

# Retriever — hit@1/hit@3/MRR (TF-IDF, không cần Ollama)
python eval/eval_rag.py

# Q&A pháp luật (cần Ollama chạy ở localhost:11434)
python src/qa.py

# Phát hiện mập mờ/bất lợi + pipeline hybrid (cần Ollama)
python src/detect_llm.py
python src/analyze.py

# Dựng lại / xem notebook
python rule_engine/build_nb.py                   # dựng lại eval/eval_report.ipynb
python notebook/build_method_nb.py               # dựng lại notebook/00_method_report.ipynb
jupyter notebook notebook/00_method_report.ipynb # báo cáo phương pháp (tổng quan)
jupyter notebook eval/eval_report.ipynb          # báo cáo Mốc 1 (rule)
jupyter notebook notebook/eda_report.ipynb       # khảo sát dữ liệu
```

## Kết quả tham chiếu

- Rule-only trên 50 HĐ: precision = 1.00, recall in-scope (Loại 1–2) = 1.00, recall mọi loại = 0.47, F1 = 0.64.
- Hybrid (rule + LLM) trên 50 HĐ: P = 1.00, R = 0.96, F1 = 0.98.
- Retriever (TF-IDF): hit@1 = 0.42, hit@3 = 0.75, MRR = 0.56.

Lưu ý về con số hybrid: precision 1.00 đạt được trên tập hợp đồng mẫu tương đối đồng nhất, với prompt được tinh chỉnh trên chính tập này. Đây là giới hạn trên lạc quan; cần tập kiểm thử diễn đạt khác để đánh giá khả năng tổng quát.

## Ghi chú kỹ thuật

- Phần LLM gọi mô hình cục bộ qua Ollama với `temperature=0`; không có kết nối ra ngoài.
- Retriever ưu tiên embedding tiếng Việt (`sentence-transformers`); nếu không tải được mô hình sẽ tự lùi về TF-IDF.
- Các module `ingest.py`, `extract.py`, `rules.py`, `eval.py` có bản sao giống hệt trong cả `rule_engine/` và `src/` để mỗi tầng chạy độc lập; `gold_answers.csv` và `thresholds.yaml` cũng có hai bản. Chạy vẫn đúng nhưng dễ lệch phiên bản — có thể gộp về một nơi sau.
- Dự án chưa kèm script sinh dữ liệu (tạo 50 hợp đồng mẫu, dựng `chunks_v3.json`) và chưa có entry point demo kiểm tra một hợp đồng đơn lẻ; các tệp dữ liệu đã sinh sẵn nằm trong `data/`.
