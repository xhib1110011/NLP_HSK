
import json
import re

from llm.ollama_service import generate_text


AI_REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "valid": {"type": "boolean"},
        "errors": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["valid", "errors"],
    "additionalProperties": False
}


def normalize_text(text):
    """Chuẩn hóa văn bản để so sánh."""
    if not isinstance(text, str):
        return ""

    text = text.strip().lower()
    text = re.sub(r"\s+", "", text)
    return text


def check_options(options):
    """Kiểm tra bốn phương án A, B, C, D."""
    errors = []

    if not isinstance(options, dict):
        return ["Phương án không đúng định dạng dict."]

    if set(options.keys()) != {"A", "B", "C", "D"}:
        return ["Phải có đủ bốn phương án A, B, C, D."]

    values = [normalize_text(v) for v in options.values()]

    if any(not value for value in values):
        errors.append("Có phương án bị trống.")

    if len(set(values)) != len(values):
        errors.append("Có phương án bị trùng.")

    for key, value in options.items():
        if not isinstance(value, str):
            errors.append(f"Phương án {key} không phải chuỗi.")
            continue

        if "Phóng án" in value or "Phương án" in value:
            errors.append(
                f"Phương án {key} vẫn chứa nội dung mẫu."
            )

    return errors


def check_question_context(question_text):
    """Kiểm tra ngữ cảnh cơ bản."""

    errors = []

    if not isinstance(question_text, str) or not question_text.strip():
        return ["Nội dung câu hỏi bị trống."]

    text = question_text.strip()

    if len(text) < 5:
        errors.append("Câu hỏi quá ngắn.")

    blank_count = text.count("____") + text.count("＿")

    if blank_count > 1:
        errors.append("Câu hỏi có quá nhiều vị trí điền đáp án.")

    weak_patterns = [
        r"我喜欢____[。！？.!?]?$",
        r"这个____[。！？.!?]?$",
        r"我____了[。！？.!?]?$",
        r"我在____[。！？.!?]?$",
        r"他是一个____[。！？.!?]?$",
        r"她是一个____[。！？.!?]?$",
    ]

    for pattern in weak_patterns:
        if re.search(pattern, text):
            errors.append(
                "Câu hỏi có thể thiếu ngữ cảnh để xác định đáp án."
            )
            break

    return errors


def check_correct_answer(question):
    """Kiểm tra đáp án được đánh dấu."""

    errors = []

    options = question.get("options", {})
    correct_option = question.get("correct_option")

    if correct_option not in ["A", "B", "C", "D"]:
        errors.append("Đáp án đúng không hợp lệ.")
        return errors

    if not isinstance(options, dict):
        errors.append("Danh sách phương án không hợp lệ.")
        return errors

    if correct_option not in options:
        errors.append("Không tìm thấy đáp án đúng trong các phương án.")
        return errors

    if not isinstance(options[correct_option], str):
        errors.append("Nội dung đáp án đúng không hợp lệ.")

    return errors


def check_explanation(question):
    """Kiểm tra phần giải thích."""

    explanation = question.get("explanation")

    if not isinstance(explanation, str) or not explanation.strip():
        return ["Câu hỏi chưa có phần giải thích."]

    if '""' in explanation:
        return ["Phần giải thích có nội dung tiếng Trung bị thiếu."]

    return []


def check_missing_content(question):
    """Phát hiện câu hỏi hoặc phương án bị thiếu nội dung."""

    errors = []

    text = question.get("question", "")
    options = question.get("options", {})
    explanation = question.get("explanation", "")

    if not isinstance(text, str):
        errors.append("Câu hỏi không phải chuỗi.")
    elif '""' in text:
        errors.append("Câu hỏi có nội dung tiếng Trung bị thiếu.")

    if isinstance(options, dict):
        for key, value in options.items():
            if not isinstance(value, str) or not value.strip():
                errors.append(f"Phương án {key} bị trống.")
                continue

            if '""' in value:
                errors.append(
                    f"Phương án {key} có nội dung tiếng Trung bị thiếu."
                )

            if "..." in value or "…" in value:
                errors.append(
                    f"Phương án {key} có dấu ba chấm thay cho nội dung."
                )

    if isinstance(explanation, str) and "..." in explanation:
        errors.append("Phần giải thích có dấu ba chấm thay cho nội dung.")

    return errors


def validate_semantics(question):
    """
    Kiểm tra cấu trúc và chất lượng cơ bản bằng Python.
    """

    if not isinstance(question, dict):
        return False, ["Câu hỏi không đúng định dạng dict."]

    errors = []

    question_text = question.get("question", "")
    options = question.get("options", {})

    errors.extend(check_question_context(question_text))
    errors.extend(check_options(options))
    errors.extend(check_correct_answer(question))
    errors.extend(check_explanation(question))
    errors.extend(check_missing_content(question))
    errors.extend(check_vietnamese_language(question))

    return len(errors) == 0, errors


def validate_question_with_ai(question, hsk_level):
    """
    Dùng Llama 3 kiểm tra chất lượng câu hỏi.
    Trả về: (is_valid, errors).
    """

    prompt = f"""
Bạn là chuyên gia kiểm định đề thi HSK.

Hãy kiểm tra câu hỏi sau:

Cấp độ: HSK {hsk_level}
Chủ đề: {question.get("topic", "")}

Câu hỏi:
{question.get("question", "")}

Các phương án:
{json.dumps(question.get("options", {}), ensure_ascii=False)}

Đáp án được đánh dấu:
{question.get("correct_option", "")}

Giải thích:
{question.get("explanation", "")}

KIỂM TRA:

1. Câu hỏi có đúng kiến thức tiếng Trung không?
2. Câu hỏi có đủ ngữ cảnh không?
3. Đáp án được đánh dấu có chính xác không?
4. Có phương án nào khác cũng đúng không?
5. Các phương án có phù hợp với câu hỏi không?
6. Câu hỏi có phù hợp HSK {hsk_level} không?
7. Giải thích có chính xác và khớp đáp án không?
8. Có nội dung bị thiếu hoặc vô nghĩa không?

KIỂM TRA NGHIÊM NGẶT:

1. Câu hỏi và phương án là tiếng Trung phù hợp HSK; phần giải thích là tiếng Việt.
2. Kiểm tra kiến thức tiếng Trung, không được đoán.
3. Đáp án được chọn phải thực sự chính xác.
4. Ba phương án còn lại phải sai rõ ràng trong ngữ cảnh câu hỏi.
5. Giải thích phải đúng với chức năng ngữ pháp của từ được hỏi.
6. Nếu đáp án sai, giải thích sai hoặc không đủ căn cứ,
   bắt buộc trả về valid = false.
7. Không được chấp nhận câu hỏi chỉ vì cấu trúc JSON hợp lệ.

QUY TẮC:

- Chấp nhận câu hỏi từ vựng và ngữ pháp.
- Không bắt buộc phải có chỗ trống.
- Chấp nhận các dạng điền từ, chọn câu hồi đáp, đọc hiểu ngắn và chọn câu đúng.
- Câu hỏi/đoạn đọc và phương án phải dùng tiếng Trung.
- Không chấp nhận câu sai ngữ pháp.
- Không chấp nhận nhiều đáp án đúng.
- Không chấp nhận câu hỏi thiếu dữ liệu.
- Nếu không chắc chắn, đánh giá không hợp lệ.
- Không tự sửa câu hỏi.

CHỈ TRẢ VỀ JSON:

{{
    "valid": true,
    "errors": []
}}

Hoặc:

{{
    "valid": false,
    "errors": ["Lý do không hợp lệ"]
}}
"""

    try:
        response = generate_text(prompt, output_format=AI_REVIEW_SCHEMA)

        if not isinstance(response, str) or not response.strip():
            return False, ["AI kiểm tra trả về nội dung rỗng."]

        cleaned = response.strip()

        cleaned = re.sub(
            r"^\s*```(?:json)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE
        )

        cleaned = re.sub(r"\s*```\s*$", "", cleaned)

        json_start = cleaned.find("{")

        if json_start == -1:
            return False, ["AI không trả về JSON hợp lệ."]

        result, _ = json.JSONDecoder().raw_decode(
            cleaned[json_start:]
        )

        if not isinstance(result, dict):
            return False, ["Kết quả AI không đúng định dạng."]

        if not isinstance(result.get("valid"), bool):
            return False, ["AI không trả về trạng thái valid hợp lệ."]

        errors = result.get("errors", [])

        if not isinstance(errors, list):
            return False, ["Danh sách lỗi AI không hợp lệ."]

        if result["valid"] and errors:
            return False, ["AI đánh giá không nhất quán."] + errors

        return result["valid"], errors

    except Exception as error:
        return False, [f"Lỗi khi AI kiểm tra: {error}"]
def check_vietnamese_language(question):
    """Kiểm tra câu hỏi và giải thích có sử dụng tiếng Việt."""

    errors = []

    question_text = question.get("question", "")
    explanation = question.get("explanation", "")

    vietnamese_pattern = (
        r"[àáạảãâầấậẩẫăằắặẳẵ"
        r"èéẹẻẽêềếệểễ"
        r"ìíịỉĩ"
        r"òóọỏõôồốộổỗơờớợởỡ"
        r"ùúụủũưừứựửữ"
        r"ỳýỵỷỹđ]"
    )

    question_has_vietnamese = (
        isinstance(question_text, str)
        and re.search(vietnamese_pattern, question_text.lower())
    )
    question_has_chinese = (
        isinstance(question_text, str)
        and re.search(r"[㐀-鿿]", question_text)
    )

    # Câu hỏi HSK có thể là câu tiếng Trung thuần; phần giải thích phải là tiếng Việt.
    if not question_has_vietnamese and not question_has_chinese:
        errors.append("Câu hỏi cần có nội dung tiếng Việt hoặc tiếng Trung.")

    if not isinstance(explanation, str) or not re.search(
        vietnamese_pattern, explanation.lower()
    ):
        errors.append("Giải thích phải được viết bằng tiếng Việt có dấu.")

    return errors
