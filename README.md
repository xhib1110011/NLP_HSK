# HSK AI Tutor

**HSK AI Tutor** is an AI-powered Chinese language learning application built with Streamlit. It provides practice questions across all six HSK levels, helping learners improve their Chinese language proficiency through structured exercises.

The application uses **Ollama (LLM)** to generate questions and **SQLite** to manage the question bank and user learning data.

## Features

- **Six HSK Levels:** Supports learning and practicing from HSK 1 to HSK 6.
- **AI-generated Questions:** Uses locally hosted LLMs through Ollama to generate practice questions.
- **Question Bank Management:** Stores generated questions in SQLite and exports them into JSON files for synchronization.
- **Question Retrieval:** Learners access existing questions from the shared question bank without requiring Ollama.
- **User Data Management:** Stores user accounts and learning history locally in SQLite.
- **Data Synchronization:** Supports importing and exporting question banks between different machines through JSON files and GitHub.

## System Architecture

The application consists of three main components:

| Component | Technology | Purpose |
|---|---|---|
| User Interface | Streamlit | Provides the learning interface |
| AI Question Generation | Ollama / LLM | Generates HSK practice questions |
| Data Storage | SQLite + JSON | Stores user data and synchronizes question banks |

**Workflow:**

1. The administrator generates questions using Ollama.
2. Generated questions are validated and saved to the local SQLite database.
3. The question bank is exported into JSON files.
4. JSON files are committed and pushed to GitHub.
5. Other machines pull the latest question bank and import it into their local SQLite databases.
6. Learners practice using the available questions.

## Installation and Usage

### 1. Run the Application

Activate the project's virtual environment and launch Streamlit:

```powershell
.\.venv\Scripts\python.exe -m streamlit run .\NLP\app.py
```

### 2. Generate Questions (Administrator)

Question generation requires Ollama to be installed and running on the administrator's machine.

To generate 20 questions for HSK Level 3:

```powershell
.\.venv\Scripts\python.exe .\NLP\build_question_bank.py --level 3 --target 20
```

The generated questions are:
- Saved to the local SQLite database.
- Automatically exported to the corresponding JSON file after each save operation.

Question bank files are located at:

```text
NLP/data/question_bank/
├── hsk_1.json
├── hsk_2.json
├── hsk_3.json
├── hsk_4.json
├── hsk_5.json
└── hsk_6.json
```

### 3. Synchronize the Question Bank

The question bank is shared through GitHub, while user accounts and learning history remain local to each machine.

**Export questions from SQLite to JSON:**

```powershell
.\.venv\Scripts\python.exe .\NLP\sync_question_bank.py --direction export --level 3
```

**Import questions from JSON into SQLite:**

```powershell
.\.venv\Scripts\python.exe .\NLP\sync_question_bank.py --direction import --level 3
```

To synchronize all six HSK levels, omit the `--level` argument.

Import behavior:
- Adds new questions to the local database.
- Skips duplicate questions.
- Preserves existing user accounts and learning history.

### 4. Publish the Question Bank to GitHub

After generating and exporting questions, review the changes:

```powershell
git status
```

Stage and commit the updated question bank:

```powershell
git add .\NLP\data\question_bank\hsk_3.json
git commit -m "Add HSK 3 question bank"
git push
```

On another machine, retrieve the latest version:

```powershell
git pull
```

Then import the updated question bank into its local SQLite database.

## GitHub Repository Setup

To initialize the repository and publish the project for the first time:

```powershell
git init -b main
git add .
git commit -m "Initial HSK AI Tutor project"
git remote add origin https://github.com/<username>/<repository-name>.git
git push -u origin main
```

Replace `<username>` and `<repository-name>` with your GitHub account and repository name.

## Data Management

The project separates shared learning content from individual user data.

**Shared data (GitHub):**
- Source code.
- Vocabulary and grammar JSON datasets.
- HSK question bank JSON files (`NLP/data/question_bank/hsk_*.json`).

**Local data (SQLite):**
- User accounts.
- Learning history.
- Other individual learning records.

The SQLite database is stored at:

```text
NLP/database/hsk_tutor.db
```

**Important:** The SQLite database must not be uploaded to GitHub because it contains user account information and individual learning records.

The `.gitignore` file excludes:
- Python virtual environments.
- `.env` files.
- SQLite databases.
- Experimental notebooks.
- Research datasets in the project root.
- Legacy code in `NLP/nlp/`.

## Technologies

- Python
- Streamlit
- Ollama
- Large Language Models (LLMs)
- SQLite
- JSON
- Git & GitHub

---

*HSK AI Tutor — AI-assisted Chinese language learning through structured HSK practice.*
