from pathlib import Path
import random
import sys
import streamlit as st

PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from services.grading_service import grade_quiz
from services.auth_service import authenticate_user, create_user
from services.question_bank_service import get_question_bank
from services.progress_service import (
    save_quiz_result,
    get_history,
    get_topic_statistics
)
from database.connection import get_connection, init_database

st.set_page_config(
    page_title="HSK AI Tutor",
    page_icon="📚",
    layout="wide"
)

init_database()

st.title("📚 HSK AI Tutor")
st.write("Hệ thống luyện thi tiếng Trung bằng câu hỏi trắc nghiệm.")

if "user_id" not in st.session_state:
    st.session_state.user_id = None
    st.session_state.username = None

if st.session_state.user_id is None:
    login_tab, register_tab = st.tabs(["Đăng nhập", "Tạo tài khoản"])

    with login_tab:
        with st.form("login_form"):
            login_username = st.text_input("Email hoặc tên đăng nhập")
            login_password = st.text_input("Mật khẩu", type="password")
            login_submitted = st.form_submit_button("Đăng nhập")

        if login_submitted:
            with get_connection() as conn:
                user = authenticate_user(conn, login_username, login_password)
            if user:
                st.session_state.user_id = user["id"]
                st.session_state.username = user["username"]
                st.rerun()
            else:
                st.error("Tên đăng nhập hoặc mật khẩu chưa chính xác.")

    with register_tab:
        with st.form("register_form"):
            register_username = st.text_input("Email hoặc tên đăng nhập mới")
            register_password = st.text_input(
                "Mật khẩu (ít nhất 8 ký tự)", type="password"
            )
            confirm_password = st.text_input(
                "Nhập lại mật khẩu", type="password"
            )
            register_submitted = st.form_submit_button("Tạo tài khoản")

        st.caption("Email hiện chỉ dùng làm tên đăng nhập, chưa có xác minh email.")

        if register_submitted:
            if register_password != confirm_password:
                st.error("Hai mật khẩu chưa khớp.")
            else:
                with get_connection() as conn:
                    new_user_id, error = create_user(
                        conn, register_username, register_password
                    )
                if error:
                    st.error(error)
                else:
                    st.session_state.user_id = new_user_id
                    st.session_state.username = register_username.strip()
                    st.rerun()

    st.stop()

user_id = int(st.session_state.user_id)

with st.sidebar:
    st.header("Thiết lập bài luyện")
    st.caption(f"Đang đăng nhập: {st.session_state.username}")
    if st.button("Đăng xuất"):
        for key in (
            "user_id", "username", "quiz", "quiz_level",
            "quiz_result", "quiz_submitted", "quiz_token"
        ):
            st.session_state.pop(key, None)
        st.rerun()

    hsk_level = st.selectbox(
        "Chọn cấp độ HSK",
        options=[1, 2, 3, 4, 5, 6],
        index=2
    )

    with get_connection() as conn:
        available_questions = get_question_bank(conn, hsk_level)

    st.caption("Đề được lấy từ kho câu hỏi có sẵn để bắt đầu nhanh.")

    if available_questions:
        max_questions = min(20, len(available_questions))
        num_questions = st.slider(
            "Số câu muốn làm",
            min_value=1,
            max_value=max_questions,
            value=min(5, max_questions),
        )
    else:
        num_questions = 0
        st.info(
            f"Cấp độ HSK {hsk_level} hiện chưa có câu hỏi. "
            "Hãy chọn cấp độ khác hoặc quay lại sau."
        )

    create_button = st.button(
        "🎯 Tạo đề",
        type="primary",
        use_container_width=True,
        disabled=not available_questions,
    )

if create_button:
    generated_quiz = random.sample(available_questions, num_questions)
    st.session_state.quiz = generated_quiz
    st.session_state.quiz_level = hsk_level
    st.session_state.quiz_token = (
        st.session_state.get("quiz_token", 0) + 1
    )
    st.session_state.quiz_result = None
    st.session_state.quiz_submitted = False
    st.rerun()

quiz = st.session_state.get("quiz")

if quiz:
    st.divider()
    st.subheader(f"📝 Bài luyện HSK {st.session_state.quiz_level}")
    st.write(f"Tổng số câu: {len(quiz)}")

    if not st.session_state.get("quiz_submitted", False):
        with st.form("quiz_form"):
            for index, question in enumerate(quiz, start=1):
                st.markdown(
                    f"**Câu {index}. {question['question']}**"
                )
                if question.get("question_type"):
                    st.caption(f"Dạng bài: {question['question_type']}")

                options = ["A", "B", "C", "D"]
                st.radio(
                    "Chọn đáp án:",
                    options=options,
                    format_func=lambda option, q=question:
                        f"{option}. {q['options'][option]}",
                    key=(
                        f"answer_{st.session_state.quiz_token}_"
                        f"{question['id']}"
                    ),
                    index=None
                )
                st.write("")

            submitted = st.form_submit_button(
                "Nộp bài",
                type="primary"
            )

        if submitted:
            answers = {}
            for question in quiz:
                key = (
                    f"answer_{st.session_state.quiz_token}_"
                    f"{question['id']}"
                )
                answers[question["id"]] = st.session_state.get(key)

            result = grade_quiz(quiz, answers)

            with get_connection() as conn:
                save_quiz_result(
                    conn,
                    st.session_state.quiz_level,
                    result,
                    quiz,
                    user_id=user_id,
                )

            st.session_state.quiz_result = result
            st.session_state.quiz_submitted = True
            st.rerun()

    if st.session_state.get("quiz_submitted", False):
        result = st.session_state.quiz_result

        st.divider()
        st.subheader("📊 Kết quả")

        col1, col2, col3 = st.columns(3)
        col1.metric("Số câu đúng", f"{result['score']}/{result['total']}")
        col2.metric("Điểm phần trăm", f"{result['percentage']:.1f}%")
        col3.metric("Số câu sai", result["total"] - result["score"])

        st.subheader("📖 Xem lại đáp án")

        for index, item in enumerate(result["results"], start=1):
            if item["is_correct"]:
                st.success(f"Câu {index}: Chính xác!")
            else:
                st.error(f"Câu {index}: Chưa chính xác.")

            st.write(f"**Câu hỏi:** {item['question']}")
            st.write(f"**Bạn chọn:** {item['selected_option'] or 'Chưa trả lời'}")
            st.write(f"**Đáp án đúng:** {item['correct_option']}")

            question_data = next(
                q for q in quiz if q["id"] == item["question_id"]
            )
            st.write(
                f"**Nội dung đáp án:** "
                f"{question_data['options'][item['correct_option']]}"
            )
            st.write(f"**Giải thích:** {item['explanation']}")
            st.divider()

        if st.button("Làm đề mới"):
            st.session_state.quiz = None
            st.session_state.quiz_result = None
            st.session_state.quiz_submitted = False
            st.rerun()

st.divider()
st.header("📈 Lịch sử và thống kê học tập")

with get_connection() as conn:
    history = get_history(conn, user_id)
    statistics = get_topic_statistics(conn, user_id)

if history:
    st.subheader("Lịch sử làm bài")
    st.dataframe([dict(row) for row in history], use_container_width=True)
else:
    st.info("Bạn chưa có lịch sử làm bài.")

if statistics:
    st.subheader("Độ chính xác theo chủ đề")
    st.dataframe([dict(row) for row in statistics], use_container_width=True)
else:
    st.info("Chưa có đủ dữ liệu để thống kê theo chủ đề.")
