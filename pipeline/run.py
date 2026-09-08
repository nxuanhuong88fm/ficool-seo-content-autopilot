from __future__ import annotations
import os,uuid
from pathlib import Path
from pipeline.topic_selector import TopicSelector
from pipeline.research import ResearchPipeline
from pipeline.article import ArticlePipeline
from pipeline.images import ImagePipeline
from pipeline.assembly import AssemblyPipeline
from pipeline.qa import QAPipeline
from pipeline.wordpress_publish import WordPressPipeline
from pipeline.utils import dump_yaml

def run_topic(topic_id,output_root=None,use_mock_images=False):
    topic=TopicSelector().by_id(topic_id); root=Path(output_root or os.getenv('FICOOL_OUTPUT_DIR','output/runs'))/f'{topic_id}-{uuid.uuid4().hex[:8]}'; root.mkdir(parents=True,exist_ok=True)
    research=ResearchPipeline().run(topic,root); article=ArticlePipeline().run(topic,research,root)
    if use_mock_images:
        from connectors.image_provider import MockImageProvider
        p=MockImageProvider(); images=[]
        for i in range(1,5):
            a=p.generate(prompt=topic['title'],output_path=root/'images'/f'img-{i:03d}',width=1600,height=900); images.append({'id':f'IMG-{i:03d}','width':a.width,'height':a.height,'alt':topic['title'],'title':topic['title'],'caption':topic['title'],'filename':a.path.name,'local_path':str(a.path)})
    else:
        images=ImagePipeline().generate(topic,article['body'],root)
        for i in images: i['local_path']=str(root/'images'/i['filename'])
    uploaded=[{'id':i['id'],'source_url':i['local_path'],'local_path':i['local_path'],'width':i['width'],'height':i['height'],'alt':i['alt'],'caption':i['caption']} for i in images]
    html_body=AssemblyPipeline().run(article,images,uploaded,root)
    qa=QAPipeline().run(topic,article,html_body,images,research); dump_yaml(root/'qa.yaml',qa)
    if qa['status']!='PASS': raise RuntimeError(f'QA BLOCK: {qa}')
    wp=WordPressPipeline().run(topic,article,html_body,images) if all(os.getenv(k) for k in ('WP_URL','WP_USERNAME','WP_APPLICATION_PASSWORD')) else {'status':'not_run','reason':'WordPress credentials missing'}
    dump_yaml(root/'wordpress.yaml',wp); return root,qa,wp
