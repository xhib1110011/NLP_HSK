"""Đồng bộ kho câu hỏi portable JSON với SQLite của ứng dụng.

Ví dụ:
    python .\NLP\sync_question_bank.py --direction export --level 3
    python .\NLP\sync_question_bank.py --direction import --level 3
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
    import_question_bank_json,
)


def main():
    parser = argparse.ArgumentParser(
        description="Xuất/nhập kho câu hỏi JSON, không đồng bộ tài khoản hoặc lịch sử."
    )
    parser.add_argument(
        "--direction",
        choices=("export", "import"),
        required=True,
        help="export: SQLite -> JSON; import: JSON -> SQLite (chỉ bổ sung, bỏ qua trùng).",
    )
    parser.add_argument(
        "--level",
        type=int,
        choices=range(1, 7),
        help="Cấp HSK cần đồng bộ; bỏ trống để chạy cả cấp 1–6.",
    )
    args = parser.parse_args()

    init_database()
    levels = [args.level] if args.level is not None else range(1, 7)
    with get_connection() as conn:
        for level in levels:
            if args.direction == "export":
                path, count = export_question_bank_json(conn, level)
                print(f"HSK {level}: đã xuất {count} câu -> {path}")
            else:
                valid_count, inserted = import_question_bank_json(conn, level)
                print(
                    f"HSK {level}: đọc {valid_count} câu hợp lệ, "
                    f"thêm mới {inserted} câu (câu trùng được bỏ qua)."
                )


if __name__ == "__main__":
    main()
