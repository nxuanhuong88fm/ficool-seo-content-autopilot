"""Bài mẫu đúng hình dạng mà LUAT_VIET yêu cầu và cổng QA/GEO đo.

Một nguồn duy nhất cho cả `ficool demo` và bộ test. Nếu ai đó siết một phép đo mà
quên dạy lại prompt, bài mẫu này đỏ ngay ở CI — nên nó là chốt chặn cho chính
cái bẫy "cổng mà người viết không thể qua".
"""
from __future__ import annotations

_DOAN = ('Máng hứng nước nằm ngay dưới dàn lạnh và dẫn nước ngưng ra ngoài theo ống thoát. '
         'Bụi bám lâu ngày làm máng đọng nước rồi tràn ra sàn. '
         'Hãy ngắt điện trước khi chạm vào bất kỳ bộ phận nào. ')


def bai_mau(tu_khoa: str) -> str:
    T = tu_khoa.capitalize()
    return f"""# {T}: nguyên nhân và cách xử lý

{T} thường bắt nguồn từ máng hứng nước bị nghẹt hoặc ống thoát bị gấp khúc. Kiểm tra hai chỗ đó trước khi gọi thợ.

<!-- IMAGE: IMG-001 -->

## Vì sao hiện tượng này xảy ra?

{_DOAN * 10}

- Máng hứng nước đọng bụi
- Ống thoát bị gấp khúc
- Thiếu **gas** làm dàn lạnh đóng băng

<!-- IMAGE: IMG-002 -->

## Cách kiểm tra tại nhà thế nào?

1. Ngắt nguồn điện của thiết bị và chờ khoảng năm phút cho máy ngừng hẳn.
2. Mở mặt nạ dàn lạnh, quan sát máng hứng nước xem có đọng bụi hay rêu không.
3. Kiểm tra ống thoát nước xem có đoạn nào bị gấp, bị đè hoặc dốc ngược không.
4. Lau sạch phần bụi nhìn thấy được, lắp lại mặt nạ rồi bật máy theo dõi.

{_DOAN * 10}

Tham khảo <!-- INTERNAL: bảng giá dịch vụ | /bang-gia/ --> trước khi quyết định.

<!-- IMAGE: IMG-003 -->

## Khi nào nên gọi kỹ thuật viên?

{_DOAN * 8}

| Hiện tượng | Hướng xử lý |
|---|---|
| Nhỏ giọt nhẹ | Vệ sinh máng hứng nước |
| Chảy thành dòng | Kiểm tra ống thoát |

Những gì Ficool cam kết làm: kiểm tra trước, báo giá rõ ràng, làm xong mới thu tiền.

<!-- IMAGE: IMG-004 -->

## Câu hỏi thường gặp (FAQ)

### {T} có tự hết được không?

Hiện tượng này hiếm khi tự hết, vì nguyên nhân thường là tắc nghẽn cơ học trong máng hứng nước hoặc ống thoát. Nếu không xử lý, nước sẽ tiếp tục tràn và có thể làm hỏng trần hoặc tường.

### Bao lâu nên vệ sinh máy một lần?

Với hộ gia đình tại TP.HCM dùng máy hằng ngày, nên vệ sinh định kỳ theo khuyến nghị của nhà sản xuất ghi trong sách hướng dẫn. Môi trường nhiều bụi thì rút ngắn chu kỳ lại.

### Tự vệ sinh tại nhà có an toàn không?

Bạn có thể tự lau phần máng và mặt nạ nhìn thấy được sau khi đã ngắt điện. Những việc cần tháo dàn lạnh, xử lý gas hoặc đụng tới mạch điện thì nên để kỹ thuật viên làm.

### Chi phí xử lý phụ thuộc vào những gì?

Chi phí thay đổi theo công suất máy, mức độ bám bẩn và việc có phải tháo dàn lạnh hay không. Ficool báo giá sau khi kiểm tra thực tế thay vì báo trước một con số cố định.
"""
