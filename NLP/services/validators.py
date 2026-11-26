
def validate_question(question):
    """Kiểm tra cấu trúc cơ bản của một câu hỏi trắc nghiệm."""

    required_fields = [
        "id", "hsk_level", "topic", "question",
        "options", "correct_option", "explanation"
    ]

    for field in required_fields:
        if field not in question:
            return False, f"Thiếu trường: {field}"

    if question["hsk_level"] not in range(1, 7):
        return False, "Cấp độ HSK phải từ 1 đến 6"

    options = question["options"]

    if not isinstance(options, dict):
        return False, "Phương án phải là dictionary"

    if set(options.keys()) != {"A", "B", "C", "D"}:
        return False, "Phải có đúng bốn phương án A/B/C/D"

    if any(not isinstance(v, str) or not v.strip()
           for v in options.values()):
        return False, "Phương án không được để trống"

    if len(set(v.strip() for v in options.values())) != 4:
        return False, "Các phương án không được trùng nhau"

    if question["correct_option"] not in options:
        return False, "Đáp án đúng không hợp lệ"

    if not isinstance(question["question"], str) or not question["question"].strip():
        return False, "Nội dung câu hỏi không được để trống"

    if not isinstance(question["explanation"], str) or not question["explanation"].strip():
        return False, "Giải thích không được để trống"

    return True, "Câu hỏi hợp lệ"
