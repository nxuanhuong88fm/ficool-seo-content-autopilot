from __future__ import annotations
import os
from openai import OpenAI
class ResearchError(RuntimeError): pass
class OpenAIResearchClient:
    def __init__(self,api_key=None,model=None):
        key=api_key or os.getenv('OPENAI_API_KEY','')
        if not key: raise ResearchError('OPENAI_API_KEY is required')
        self.client=OpenAI(api_key=key); self.model=model or os.getenv('OPENAI_TEXT_MODEL','gpt-5.6-luna')
    def research(self,prompt):
        response=self.client.responses.create(model=self.model,tools=[{'type':'web_search'}],input=prompt,store=False)
        return {'text':response.output_text,'sources':[]}
