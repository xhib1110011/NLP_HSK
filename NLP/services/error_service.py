
def analyze_errors(grade_result, questions):
    """
    Phân tích các câu trả lời sai.
    grade_result: kết quả từ grade_quiz()
    questions: danh sách câu hỏi gốc
    """

    question_map = {q["id"]: q for q in questions}
    errors = []

    for result in grade_result["results"]:
        if result["is_correct"]:
            continue

        q = question_map[result["question_id"]]

        errors.append({
            "question_id": q["id"],
            "hsk_level": q["hsk_level"],
            "topic": q["topic"],
            "question": q["question"],
            "selected_option": result["selected_option"],
            "correct_option": result["correct_option"],
            "explanation": q["explanation"],
            "suggestion": get_study_suggestion(q["topic"])
        })

    return errors


def get_study_suggestion(topic):
    """Gợi ý ôn tập dựa trên chủ điểm câu hỏi."""

    suggestions = {
        "vocabulary": "Ôn lại nghĩa từ vựng và cách sử dụng từ trong ngữ cảnh.",
        "grammar": "Ôn lại cấu trúc ngữ pháp và làm thêm bài tập tương tự.",
        "sentence_order": "Luyện sắp xếp trạng ngữ, chủ ngữ, động từ và tân ngữ.",
        "reading": "Đọc lại đoạn văn, xác định từ khóa và tìm thông tin liên quan."
    }

    return suggestions.get(
        topic,
        "Ôn lại kiến thức liên quan và làm thêm câu hỏi cùng chủ điểm."
    )
