"""Lớp kết nối Gemini (Google AI Studio) — dùng chung cho viết bài, nghiên cứu, sinh ảnh.

Gom vào một chỗ để KHOÁ và TÊN MODEL chỉ đọc từ một nơi. Ba module trước đây mỗi
module tự đọc `OPENAI_API_KEY` và tự đặt model mặc định riêng — đúng kiểu trôi
khỏi nhau mà cả kho này đã mắc một lần.

Khoá: `GEMINI_API_KEY`. Cố ý KHÔNG dùng `GOOGLE_API_KEY` dù SDK cũng chấp nhận —
kho này đã có `GOOGLE_APPLICATION_CREDENTIALS_JSON` cho Search Console, và hai
biến `GOOGLE_*` cạnh nhau với ý nghĩa khác hẳn là mời gọi nhầm lẫn.
"""
from __future__ import annotations
import os


class GeminiError(RuntimeError):
    pass


# Đối chiếu ai.google.dev/gemini-api/docs/models ngày 09/09/2026.
MODEL_VAN_BAN_MAC_DINH = 'gemini-3.8-flash'
MODEL_ANH_MAC_DINH = 'gemini-3.1-flash-image'   # Nano Banana 2


def khoa() -> str:
    k = os.getenv('GEMINI_API_KEY', '')
    if not k:
        raise GeminiError('GEMINI_API_KEY is required (Google AI Studio)')
    return k


def tao_client():
    from google import genai
    return genai.Client(api_key=khoa())


def model_van_ban() -> str:
    return os.getenv('GEMINI_TEXT_MODEL') or MODEL_VAN_BAN_MAC_DINH


def model_anh() -> str:
    return os.getenv('GEMINI_IMAGE_MODEL') or MODEL_ANH_MAC_DINH
