from __future__ import annotations


def verify_post(client, post_id: int, expected_status: str = "draft") -> dict:
    """Đọc LẠI bài từ WordPress sau khi tạo, thay vì tin vào phản hồi lúc ghi.

    Trả về cả `status` và `link` — người gọi cần hai trường đó để báo cáo.
    """
    post = client.get_post(post_id)
    status = post.get("status")
    tieu_de = post.get("title")
    if isinstance(tieu_de, dict):
        tieu_de = tieu_de.get("rendered", "")
    checks = {"id": post.get("id") == post_id, "status": status == expected_status}
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "status": status,
        "link": post.get("link"),
        "title": tieu_de or "",
    }
