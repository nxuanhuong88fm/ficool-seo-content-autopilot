from pathlib import Path
import argparse, json, re
from connectors.image_provider import MockImageProvider

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    return re.sub(r"[-\s]+", "-", text).strip("-")

def build_demo(keyword):
    slug = slugify(keyword)
    out = OUTPUT / "runs" / slug
    out.mkdir(parents=True, exist_ok=True)
    brief = {
        "article": {"title": keyword.capitalize() + ": nguyên nhân và cách xử lý", "primary_keyword": keyword, "search_intent": "informational", "funnel_stage": "problem_aware"},
        "strategy": {"business_goal": "educate_and_assist", "unique_angle": "practical troubleshooting with safety boundaries"},
        "structure": {"h1": keyword.capitalize() + ": nguyên nhân và cách xử lý", "sections": ["Dấu hiệu", "Nguyên nhân", "Cách kiểm tra", "Khi nào nên gọi kỹ thuật viên", "FAQ"]},
        "links": {"required_internal": []}, "images": {"target_count": 4},
        "seo": {"slug": slug, "meta_title": keyword.capitalize() + ": nguyên nhân thường gặp", "meta_description": f"Tìm hiểu {keyword}, nguyên nhân thường gặp, cách kiểm tra an toàn và khi nào nên gọi kỹ thuật viên."},
        "cta": {"type": "soft", "destination": "/dich-vu/"}
    }
    (out / "brief.json").write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    article = f"# {brief['article']['title']}\n\n{keyword.capitalize()} có thể xuất hiện vì nhiều nguyên nhân khác nhau. Bài viết này giúp bạn nhận biết dấu hiệu, kiểm tra các nguyên nhân thường gặp và biết khi nào nên cần kỹ thuật viên.\n\n## Dấu hiệu thường gặp\n\nKiểm tra vị trí, thời điểm và mức độ bất thường trước khi quyết định xử lý.\n\n## Nguyên nhân\n\nCác nguyên nhân cần được đánh giá theo tình trạng thiết bị thực tế; không nên kết luận chỉ từ một dấu hiệu.\n\n## Khi nào nên gọi kỹ thuật viên?\n\nNếu thiết bị có dấu hiệu bất thường kéo dài, liên quan điện/nước hoặc cần tháo lắp chuyên môn, nên dừng thao tác không cần thiết và liên hệ kỹ thuật viên.\n\n## Kết luận\n\nƯu tiên xác định nguyên nhân trước khi sửa chữa để tránh xử lý sai vấn đề.\n"
    (out / "article.md").write_text(article, encoding="utf-8")
    provider = MockImageProvider()
    images = []
    for i, purpose in enumerate(["featured topic context", "explain likely cause", "show inspection context", "support service decision"], 1):
        path = provider.generate(f"{keyword}; {purpose}; realistic HVAC service illustration", out / "images" / f"img-{i:03d}.webp")
        images.append({"id": f"IMG-{i:03d}", "type": "featured" if i == 1 else "contextual", "purpose": purpose, "path": str(path.relative_to(ROOT)), "alt": f"Minh họa {keyword} — {purpose}"})
    manifest = {"article": {"slug": slug}, "images": images}
    (out / "image-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    qa = {"quality": {"overall": 90, "content": 88, "seo": 90, "images": 90, "technical": 95}, "blockers": [], "passed": True}
    (out / "qa-report.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    wp = {"title": brief["article"]["title"], "slug": slug, "status": "draft", "content_file": str((out / "article.md").relative_to(ROOT))}
    (out / "wordpress-payload.json").write_text(json.dumps(wp, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Demo complete: {out.relative_to(ROOT)}")

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    d = sub.add_parser("demo")
    d.add_argument("keyword")
    args = p.parse_args()
    if args.command == "demo": build_demo(args.keyword)

if __name__ == "__main__": main()
