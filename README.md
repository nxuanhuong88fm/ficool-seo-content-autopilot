# Ficool SEO Content Autopilot

Tự động hoá nội dung SEO cho Ficool — dịch vụ điện lạnh tại TP.HCM. **Chỉ tạo bản
nháp (draft), không có đường publish tự động.**

## Một đường duy nhất

```
GSC → 108 chủ đề → xếp ưu tiên → SERP → nghiên cứu → viết bài
   → sinh ảnh → tải lên WP Media → ghép HTML bằng URL thật
   → CỔNG QA (14 phép, chặn hết) → tạo bản nháp WordPress → ghi sổ
```

Thứ tự trên là cố ý: **ảnh được tải lên TRƯỚC khi dựng HTML**, để cổng QA soi
đúng cái sẽ được đăng. Bài bị chặn thì ảnh vừa tải được gỡ, không để lại file
mồ côi.

Điểm vào duy nhất là `pipeline/`. Không có bản cài đặt thứ hai.

## Cài

```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e .
cp .env.example .env
```

Cần `OPENAI_API_KEY`, `GSC_SITE_URL` + `GOOGLE_APPLICATION_CREDENTIALS(_JSON)`,
`SERPER_API_KEY`, và nhóm biến `WP_*`. Cấp quyền cho email service account trên
Search Console. WordPress dùng Application Password qua HTTPS.

## Lệnh

```bash
python scripts/validate_repo.py                       # kiểm kho: import thật, không chỉ kiểm file tồn tại
python scripts/ficool.py demo "máy lạnh chảy nước"    # chạy khô, không mạng, không khoá
python scripts/ficool.py topics --category ML         # liệt kê chủ đề
python scripts/ficool.py show ML-01                   # xem một chủ đề
python scripts/ficool.py run ML-01 --mock-images      # chạy thử, không gọi API ảnh
python scripts/ficool.py run ML-01                    # chạy thật
python scripts/ficool.py run --auto                   # tự chọn chủ đề (cron dùng lệnh này)
```

`--auto` xếp hạng 108 chủ đề theo tín hiệu GSC, bỏ chủ đề đã có bản nháp, rồi
chạy chủ đề đứng đầu. So khớp truy vấn có bỏ dấu, nên truy vấn gõ không dấu vẫn
tính điểm.

## Cổng QA

14 phép, **tất cả đều chặn**. Luật cấm khẳng định nằm ở **một nguồn duy nhất**:
`config/forbidden-claims.yaml`. Mỗi luật bắt buộc mang theo một ví dụ phải chặn
và một ví dụ phải tha; `tests/test_qa.py` chạy cả hai chiều.

Chiều phủ định không phải trang trí — thiếu nó thì luật lặng lẽ chặn nhầm. Bản
cũ chặn mọi bài chứa `cam kết`, trong khi chính trang chủ ficool.top viết
"Những gì Ficool **cam kết** làm".

Tương tự, mỗi phép trong 14 phép đều có một test bẻ nó cho đỏ. Phép nào không
thể đỏ thì không phải phép đo.

## Chống trùng

`output/manifests/*.json` ghi mọi lượt đã ra bản nháp; thư mục này được commit
ngược lại repo sau mỗi lượt cron nên sổ sống qua các lượt chạy. Trước khi tạo
bài, pipeline còn hỏi thẳng WordPress xem slug đã tồn tại chưa.

## Kết quả mỗi lượt

`output/runs/<topic>-<run-id>/`: research, bằng chứng GSC/SERP, bản thảo, manifest
ảnh, HTML đã ghép, báo cáo QA, kết quả WordPress.

## Kiểm thử

```bash
pytest -q
```

CI chạy trên Python 3.11 (bản cron dùng) **và** 3.13, cài bằng `pip install -e .`
đúng như production, rồi `import pipeline.run` trước khi làm bất cứ việc gì khác.
