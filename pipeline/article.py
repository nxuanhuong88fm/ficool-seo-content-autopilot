from __future__ import annotations
import json

from connectors.gemini import model_van_ban, tao_client
from pipeline.utils import dump_yaml, slugify

# Yêu cầu cấu trúc phải KHỚP với các phép đo trong pipeline/geo.py và pipeline/qa.py.
# Cổng mà người viết không thể qua là cổng hỏng — nếu sửa phép đo thì sửa cả đây.
LUAT_VIET = """Bạn là biên tập viên SEO tiếng Việt của Ficool (dịch vụ điện lạnh tại TP.HCM).

CẤU TRÚC BẮT BUỘC
- Đúng MỘT dòng `# ` ở đầu bài.
- Ngay sau `# `, viết một đoạn 1–3 câu (40–400 ký tự) TRẢ LỜI THẲNG câu hỏi của
  tiêu đề. Đoạn này phải đứng độc lập, hiểu được mà không cần đọc phần còn lại.
  Không mở đầu bằng "Như trên", "Điều này", "Ngoài ra", "Nó...".
- Ít nhất HAI tiêu đề `## ` hoặc `### ` viết dưới dạng câu hỏi (có dấu ? hoặc bắt
  đầu bằng: khi nào / tại sao / vì sao / làm sao / có nên / bao lâu / cách).
- Một mục `## Câu hỏi thường gặp (FAQ)` ở cuối, bên trong có ÍT NHẤT 3 câu hỏi,
  mỗi câu là một dòng `### ` kết thúc bằng dấu ?, và ngay dưới là đáp án 2–4 câu
  (tối thiểu 40 ký tự). Mỗi đáp án phải TỰ CHỨA — người đọc chỉ đọc riêng đáp án
  đó vẫn hiểu, vì máy trả lời sẽ trích lẻ từng đáp án.
- Ít nhất một danh sách gạch đầu dòng hoặc một bảng Markdown.
- Nếu là bài hướng dẫn: các bước đánh số `1.` `2.` `3.` trong một mục riêng.
- Câu ngắn. Trung vị độ dài câu không quá 28 từ.
- Nêu rõ "Ficool" và "TP.HCM" ít nhất một lần mỗi thứ, bằng tên chứ không bằng
  đại từ — máy trả lời cần thực thể tường minh.
- Độ dài toàn bài tối thiểu 900 từ.

TUYỆT ĐỐI KHÔNG
- Không bịa giá, thời hạn bảo hành, thời gian có mặt, số năm kinh nghiệm, số ca
  đã làm, chứng chỉ, đánh giá khách hàng hay thống kê không nguồn.
- Không dùng "100%", "rẻ nhất", "tốt nhất", "số 1", "uy tín nhất", "hàng đầu".
- Không viết "cam kết" kèm con số.
- Giá luôn nói theo hướng "phụ thuộc công suất và tình trạng máy", không nêu số.

MỐC CHÈN
- Chèn `<!-- IMAGE: IMG-001 -->` … `<!-- IMAGE: IMG-004 -->` vào chỗ hợp lý.
- Liên kết nội bộ viết dạng `<!-- INTERNAL: chữ neo | /duong-dan/ -->`.

Chỉ trả về nội dung bài, không thêm lời dẫn."""


class ArticlePipeline:
    def __init__(self):
        self.client = tao_client()
        self.model = model_van_ban()

    def _sinh(self, prompt, json_thuan=False):
        from google.genai import types
        cau_hinh = types.GenerateContentConfig(response_mime_type='application/json') if json_thuan else None
        r = self.client.models.generate_content(model=self.model, contents=prompt, config=cau_hinh)
        return (r.text or '').strip()

    def run(self, topic, research, output_dir):
        prompt = (LUAT_VIET + chr(10) * 2
                  + 'TOPIC=' + json.dumps(topic, ensure_ascii=False) + chr(10)
                  + 'RESEARCH=' + json.dumps(research, ensure_ascii=False)[:30000])
        body = self._sinh(prompt)

        # `response_mime_type='application/json'` ÉP Gemini trả JSON thuần. Bản
        # OpenAI cũ chỉ NHỜ model trả JSON rồi bọc try/except, nên mỗi lần model
        # kèm ```json là rơi vào nhánh dự phòng mà không ai biết — meta title và
        # meta description im lặng tụt về tiêu đề chủ đề.
        thoi = self._sinh(
            'Trả về JSON thuần với đúng các khoá: title (<=60 ký tự), '
            'meta_description (<=160 ký tự), slug, secondary_keywords (mảng), faq (mảng).'
            + chr(10) * 2 + body[:18000], json_thuan=True)
        try:
            meta = json.loads(thoi)
        except (json.JSONDecodeError, TypeError):
            meta = {'title': topic['title'], 'meta_description': topic['title'],
                    'slug': slugify(topic['title']),
                    'secondary_keywords': topic['secondary_keywords'], 'faq': []}

        dump_yaml(output_dir / 'article-draft.yaml', {'topic': topic, 'article': body, 'seo': meta})
        (output_dir / 'article.md').write_text(body, encoding='utf-8')
        return {'title': meta.get('title') or topic['title'], 'body': body, 'seo': meta,
                'slug': meta.get('slug') or slugify(topic['title'])}
