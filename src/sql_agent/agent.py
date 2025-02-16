import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Annotated, Literal, Any, Optional, List
from dataclasses import dataclass
from agno.models.ollama import Ollama
from agno.agent import Agent
from sql_agent.prompt import TEXT2SQL_TEMPLATE
from sql_agent.utils import logger


log = logger.get_logger(__name__)


@dataclass
class Text2SQLAgent:
	""" Text to SQL Agent to convert natural language to SQL """	
	def __post_init__(self):
		# Instantiate the Ollama model
		self.ollama_model= Ollama(id="qwen2.5-coder:7b")
		self.agent_name = "text2sql",
		# Instantiate the agent
		self.text2sql_agent = Agent(model=self.ollama_model, 
								name = self.agent_name, 
								role="Text to SQL Agent",
								instructions=[TEXT2SQL_TEMPLATE], 
								show_tool_calls=True)

	def request(self, question):
		""" Run the agent and return the answer. """
		log.info(f"Running {self.agent_name} agent...question:{question}")
		response = self.text2sql_agent.run(question)
		answer = response.content
		log.info(f"Answer: {answer}")
		return answer