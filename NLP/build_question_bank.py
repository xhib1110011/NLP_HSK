"""Tạo trước câu hỏi HSK và lưu vào kho dùng chung của ứng dụng.

Chạy thủ công trên máy có Ollama, ví dụ:
    python build_question_bank.py --level 3 --target 20
"""

import argparse
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from database.connection import get_connection, init_database
from services.question_bank_service import (
    export_question_bank_json,
    get_question_bank,
    save_questions_to_bank,
)
from services.question_service import generate_quiz


def main():
    parser = argparse.ArgumentParser(
        description="Sinh câu hỏi HSK bằng Ollama rồi lưu vào kho SQLite."
    )
    parser.add_argument(
        "--level", type=int, choices=range(1, 7), required=True,
        help="Cấp độ HSK cần nạp (1–6).",
    )
    parser.add_argument(
        "--target", type=int, default=20,
        help="Tổng số câu mong muốn trong kho cấp độ này (mặc định: 20).",
    )
    parser.add_argument(
        "--ai-review", action="store_true",
        help="Bật thêm lượt Ollama rà soát ngữ nghĩa; sẽ chạy lâu hơn.",
    )
    args = parser.parse_args()

    if args.target < 1:
        parser.error("--target phải lớn hơn 0.")

    init_database()
    with get_connection() as conn:
        existing = get_question_bank(conn, args.level)
        export_path, exported_count = export_question_bank_json(
            conn, args.level
        )
    total = len(existing)
    print(
        f"Đã đồng bộ {exported_count} câu ra {export_path.relative_to(PROJECT_DIR)}."
    )

    if total >= args.target:
        print(
            f"Kho HSK {args.level} đã có {total} câu; "
            f"đạt mục tiêu {args.target}, không cần sinh thêm."
        )
        return

    total_inserted = 0
    # Mỗi câu là một request ngắn hơn và được lưu ngay, tránh một request
    # sinh nhiều câu vượt quá thời gian chờ trên máy chạy Ollama.
    batch_size = 1
    while total < args.target:
        missing = args.target - total
        request_count = min(batch_size, missing)

        print(
            f"Kho HSK {args.level} có {total}/{args.target} câu; "
            f"đang sinh nhóm {request_count} câu."
        )
        additions = generate_quiz(
            PROJECT_DIR,
            args.level,
            request_count,
            ai_review=args.ai_review,
            existing_questions=[
                question["question"] for question in existing
            ],
            allow_partial=True,
        )

        with get_connection() as conn:
            inserted = save_questions_to_bank(conn, additions)
            existing = get_question_bank(conn, args.level)
            total = len(existing)
            export_path, exported_count = export_question_bank_json(
                conn, args.level
            )

        total_inserted += inserted
        print(f"Đã lưu thêm {inserted} câu; kho hiện có {total} câu.")
        print(
            f"Đã cập nhật {export_path.relative_to(PROJECT_DIR)} "
            f"({exported_count} câu)."
        )
        if inserted == 0:
            print("Không có câu mới hợp lệ để lưu; dừng các lượt bổ sung.")
            break

    print(f"Tổng số câu mới lưu trong lần chạy này: {total_inserted}.")
    if total < args.target:
        print(
            f"Kho HSK {args.level} hiện có {total}/{args.target} câu. "
            "Chạy lại cùng lệnh để sinh tiếp phần còn thiếu."
        )
    else:
        print(
            f"Kho HSK {args.level} hiện có {total} câu; "
            f"đã đạt mục tiêu {args.target}."
        )


if __name__ == "__main__":
    main()
