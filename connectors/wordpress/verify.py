def verify_draft(client, post_id: int, expected_title: str) -> dict:
    post = client.get_post(post_id)
    checks = {"id": post.get("id") == post_id, "title": post.get("title", {}).get("rendered") == expected_title, "status": post.get("status") == "draft"}
    return {"passed": all(checks.values()), "checks": checks}
