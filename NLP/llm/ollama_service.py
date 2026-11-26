
import json
import os
import urllib.request
import urllib.error

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "llama3:latest")
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "600"))


def generate_text(prompt, output_format=None):
    """Gửi prompt đến Ollama, có thể yêu cầu định dạng JSON."""

    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt không được để trống.")

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 1500
        }
    }

    # Chỉ áp dụng định dạng khi được yêu cầu
    if output_format is not None:
        payload["format"] = output_format

    data = json.dumps(
        payload,
        ensure_ascii=False
    ).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=OLLAMA_TIMEOUT_SECONDS
        ) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )

        if "response" not in result:
            raise ValueError(
                f"Ollama không trả về response: {result}"
            )

        return result["response"]

    except urllib.error.HTTPError as error:
        detail = error.read().decode(
            "utf-8", errors="replace"
        )
        raise RuntimeError(
            f"Ollama HTTP Error {error.code}: {detail}"
        ) from error

    except TimeoutError as error:
        raise TimeoutError(
            f"Ollama không phản hồi trong {OLLAMA_TIMEOUT_SECONDS} giây. "
            "Model có thể đang nạp hoặc sinh quá chậm."
        ) from error

    except urllib.error.URLError as error:
        if isinstance(error.reason, TimeoutError):
            raise TimeoutError(
                f"Ollama không phản hồi trong {OLLAMA_TIMEOUT_SECONDS} giây. "
                "Model có thể đang nạp hoặc sinh quá chậm."
            ) from error
        raise ConnectionError(
            "Không kết nối được Ollama tại "
            f"{OLLAMA_URL}. Hãy kiểm tra Ollama đang chạy và model "
            f"'{MODEL_NAME}' đã được tải."
        ) from error
