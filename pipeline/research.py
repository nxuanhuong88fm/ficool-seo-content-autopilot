from __future__ import annotations
import os
from pipeline.utils import dump_yaml
from pipeline.prioritize import prioritize_topics
from pipeline.topic_selector import TopicSelector
from connectors.gsc import GSCClient
from connectors.web_search import SerperClient, GeminiResearchClient

class ResearchPipeline:
    def __init__(self):
        self.selector=TopicSelector(); self.gsc=GSCClient(); self.serp=SerperClient(); self.ai=GeminiResearchClient()
    def run(self,topic,output_dir):
        gsc=self.gsc.last_n_days(int(os.getenv('GSC_LOOKBACK_DAYS','90')))
        ranked=prioritize_topics(self.selector.all(),gsc)
        selected=next(x for x in ranked if x['id']==topic['id'])
        serp=self.serp.compact(topic['primary_keyword'])
        prompt=(f"Research this Ficool topic in Vietnamese for Ho Chi Minh City: {topic['title']}. Primary keyword: {topic['primary_keyword']}. "
                f"GSC signal: {selected.get('gsc_signal',{})}. SERP: {serp[:10]}. "
                "Separate search intent, entities, common claims, gaps, FAQs, local opportunities, service conversion opportunities and source URLs. Never invent Ficool business facts.")
        ai=self.ai.research(prompt)
        artifact={'topic':selected,'gsc':gsc,'gsc_ranked_topic_snapshot':ranked[:25],'serp':serp,'ai_research':ai}
        dump_yaml(output_dir/'research.yaml',artifact); return artifact
