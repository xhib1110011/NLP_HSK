"""Lưu và đọc kho câu hỏi dùng chung giữa các tài khoản."""

import hashlib
import json
import re
from pathlib import Path


QUESTION_BANK_DIR = (
    Path(__file__).resolve().parent.parent / "data" / "question_bank"
)
QUESTION_FIELDS = (
    "hsk_level",
    "topic",
    "question_type",
    "question",
    "options",
    "correct_option",
    "explanation",
)


def _question_key(question):
    text = re.sub(r"\s+", " ", question).strip().casefold()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_question_bank(conn, hsk_level):
    rows = conn.execute(
        """
        SELECT id, hsk_level, topic, question_type, question_text,
               options_json, correct_option, explanation
        FROM question_bank
        WHERE hsk_level = ?
        ORDER BY id
        """,
        (hsk_level,),
    ).fetchall()

    questions = []
    for row in rows:
        try:
            options = json.loads(row["options_json"])
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(options, dict):
            continue
        questions.append({
            "id": f"bank-{row['id']}",
            "hsk_level": row["hsk_level"],
            "topic": row["topic"],
            "question_type": row["question_type"],
            "question": row["question_text"],
            "options": options,
            "correct_option": row["correct_option"],
            "explanation": row["explanation"],
        })
    return questions


def save_questions_to_bank(conn, questions):
    """Lưu câu hỏi mới, bỏ qua câu đã có cùng cấp độ và nội dung."""
    inserted = 0
    with conn:
        for question in questions:
            text = question.get("question")
            options = question.get("options")
            if not isinstance(text, str) or not text.strip():
                continue
            if not isinstance(options, dict):
                continue

            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO question_bank
                (question_key, hsk_level, topic, question_type,
                 question_text, options_json, correct_option, explanation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _question_key(text),
                    question["hsk_level"],
                    question["topic"],
                    question.get("question_type", ""),
                    text.strip(),
                    json.dumps(options, ensure_ascii=False),
                    question["correct_option"],
                    question["explanation"],
                ),
            )
            inserted += cursor.rowcount
    return inserted


def export_question_bank_json(conn, hsk_level, output_dir=None):
    """Xuất riêng câu hỏi của một cấp ra JSON để đồng bộ qua GitHub.

    Không xuất ID nội bộ, tài khoản hay lịch sử làm bài trong SQLite.
    """
    if hsk_level not in range(1, 7):
        raise ValueError("HSK phải từ 1 đến 6.")

    output_dir = Path(output_dir or QUESTION_BANK_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"hsk_{hsk_level}.json"

    questions = get_question_bank(conn, hsk_level)
    portable_questions = [
        {field: question[field] for field in QUESTION_FIELDS}
        for question in questions
    ]

    temporary_path = output_path.with_suffix(".json.tmp")
    temporary_path.write_text(
        json.dumps(portable_questions, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(output_path)
    return output_path, len(portable_questions)


def import_question_bank_json(conn, hsk_level, input_dir=None):
    """Nhập bổ sung câu hỏi JSON vào SQLite; bỏ qua câu trùng đã có."""
    if hsk_level not in range(1, 7):
        raise ValueError("HSK phải từ 1 đến 6.")

    input_dir = Path(input_dir or QUESTION_BANK_DIR)
    input_path = input_dir / f"hsk_{hsk_level}.json"
    if not input_path.exists():
        return 0, 0

    try:
        questions = json.loads(input_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Không đọc được kho câu hỏi {input_path}: {error}") from error

    if not isinstance(questions, list):
        raise ValueError(f"Kho câu hỏi phải là một danh sách JSON: {input_path}")

    valid_questions = []
    for question in questions:
        if not isinstance(question, dict):
            continue
        if question.get("hsk_level") != hsk_level:
            continue
        if not isinstance(question.get("question"), str):
            continue
        if not isinstance(question.get("options"), dict):
            continue
        if question.get("correct_option") not in question["options"]:
            continue
        if not isinstance(question.get("topic"), str):
            continue

        valid_questions.append({
            "hsk_level": hsk_level,
            "topic": question["topic"],
            "question_type": question.get("question_type", ""),
            "question": question["question"],
            "options": question["options"],
            "correct_option": question["correct_option"],
            "explanation": question.get("explanation", ""),
        })

    inserted = save_questions_to_bank(conn, valid_questions)
    return len(valid_questions), inserted
