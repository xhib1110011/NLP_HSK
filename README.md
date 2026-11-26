# HSK AI Tutor

Ứng dụng Streamlit luyện tiếng Trung theo cấp HSK. App dùng Ollama để sinh câu hỏi khi người quản lý nạp kho; người học lấy câu hỏi đã có trong kho SQLite.

## Chạy ứng dụng

```powershell
.\.venv\Scripts\python.exe -m streamlit run .\NLP\app.py
```

## Tạo và đồng bộ kho câu hỏi

Sinh câu hỏi trên máy đã cài/chạy Ollama. `build_question_bank.py` lưu câu hỏi vào SQLite cục bộ và tự xuất kho cấp đó ra `NLP/data/question_bank/hsk_<cấp>.json` sau mỗi lượt lưu:

```powershell
.\.venv\Scripts\python.exe .\NLP\build_question_bank.py --level 3 --target 20
```

Sau khi sinh xong, kiểm tra thay đổi rồi commit JSON lên GitHub:

```powershell
git status
git add .\NLP\data\question_bank\hsk_3.json
git commit -m "Add HSK 3 question bank"
git push
```

Nếu đã nạp câu hỏi trực tiếp vào SQLite và muốn xuất lại thủ công:

```powershell
.\.venv\Scripts\python.exe .\NLP\sync_question_bank.py --direction export --level 3
```

Trên máy chủ hoặc bản clone mới, sau khi `git pull`, nhập JSON vào SQLite của máy đó:

```powershell
.\.venv\Scripts\python.exe .\NLP\sync_question_bank.py --direction import --level 3
```

Bỏ `--level 3` để đồng bộ cả sáu cấp. Import chỉ thêm câu mới và bỏ qua câu trùng; mỗi máy vẫn giữ database tài khoản/lịch sử riêng. GitHub chỉ cần lưu mã nguồn, dữ liệu từ vựng/ngữ pháp JSON app đang dùng và các file `NLP/data/question_bank/hsk_*.json`.

## GitHub

Tạo repository trên GitHub, rồi chạy lần đầu tại thư mục dự án:

```powershell
git init -b main
git add .
git commit -m "Initial HSK AI Tutor project"
git remote add origin https://github.com/<tai-khoan>/<ten-repo>.git
git push -u origin main
```

`.gitignore` đã loại môi trường ảo, file `.env`, database SQLite, notebook thử nghiệm, dữ liệu nghiên cứu ở thư mục gốc và bản mã cũ `NLP/nlp/`. Không đưa `NLP/database/hsk_tutor.db` lên GitHub vì file đó có thông tin tài khoản và lịch sử học.
