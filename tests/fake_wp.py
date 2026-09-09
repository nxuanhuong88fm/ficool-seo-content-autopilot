"""WordPress giả, chạy trong bộ nhớ, thay tầng requests.

Đủ thật để bắt lỗi giao diện: trả id tăng dần, khớp mờ cho ?search= (đúng như
WordPress thật, đó là cái bẫy mà find_term phải chống), và từ chối payload thiếu
trường bắt buộc.
"""
from __future__ import annotations
import json as _json


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status
        self.ok = status < 400
        self.text = _json.dumps(payload, ensure_ascii=False)

    def json(self):
        return self._payload


class FakeWordPress:
    def __init__(self):
        self.posts, self.media, self.terms = {}, {}, {"categories": {}, "tags": {}}
        self._next = 100
        self.calls = []

    def _id(self):
        self._next += 1
        return self._next

    def request(self, method, url, **kw):
        path = url.split("/wp-json/wp/v2", 1)[1]
        params = kw.get("params") or {}
        body = kw.get("json")
        self.calls.append((method, path.split("?")[0], params, body))

        if method == "POST" and path == "/posts":
            pid = self._id()
            self.posts[pid] = {
                **body, "id": pid, "link": f"https://ficool.top/?p={pid}",
                # WordPress thật luôn trả title/excerpt dạng {"rendered": ...},
                # không phải chuỗi thô như lúc gửi lên.
                "title": {"rendered": body.get("title", "")},
                "excerpt": {"rendered": body.get("excerpt", "")},
                "_payload": body,
            }
            return FakeResponse(self.posts[pid], 201)

        if method == "GET" and path.startswith("/posts/"):
            pid = int(path.rsplit("/", 1)[1])
            return FakeResponse(self.posts[pid]) if pid in self.posts else FakeResponse({}, 404)

        if method == "GET" and path == "/posts":
            slug = params.get("slug")
            return FakeResponse([p for p in self.posts.values() if p.get("slug") == slug])

        if method == "POST" and path == "/media":
            mid = self._id()
            self.media[mid] = {"id": mid, "source_url": f"https://ficool.top/wp-content/uploads/{mid}.png"}
            return FakeResponse(self.media[mid], 201)

        if method == "POST" and path.startswith("/media/"):
            mid = int(path.rsplit("/", 1)[1])
            self.media[mid].update(body or {})
            return FakeResponse(self.media[mid])

        for tax in ("categories", "tags"):
            if path == f"/{tax}":
                if method == "GET":
                    q = str(params.get("search", "")).casefold()
                    # khớp MỜ, y như WordPress thật
                    return FakeResponse([t for t in self.terms[tax].values() if q in t["name"].casefold()])
                tid = self._id()
                self.terms[tax][tid] = {"id": tid, "name": body["name"]}
                return FakeResponse(self.terms[tax][tid], 201)

        return FakeResponse({"message": f"khong co tuyen: {method} {path}"}, 404)
