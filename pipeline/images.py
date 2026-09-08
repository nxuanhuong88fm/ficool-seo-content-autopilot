from __future__ import annotations
from connectors.image_provider import OpenAIImageProvider
from pipeline.utils import dump_yaml
class ImagePipeline:
    def __init__(self): self.provider=OpenAIImageProvider()
    def plan(self,topic):
        return [
          {'id':'IMG-001','type':'featured','placement':'after_h1','purpose':'establish_topic','subject':topic['title']},
          {'id':'IMG-002','type':'instructional','placement':'after_h2_1','purpose':'show_problem','subject':topic['primary_keyword']},
          {'id':'IMG-003','type':'instructional','placement':'after_h2_2','purpose':'show_explanation','subject':topic['secondary_keywords'][0]},
          {'id':'IMG-004','type':'service','placement':'before_cta','purpose':'show_service_context','subject':'kỹ thuật viên điện lạnh tại TP.HCM'}]
    def generate(self,topic,article,output_dir):
        rows=[]
        for item in self.plan(topic):
            prompt=(f"Photorealistic editorial image for Vietnamese HVAC/refrigeration content. Subject: {item['subject']}. Purpose: {item['purpose']}. "
                    "Context: Ho Chi Minh City, Vietnam. Professional documentary style, realistic equipment, safe technician practice, natural lighting, no text, watermark or invented logos.")
            a=self.provider.generate(prompt=prompt,output_path=output_dir/'images'/item['id'].lower(),width=1600,height=900)
            rows.append({**item,'filename':a.path.name,'width':a.width,'height':a.height,'mime_type':a.mime_type,'provider':a.provider,'alt':f"{item['subject']} tại TP.HCM – Ficool",'title':item['subject'],'caption':f"Hình minh họa: {item['subject']}."})
        dump_yaml(output_dir/'image-manifest.yaml',{'topic_id':topic['id'],'images':rows}); return rows
