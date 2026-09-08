from __future__ import annotations
import re
class QAPipeline:
    def run(self,topic,article,html_body,images,research):
        checks={
          'h1':bool(re.search(r'<h1\b',html_body,re.I)),
          'primary_keyword':topic['primary_keyword'].casefold() in article['body'].casefold(),
          'faq':bool(re.search(r'faq|câu hỏi thường gặp',article['body'],re.I)),
          'no_fake_claims':not bool(re.search(r'100%|rẻ nhất|số 1|uy tín nhất|hơn \d+ năm',article['body'],re.I)),
          'contextual_images':len(images)>=3 and all(i.get('alt') for i in images),
          'images_inserted':html_body.count('ficool-article-image')>=len(images),
          'source_boundary':bool(research.get('serp') or research.get('ai_research',{}).get('sources')),
          'local_context':bool(re.search(r'TP\.HCM|Hồ Chí Minh',article['body'],re.I)),
          'cta':bool(re.search(r'đặt lịch|liên hệ|dịch vụ',article['body'],re.I)),
          'meta_title_length':len(str(article.get('seo',{}).get('title','')))<=60,
          'meta_description_length':len(str(article.get('seo',{}).get('meta_description','')))<=160}
        required=['h1','primary_keyword','faq','no_fake_claims','contextual_images','images_inserted','source_boundary']
        score=round(100*sum(checks.values())/len(checks)); return {'status':'PASS' if all(checks[k] for k in required) else 'BLOCK','overall':score,'checks':checks,'required_gate':required}
