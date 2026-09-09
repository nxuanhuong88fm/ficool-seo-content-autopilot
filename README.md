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

Cần `GEMINI_API_KEY` (Google AI Studio), `GSC_SITE_URL` +
`GOOGLE_APPLICATION_CREDENTIALS(_JSON)`, `SERPER_API_KEY`, và nhóm biến `WP_*`.
Cấp quyền cho email service account trên Search Console. WordPress dùng
Application Password qua HTTPS.

### Mô hình

Viết bài, nghiên cứu và sinh ảnh đều chạy trên **Gemini qua Google AI Studio**.

| việc | model mặc định | biến ghi đè |
|---|---|---|
| viết bài + rút meta | `gemini-3.8-flash` | `GEMINI_TEXT_MODEL` |
| nghiên cứu (Google Search grounding) | `gemini-3.8-flash` | `GEMINI_TEXT_MODEL` |
| sinh ảnh (Nano Banana 2) | `gemini-3.1-flash-image` | `GEMINI_IMAGE_MODEL` |
| khổ ảnh | `2K` | `GEMINI_IMAGE_SIZE` (`1K`/`2K`/`4K`) |

Khoá cố ý đặt tên `GEMINI_API_KEY` chứ không phải `GOOGLE_API_KEY`: kho này đã
có `GOOGLE_APPLICATION_CREDENTIALS_JSON` cho Search Console, và hai biến
`GOOGLE_*` cạnh nhau với ý nghĩa khác hẳn là mời gọi nhầm lẫn.

Ba khác biệt so với bản OpenAI cũ, đều đo được:

- **Nguồn nghiên cứu là dữ liệu thật.** Bản cũ luôn trả `sources: []` — trường
  có tên nhưng không bao giờ có nội dung. Google Search grounding trả URL thật.
- **JSON meta được ÉP.** Bản cũ chỉ *nhờ* model trả JSON rồi bọc `try/except`,
  nên mỗi lần model kèm ```json là im lặng rơi vào nhánh dự phòng — meta title
  và description tụt về tiêu đề chủ đề mà không ai biết. Nay dùng
  `response_mime_type='application/json'`.
- **`width`/`height` đọc từ byte ảnh.** Gemini nhận TỈ LỆ chứ không nhận pixel,
  và `image_size='2K'` không nói chính xác bao nhiêu pixel. Con số đó đi thẳng
  vào `<img width height>`, nên đọc header ảnh thật thay vì khai theo số đã xin.
  Định dạng lạ thì **dừng lại**, không khai bừa.

## Lệnh

```bash
python scripts/validate_repo.py                       # kiểm kho: import thật, không chỉ kiểm file tồn tại
python scripts/ficool.py demo "máy lạnh chảy nước"    # chạy khô, không mạng, không khoá
python scripts/ficool.py topics --category ML         # liệt kê chủ đề
python scripts/ficool.py show ML-01                   # xem một chủ đề
python scripts/ficool.py run ML-01 --mock-images      # chạy thử, không gọi API ảnh
python scripts/ficool.py run ML-01                    # chạy thật -> gói bàn giao
python scripts/ficool.py run ML-01 --dang-bai=rest    # máy tự đăng, cần khoá WP_*
python scripts/ficool.py run --auto                   # tự chọn theo GSC (cron dùng lệnh này)

python scripts/ficool.py lo 10 --xem-truoc            # xem 10 chủ đề kế tiếp + ước lượng gọi API
python scripts/ficool.py lo 10                        # chạy lô 10 bài
python scripts/ficool.py cho-dang                     # gói đã dựng, chưa lên WordPress
python scripts/ficool.py da-dang ML-01-ab12 4242      # đóng sổ sau khi tác nhân đã đăng
```

## Phương án (a): tác nhân nghiên cứu và viết

Chế độ đang dùng. Hai cần gạt tách riêng:

| cờ | bỏ được gì | còn cần gì |
|---|---|---|
| `--nghien-cuu=toi` | Gemini research **+ Serper + GSC** | — |
| `--viet=toi` | Gemini text | — |
| cả hai | | **chỉ `GEMINI_API_KEY` cho ảnh** |

```bash
python scripts/ficool.py yeu-cau 10                              # sinh dau-vao/*.yaml
# ... tác nhân điền nghiên cứu + bài viết vào từng tệp ...
python scripts/ficool.py lo 10 --nghien-cuu=toi --viet=toi       # chạy lô
```

Tệp mẫu mang theo **nguyên văn `LUAT_VIET`** của `pipeline/article.py`. Nên dù
tác nhân viết hay Gemini viết, luật vẫn từ một nguồn — sửa luật một chỗ là cả
hai đường đổi theo.

### Đầu vào bị kiểm chặt, cố ý

Tác nhân nộp bài cũng là một nguồn có thể sai. `pipeline/dau_vao.py` chặn ngay
nếu: nghiên cứu dưới 200 ký tự, dưới 2 URL thật (`http`/`https`), bài dưới 900
từ, thiếu dòng `# `, tiêu đề quá 60 ký tự, mô tả quá 160, slug không hợp lệ.

Dễ dãi ở đây thì cổng QA phía sau mất căn cứ: phép `co_nguon` chỉ còn kiểm rằng
trường `sources` **tồn tại**, không kiểm nó có nội dung — đúng lỗi của
`openai_research.py` cũ, luôn trả `sources: []` mà không ai biết.

Có một test chạy **toàn tuyến tới gói bàn giao khi không một khoá API nào được
đặt**. Còn dùng thừa một connector là test đó đỏ.

## Chạy theo lô, thứ tự cố định

Đây là chế độ đang dùng.

**Vì sao KHÔNG dùng `--auto` lúc này:** site đang `blog_public = 0`, chưa từng
được lập chỉ mục, nên không có một lượt hiển thị nào. Đo được: cho
`prioritize_topics` chạy với dữ liệu GSC rỗng thì 108 chủ đề **sụp xuống đúng
hai mức điểm** — 33 bài ở 20.0 và 75 bài ở 10.0. `--auto` chỉ đang bốc ngẫu
nhiên trong 33 bài đồng hạng, nhưng trông như có căn cứ. Thứ tự cố định trung
thực hơn và kiểm soát được.

| `--thu-tu` | thứ tự | khi nào dùng |
|---|---|---|
| **`cum`** *(mặc định)* | ML-01…ML-18, rồi MG-01… | gom cụm chủ đề — một lô 10 bài nằm trong cùng một dòng thiết bị |
| `luan-phien` | ML-01, MG-01, TL-01, TD-01, MN-01, TK-01, ML-02… | phủ rộng sớm — mỗi dịch vụ có bài ngay từ lô đầu |

Một bài hỏng **không giết cả lô** — chín bài kia đã tốn tiền API rồi. Lô chạy
tiếp, cuối cùng báo tổng kết và mã thoát khác 0 nếu có bài hỏng.

`output/manifests/` ghi sổ **ngay lúc dựng gói**, cố ý: sổ nghĩa là *"đã tiêu
ngân sách API cho chủ đề này"*, chạy lại là tiêu lần nữa. Đổi lại phải có
`cho-dang` để nhìn ra gói nào còn nợ chưa đăng, và `da-dang` để đóng sổ.

`--auto` xếp hạng 108 chủ đề theo tín hiệu GSC, bỏ chủ đề đã có bản nháp, rồi
chạy chủ đề đứng đầu. So khớp truy vấn có bỏ dấu, nên truy vấn gõ không dấu vẫn
tính điểm.

## Ba đường đưa bài lên WordPress

Trục thật **không phải** "MCP hay REST". Đo được trên ficool.top: ability của
novamira cũng đi qua HTTP với **cùng** application password —
`POST /wp-json/novamira/v1/abilities/{ten}/run` trả 401 y như `/wp/v2/posts`,
`permission_callback` chỉ kiểm `current_user_can_manage` (`rest-shim.php:45`).

Trục thật là hai câu hỏi khác nhau: **ai thực thi** và **API nào giàu hơn**.

| `--dang-bai` | ai chạy | cần khoá `WP_*` | được gì thêm |
|---|---|---|---|
| **`ho-so`** *(mặc định)* | tác nhân (Claude Code) | **không** | Rank Math + schema qua MCP |
| `novamira` | máy | có | meta Rank Math hạng nhất |
| `rest` | máy | có | chạy ở đâu cũng được |
| `auto` | | | thử giàu → nghèo → bàn giao |

### `ho-so` — mặc định, không cần khoá nào

MCP chỉ tồn tại trong phiên Claude Code; tiến trình Python không gọi được. Nên
Python làm phần **xác định được** (nghiên cứu, viết, ghép, đo), rồi ghi một gói
đầy đủ vào `output/runs/<id>/goi-dang/`:

```
goi-dang/
  ke-hoach.json    6 bước ability + bảng ảnh + danh sách kiểm sau khi đăng
  noi-dung.html    HTML đã ghép, ảnh còn là mốc @@ANH:IMG-001@@
  images/          các tệp ảnh
```

Rồi bảo Claude Code: *"đăng gói này lên WordPress qua novamira"*. Tác nhân có
sẵn quyền, không cần một biến `WP_*` nào.

⚠️ **Điểm yếu cố hữu của đường này, nói thẳng:** cổng QA buộc phải chấm HTML khi
ảnh còn là mốc — tác nhân chỉ biết `media_id` sau khi tải lên. Bước thay chuỗi
nằm **ngoài** cổng. Nên `ke-hoach.json` mang theo `kiem_sau_dang`: 7 khẳng định
cụ thể tác nhân phải kiểm lại sau khi đăng (còn `@@ANH:` không, `<img>` có trỏ
`wp-content/uploads` không, đủ số `<figure>` không, JSON-LD FAQPage còn nguyên
không…). Không có nó thì bước cuối không ai canh.

`ficool demo` cũng sinh gói này — đó là cách **duy nhất** chạy thử đường `ho-so`
đầu-tới-cuối mà không tốn một dòng khoá API, nên CI chạy được.

### Vì sao KHÔNG dùng `rank-math-edit-post-schema`

Đặt schema qua Rank Math thì khối FAQPage nằm **ngoài** `post_content`, nên cổng
QA sẽ chấm một tài liệu khác với tài liệu được đăng — đúng lỗi đã sửa ở `run.py`.
Một hành vi cho cả ba đường, hoặc không gì cả. JSON-LD vẫn chèn vào
`post_content`. Riêng `rank-math-edit-post-seo` thì dùng, vì chỗ đó không trùng:
REST lõi phải **đoán** tên trường qua `WP_META_TITLE_FIELD`.

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
