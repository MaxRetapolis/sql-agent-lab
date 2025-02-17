import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Annotated, Literal, Any, Optional, List
from dataclasses import dataclass
from agno.models.ollama import Ollama
from ollama import Client as OllamaClient
from agno.tools.sql import SQLTools
from sqlalchemy import create_engine
from agno.agent import Agent
from sql_agent.prompt import TEXT2SQL_TEMPLATE
from sql_agent.utils import logger
import pandas as pd

log = logger.get_logger(__name__)


@dataclass
class Text2SQLAgent:
	""" Text to SQL Agent to convert natural language to SQL """	
	db_url: str
	def __post_init__(self):
		# Instantiate the Ollama model
		self.ollama_model= Ollama(id="qwen2.5-coder:7b")

		self.agent_name = "text2sql"

		# Instantiate the agent
		self.text2sql_agent = Agent(model=self.ollama_model, 
								name = self.agent_name, 
								role="Text to SQL Agent",
								instructions=[TEXT2SQL_TEMPLATE], 
								show_tool_calls=True)
		
		# Instantiate the SQLTools
		self.engine = create_engine(self.db_url)
		self.tools = SQLTools(db_engine=self.engine)

	def write_query(self, question:str):
		""" Run the agent and return the sql query
		Args:
			question (str): question
		Returns:
			sql_query (str): sql query
		"""
		response = self.text2sql_agent.run(question)
		sql_query = response.content
		return sql_query

	def execute_query(self, sql_query:str):
		""" Run the sql query 
		Args:
			sql_query (str): sql query
		Returns:
			results: Results
		"""
		data = self.tools.run_sql(sql=sql_query)
		df = pd.DataFrame(data)
		if df.empty:
			return "No hay datos"
		else:
			return df.to_html()

	def request(self, question):
		""" Run the agent and return the answer. """
		
		log.info(f"Writing sql query for the question:{question}")
		sql_query = self.write_query(question)
		log.info(f"Executing the sql query:{sql_query}")
		answer = self.execute_query(sql_query)
		return sql_query,answer