import json
import random
import re
from pathlib import Path
from uuid import uuid4

from services.validators import validate_question
from services.semantic_validator import (
    validate_semantics,
    validate_question_with_ai,
)
from llm.ollama_service import generate_text

QUESTION_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "question_type": {
                "type": "string",
                "enum": [
                    "Điền từ",
                    "Chọn câu hồi đáp",
                    "Đọc hiểu ngắn",
                    "Chọn câu đúng"
                ]
            },
            "topic": {
                "type": "string",
                "enum": ["Từ vựng", "Ngữ pháp"]
            },
            "question": {
                "type": "string"
            },
            "options": {
                "type": "object",
                "properties": {
                    "A": {"type": "string"},
                    "B": {"type": "string"},
                    "C": {"type": "string"},
                    "D": {"type": "string"}
                },
                "required": ["A", "B", "C", "D"],
                "additionalProperties": False
            },
            "correct_option": {
                "type": "string",
                "enum": ["A", "B", "C", "D"]
            },
            "explanation": {
                "type": "string"
            }
        },
        "required": [
            "question_type",
            "topic",
            "question",
            "options",
            "correct_option",
            "explanation"
        ],
        "additionalProperties": False
    }
}

# =====================================================
# 2. XỬ LÝ DỮ LIỆU
# =====================================================

def clean_meaning(text):
    """Làm sạch và rút gọn nghĩa tiếng Việt."""

    if not isinstance(text, str):
        return ""

    # Loại bỏ phần chú thích từ điển bắt đầu bằng LT:
    text = re.sub(r"/?LT:[^/]*", "", text)

    # Loại bỏ nội dung trong ngoặc vuông
    text = re.sub(r"\[[^\]]*\]", "", text)

    # Chuẩn hóa khoảng trắng
    text = re.sub(r"\s+", " ", text).strip()

    # Tách các nghĩa
    meanings = [
        part.strip(" ;,/ ")
        for part in text.split("/")
        if part.strip(" ;,/ ")
    ]

    # Loại bỏ nghĩa trùng lặp
    unique_meanings = []
    seen = set()

    for meaning in meanings:
        key = meaning.casefold()

        if key not in seen:
            seen.add(key)
            unique_meanings.append(meaning)

    # Giới hạn số nghĩa để prompt không quá dài
    return "; ".join(unique_meanings[:3])


def load_json(file_path):
    """Đọc dữ liệu JSON."""
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_vocab(project_dir, hsk_level):
    """Lọc từ vựng theo cấp độ HSK."""
    if hsk_level not in range(1, 7):
        raise ValueError("HSK phải từ 1 đến 6.")

    file_path = Path(project_dir) / "data" / "vocab_hsk.json"
    vocab_data = load_json(file_path)

    return [
        item for item in vocab_data
        if isinstance(item, dict)
        and hsk_level in item.get("levels", [])
    ]


def load_grammar(project_dir, hsk_level):
    """Lọc ngữ pháp theo cấp độ HSK."""
    if hsk_level not in range(1, 7):
        raise ValueError("HSK phải từ 1 đến 6.")

    file_path = Path(project_dir) / "data" / "grammar_hsk.json"
    grammar_data = load_json(file_path)

    return [
        item for item in grammar_data
        if isinstance(item, dict)
        and str(item.get("level")) == str(hsk_level)
    ]


def load_hsk_material(project_dir, hsk_level):
    """Tải đồng thời từ vựng và ngữ pháp."""
    return {
        "vocab": load_vocab(project_dir, hsk_level),
        "grammar": load_grammar(project_dir, hsk_level),
    }


def load_questions(project_dir, hsk_level):
    """Đọc câu hỏi mẫu theo cấp độ; có thể rỗng nếu cấp độ chưa có file."""
    if hsk_level not in range(1, 7):
        raise ValueError("HSK phải từ 1 đến 6.")

    file_path = Path(project_dir) / "data" / f"hsk{hsk_level}" / "questions.json"
    if not file_path.exists():
        return []

    questions = load_json(file_path)
    if not isinstance(questions, list):
        return []

    valid_questions = []
    for question in questions:
        if not isinstance(question, dict) or question.get("hsk_level") != hsk_level:
            continue
        is_valid, _ = validate_question(question)
        if is_valid:
            valid_questions.append(question)
    return valid_questions

# =====================================================
# 3. CHUẨN BỊ DỮ LIỆU CHO LLM
# =====================================================



def prepare_vocab_text(vocab, limit=20):
    """Chuẩn bị dữ liệu từ vựng cho LLM."""

    if not vocab:
        return "Không có dữ liệu từ vựng."

    valid_vocab = []

    for item in vocab:
        if not isinstance(item, dict):
            continue

        word = str(item.get("word", "")).strip()
        pinyin = str(item.get("pinyin", "")).strip()
        meaning = clean_meaning(item.get("meaning_vi", ""))

        if not word or not meaning:
            continue

        valid_vocab.append({
            "word": word,
            "pinyin": pinyin,
            "meaning": meaning
        })

    if not valid_vocab:
        return "Không có từ vựng hợp lệ."

    selected = random.sample(
        valid_vocab,
        min(limit, len(valid_vocab))
    )

    lines = []

    for item in selected:
        lines.append(
            f"- Từ: {item['word']} | "
            f"Pinyin: {item['pinyin']} | "
            f"Nghĩa: {item['meaning']}"
        )

    return "\n".join(lines)





def prepare_grammar_text(grammar, limit=10):
    """Chuẩn bị dữ liệu ngữ pháp cho LLM."""

    if not grammar:
        return "Không có dữ liệu ngữ pháp."

    valid_grammar = []

    for item in grammar:
        if not isinstance(item, dict):
            continue

        name = str(item.get("grammar", "")).strip()
        detail = str(
            item.get("grammar_detail", "")
        ).strip()

        examples = item.get("examples_cn", "")

        if not isinstance(examples, str):
            examples = ""

        examples = examples.replace("\\n", "\n")

        example_list = [
            line.strip()
            for line in examples.splitlines()
            if line.strip()
        ]

        if name and detail:
            valid_grammar.append({
                "name": name,
                "detail": detail,
            "examples": example_list[:2]
            })

    if not valid_grammar:
        return "Không có dữ liệu ngữ pháp hợp lệ."

    selected = random.sample(
        valid_grammar,
        min(limit, len(valid_grammar))
    )

    lines = []

    for item in selected:
        example_text = "\n".join(item["examples"])

        lines.append(
            f"Ngữ pháp: {item['name']}\n"
            f"Giải thích: {item['detail']}\n"
            f"Ví dụ:\n{example_text}"
        )

    return "\n\n".join(lines)


# =====================================================
# 4. ĐỌC JSON DO LLM TẠO
# =====================================================

def parse_questions(response):
    """Đọc mảng JSON từ phản hồi của LLM."""
    if not isinstance(response, str) or not response.strip():
        raise ValueError("LLM trả về nội dung rỗng.")

    cleaned = response.strip()
    cleaned = re.sub(
        r"```(?:json)?",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).replace("```", "").strip()

    decoder = json.JSONDecoder()

    for match in re.finditer(r"\[", cleaned):
        try:
            result, _ = decoder.raw_decode(cleaned[match.start():])
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            continue

    raise ValueError(
        "Không tìm thấy mảng JSON hợp lệ. "
        f"Phản hồi đầu tiên: {cleaned[:500]}"
    )


# =====================================================
# 5. TẠO PROMPT SINH CÂU HỎI
# =====================================================

def build_generation_prompt(
    hsk_level,
    num_questions,
    vocab_text,
    grammar_text,
    existing_questions=None,
):
    """Tạo prompt yêu cầu LLM sinh câu hỏi trắc nghiệm."""
    existing_questions = existing_questions or []

    existing_text = (
        "\n".join(f"- {question}" for question in existing_questions)
        if existing_questions
        else "Chưa có câu hỏi nào."
    )

    return f"""
Bạn là chuyên gia biên soạn đề thi HSK cho người Việt Nam.

NHIỆM VỤ:
Tạo chính xác {num_questions} câu hỏi trắc nghiệm HSK {hsk_level}.


QUY TẮC BẮT BUỘC VỀ DỮ LIỆU:
1. Kiến thức trọng tâm được kiểm tra phải thuộc từ vựng hoặc ngữ pháp trong dữ liệu tham khảo.
2. Được dùng từ nối và từ thông dụng đúng cấp độ HSK {hsk_level} để câu tiếng Trung tự nhiên.
3. Không dùng tiếng Anh.
4. Câu hỏi và phương án mô phỏng phần đọc HSK bằng tiếng Trung; giải thích viết bằng tiếng Việt có dấu.
5. Mỗi câu hỏi phải phù hợp với cấp độ HSK được yêu cầu.
6. Chỉ dùng kiến thức trọng tâm thuộc đúng cấp độ HSK đang chọn.


DỮ LIỆU TỪ VỰNG:
{vocab_text}

DỮ LIỆU NGỮ PHÁP:
{grammar_text}

CÁC CÂU ĐÃ ĐƯỢC THỬ SINH (TUYỆT ĐỐI KHÔNG LẶP LẠI):
{existing_text}

QUY ĐỊNH BẮT BUỘC:
1. Nội dung câu hỏi và phương án viết bằng tiếng Trung phù hợp cấp độ HSK.
2. Phần giải thích viết bằng tiếng Việt có dấu.
3. Không sử dụng tiếng Anh.
4. Chỉ kiến thức trọng tâm được kiểm tra phải có trong dữ liệu tham khảo; từ nối và từ thông dụng được dùng để tạo ngữ cảnh tự nhiên.
5. Mỗi câu hỏi phải rõ ràng, đủ ngữ cảnh và chỉ có một đáp án đúng.
6. Không lặp lại câu hỏi đã có trong danh sách.
7. Không tự tạo quy tắc ngữ pháp không có căn cứ.
8. Không để các phương án trùng nhau hoặc đồng nghĩa với nhau.
9. Bốn phương án phải cùng loại kiến thức để có thể so sánh.
10. Giải thích phải khớp với đáp án đúng.
11. Chỉ tạo câu thuộc chủ đề "Từ vựng" hoặc "Ngữ pháp".
12. Không biến tên ngữ pháp hoặc danh sách từ thành câu hỏi đơn giản.
13. Không hỏi nghĩa một từ riêng lẻ hoặc tên quy tắc ngữ pháp theo kiểu học thuộc.
14. Chỉ tạo dạng bài văn bản: điền từ, chọn câu hồi đáp, đọc hiểu ngắn hoặc chọn câu đúng.
15. HSK 1–2 ưu tiên câu ngắn và hội thoại đời sống; HSK 3–6 có thể dùng đoạn đọc ngắn phù hợp cấp độ.
16. Câu điền từ chỉ có một chỗ trống; câu hồi đáp phải có câu dẫn; câu đọc hiểu phải dựa trên thông tin có trong đoạn.
17. Các phương án phải cùng loại, chỉ có một đáp án đúng và không được chứa chữ Hán vô nghĩa.
18. Giải thích viết một câu ngắn bằng tiếng Việt, nêu căn cứ chọn đáp án.

CÁC DẠNG CÂU HỎI:
- "Điền từ": một chỗ trống trong câu tiếng Trung hoặc hội thoại ngắn.
- "Chọn câu hồi đáp": một câu hỏi/lời thoại tiếng Trung và bốn câu trả lời tiếng Trung.
- "Đọc hiểu ngắn": đoạn văn tiếng Trung ngắn và câu hỏi tìm thông tin trong đoạn.
- "Chọn câu đúng": bốn câu tiếng Trung cùng chủ điểm, chỉ một câu đúng theo dữ liệu.
Ứng dụng chưa có âm thanh/hình ảnh, vì vậy không tạo dạng câu cần nghe hoặc xem tranh.

ĐỊNH DẠNG:
Chỉ trả về một JSON ARRAY gồm chính xác {num_questions} phần tử.
Mỗi phần tử có đúng 6 trường:
- "question_type": "Điền từ", "Chọn câu hồi đáp", "Đọc hiểu ngắn" hoặc "Chọn câu đúng"
- "topic": "Từ vựng" hoặc "Ngữ pháp"
- "question": nội dung câu hỏi
- "options": object có đủ khóa "A", "B", "C", "D"
- "correct_option": một trong "A", "B", "C", "D"
- "explanation": giải thích bằng tiếng Việt có dấu

Ví dụ cấu trúc:
[
  {{
    "question_type": "Điền từ",
    "topic": "Từ vựng",
    "question": "我每天早上七点____，然后去学校。",
    "options": {{
      "A": "起床",
      "B": "睡觉",
      "C": "下课",
      "D": "考试"
    }},
    "correct_option": "A",
    "explanation": "“七点”和“然后去学校” cho thấy đây là hành động thức dậy buổi sáng."
  }}
]

QUY TẮC JSON:
- Chỉ trả về JSON ARRAY, không thêm lời dẫn hoặc kết luận.
- Không dùng Markdown hoặc code fence.
- Dùng dấu nháy kép cho chuỗi.
- Không thêm dấu phẩy sau phần tử cuối.
- Không bỏ trống trường dữ liệu.
- Không thêm trường ngoài 6 trường quy định.
- "options" phải có đủ đúng bốn khóa A, B, C, D.
- "question_type" phải thuộc đúng một trong bốn dạng đã nêu.

TỰ KIỂM TRA:
- Câu hỏi có đúng dạng bài HSK và đúng cấp độ không?
- Phần giải thích đã viết bằng tiếng Việt có dấu chưa?
- Kiến thức có trong dữ liệu tham khảo không?
- Câu hỏi có trùng danh sách đã thử sinh không?
- Đáp án có chính xác và duy nhất không?
- Bốn phương án có khác nhau không?
- JSON có hợp lệ không?

CHỈ TRẢ VỀ JSON ARRAY.
"""

def check_question(question, hsk_level, ai_review=False):
    """Kiểm tra cấu trúc, cấp độ và ngữ cảnh trước khi nhận câu hỏi."""
    if not isinstance(question, dict) or question.get("hsk_level") != hsk_level:
        return False

    if question.get("topic") not in ["Từ vựng", "Ngữ pháp"]:
        return False
    if question.get("question_type") not in [
        "Điền từ", "Chọn câu hồi đáp", "Đọc hiểu ngắn", "Chọn câu đúng"
    ]:
        return False

    structure_valid, message = validate_question(question)
    if not structure_valid:
        print("Lỗi cấu trúc:", message)
        return False

    semantic_valid, errors = validate_semantics(question)
    if not semantic_valid:
        print("Câu hỏi bị loại:", question.get("question", ""))
        for error in errors:
            print("-", error)
        return False

    if ai_review:
        ai_valid, ai_errors = validate_question_with_ai(question, hsk_level)
        if not ai_valid:
            print("Câu hỏi bị AI kiểm duyệt loại:", question.get("question", ""))
            for error in ai_errors:
                print("-", error)
            return False

    return True


def generate_questions_with_ai(
    project_dir,
    hsk_level,
    num_questions,
    ai_review=False,
    existing_questions=None,
    allow_partial=False,
):
    """Sinh câu hỏi HSK bằng LLM và kiểm định từng câu."""

    if hsk_level not in range(1, 7):
        raise ValueError("HSK phải từ 1 đến 6.")

    if num_questions <= 0:
        raise ValueError("Số câu hỏi phải lớn hơn 0.")

    # Tải dữ liệu HSK
    materials = load_hsk_material(project_dir, hsk_level)
    vocab = materials["vocab"]
    grammar = materials["grammar"]

    # Khởi tạo
    valid_questions = []
    attempted_questions = {
        re.sub(r"\s+", " ", question).strip().casefold()
        for question in (existing_questions or [])
        if isinstance(question, str) and question.strip()
    }

    # Sinh nhiều câu trong một request để giảm số lượt nạp/chạy model.
    batch_size = 3
    max_attempts = max(3, (num_questions + batch_size - 1) // batch_size + 2)

    for attempt in range(1, max_attempts + 1):
        remaining = num_questions - len(valid_questions)
        if remaining <= 0:
            break

        batch_count = min(remaining, batch_size)

        print(
            f"\nLượt {attempt}: đang sinh {batch_count} câu, "
            f"còn thiếu tổng cộng {remaining} câu."
        )

        # Chỉ gửi một nhóm kiến thức nhỏ để giảm thời gian xử lý prompt.
        vocab_text = prepare_vocab_text(vocab, limit=8)
        grammar_text = prepare_grammar_text(grammar, limit=4)
        existing_questions = sorted(attempted_questions)[-30:]

        prompt = build_generation_prompt(
            hsk_level,
            batch_count,
            vocab_text,
            grammar_text,
            existing_questions,
        )

        try:
            response = generate_text(
                prompt,
                output_format=QUESTION_SCHEMA
          )

            print("\n========== PHẢN HỒI THÔ TỪ LLAMA 3 ==========")
            print(repr(response))
            print("========== KẾT THÚC PHẢN HỒI ==========\n")

            generated_questions = parse_questions(response)
        except (ConnectionError, TimeoutError, RuntimeError) as error:
            raise RuntimeError(f"Không gọi được Ollama: {error}") from error
        except Exception as error:
            print("Lỗi đọc phản hồi từ Ollama:", error)
            continue

        if not generated_questions:
            print("LLM trả về danh sách câu hỏi rỗng.")
            continue

        for question in generated_questions:
            if not isinstance(question, dict):
                print("Bỏ phần tử không phải dict.")
                continue

            question_text = question.get("question", "")
            if not isinstance(question_text, str):
                print("Bỏ câu hỏi có nội dung không hợp lệ.")
                continue

            question_text = re.sub(r"\s+", " ", question_text).strip()
            if not question_text:
                print("Bỏ câu hỏi rỗng.")
                continue

            question["question"] = question_text
            normalized_question = question_text.casefold()

            if normalized_question in attempted_questions:
                print("Bỏ câu đã thử:", question_text)
                continue

            # Đánh dấu cả câu sẽ bị loại để hạn chế sinh lặp.
            attempted_questions.add(normalized_question)

            if question.get("topic") not in ["Từ vựng", "Ngữ pháp"]:
                print("Bỏ câu có chủ đề không hợp lệ:", question_text)
                continue

            question["id"] = str(uuid4())
            question["hsk_level"] = hsk_level

            try:
                is_valid = check_question(question, hsk_level, ai_review=ai_review)
            except Exception as error:
                print(
                    "Lỗi trong quá trình kiểm định:",
                    question_text,
                    "|",
                    error,
                )
                continue

            if is_valid:
                valid_questions.append(question)
                print(
                    f"Đã nhận {len(valid_questions)}/{num_questions} câu."
                )
            else:
                print("Câu hỏi không đạt:", question_text)

            if len(valid_questions) >= num_questions:
                break

    if len(valid_questions) < num_questions:
        if allow_partial:
            print(
                f"Chỉ tạo được {len(valid_questions)}/{num_questions} "
                "câu hợp lệ; trả phần này về để lưu vào kho."
            )
            return valid_questions

        raise RuntimeError(
            f"Chỉ tạo được {len(valid_questions)}/{num_questions} "
            f"câu hợp lệ sau {max_attempts} lượt. "
            "Hãy thử chạy lại hoặc kiểm tra dữ liệu và bộ kiểm định."
        )

    return valid_questions[:num_questions]


# =====================================================
# 7. HÀM TƯƠNG THÍCH
# =====================================================

def generate_quiz(
    project_dir,
    hsk_level,
    num_questions,
    ai_review=False,
    existing_questions=None,
    allow_partial=False,
):
    """Tên hàm gọi sinh đề tổng quát."""
    return generate_questions_with_ai(
        project_dir,
        hsk_level,
        num_questions,
        ai_review=ai_review,
        existing_questions=existing_questions,
        allow_partial=allow_partial,
    )


def generate_vocab_questions(project_dir, hsk_level, num_questions):
    """
    Sinh câu hỏi tổng quát rồi lọc câu từ vựng.

    Lưu ý: bộ sinh hiện tại có thể tạo cả từ vựng và ngữ pháp,
    vì vậy số câu từ vựng có thể ít hơn num_questions.
    """
    questions = generate_questions_with_ai(
        project_dir,
        hsk_level,
        num_questions,
    )

    vocab_questions = [
        question for question in questions
        if question.get("topic") == "Từ vựng"
    ]

    if len(vocab_questions) < num_questions:
        raise RuntimeError(
            f"Chỉ tạo được {len(vocab_questions)}/{num_questions} "
            "câu từ vựng. Bộ sinh hiện tại chưa đảm bảo chỉ sinh từ vựng."
        )

    return vocab_questions[:num_questions]
