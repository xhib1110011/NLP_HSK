
def grade_quiz(questions, answers):
    """
    questions: danh sách câu hỏi
    answers: dict dạng {question_id: selected_option}
    """

    results = []
    score = 0

    for q in questions:
        qid = q["id"]
        selected = answers.get(qid, "")
        selected = selected.strip().upper() if isinstance(selected, str) else ""

        correct_option = q["correct_option"]
        is_correct = selected == correct_option

        if is_correct:
            score += 1

        results.append({
            "question_id": qid,
            "question": q["question"],
            "selected_option": selected or None,
            "correct_option": correct_option,
            "is_correct": is_correct,
            "explanation": q["explanation"]
        })

    total = len(questions)
    percentage = score / total * 100 if total else 0

    return {
        "score": score,
        "total": total,
        "percentage": round(percentage, 2),
        "results": results
    }
