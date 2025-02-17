# SQL Agents with Open Source LLMs

This is a lab to explore sql agents with open source LLMs such as [qwen2.5-coder](https://ollama.com/library/qwen2.5-coder)
You can also see the leaderboars here:
- 1. [Hugging face big code models leaderboard](https://huggingface.co/spaces/bigcode/bigcode-models-leaderboard)
- 2. [artificialanalysis models leaderboard](https://artificialanalysis.ai/leaderboards/models)


## ◻️ Data 

The data used is from kaggle. You can find the same dataset [here](https://www.kaggle.com/datasets/fayez1/inventory-management)

## Technologies
* python
* [uv](https://docs.astral.sh/uv/)
* [langchain](https://python.langchain.com/docs/tutorials/sql_qa/#execute-sql-query)
* [langgraph](https://langchain-ai.github.io/langgraph/tutorials/introduction/)
* [ollama](https://ollama.com/library/qwen2.5-coder)
* [hugggingface](https://huggingface.co/)
* [sqlite](https://database.guide/category/dbms/rdbms/sqlite/)
* [agno](https://docs.agno.com/)



## ◻️ Setup 

◽  **Step 1** Install [uv](https://docs.astral.sh/uv/getting-started/installation/#standalone-installer)

◽  **Step 2**  Create a virtual environment

```bash
uv venv .venv 
```

◽  **Step 3** Install packages into the current environment.

If you have a pyproject.toml file with all the dependencies. Just run and the environment will be ready

```bash
uv pip install -e .
```

## ◻️ Usage
```bash
python app/main.py
```
Go to http://127.0.0.1:8046/


## ◻️ Demo
![demo](docs/demo.png)
