
def save_quiz_result(conn, hsk_level, grade_result, questions, user_id):
    """Lưu một lượt làm bài và đáp án từng câu."""

    question_map = {q["id"]: q for q in questions}

    with conn:
        cursor = conn.execute(
            """
            INSERT INTO quiz_sessions
            (user_id, hsk_level, total_questions, score, percentage)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                hsk_level,
                grade_result["total"],
                grade_result["score"],
                grade_result["percentage"]
            )
        )

        session_id = cursor.lastrowid

        for result in grade_result["results"]:
            q = question_map[result["question_id"]]

            conn.execute(
                """
                INSERT INTO attempts
                (session_id, question_id, selected_option,
                 correct_option, is_correct, topic)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    q["id"],
                    result["selected_option"],
                    result["correct_option"],
                    int(result["is_correct"]),
                    q["topic"]
                )
            )

    return session_id


def get_history(conn, user_id):
    return conn.execute(
        """
        SELECT id, hsk_level, total_questions, score,
               percentage, created_at
        FROM quiz_sessions
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (user_id,)
    ).fetchall()


def get_topic_statistics(conn, user_id):
    return conn.execute(
        """
        SELECT topic,
               COUNT(*) AS total_attempts,
               SUM(is_correct) AS correct_answers,
               ROUND(100.0 * SUM(is_correct) / COUNT(*), 2) AS accuracy
        FROM attempts
        INNER JOIN quiz_sessions ON quiz_sessions.id = attempts.session_id
        WHERE quiz_sessions.user_id = ?
        GROUP BY topic
        ORDER BY accuracy ASC
        """,
        (user_id,)
    ).fetchall()
