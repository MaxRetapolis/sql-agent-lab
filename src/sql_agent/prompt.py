TEXT2SQL_TEMPLATE="""
You are an expert in SQL. You can create sql queries from natural language following these schemas:

{schema}

Return only the sql query. Don't explain the query and don't put the sql query in ```sql\n```.
"""

FULL_REPORT=  """<div class="">
  <h3>📊 Report </h3>
  <p>Database: {db_name}</p>
  <p>The sql query is: {sql_query}</p>
  <p>Here are the results:</p>
  <p>{sql_results}</p>
</div>"""

DATABASE_SELECT_TEMPLATE = """
<div class="db-selector">
  <h3>Available Databases</h3>
  <form>
    <select name="database" id="database-select">
      {options}
    </select>
    <button onclick="selectDatabase()">Select Database</button>
  </form>

  <div class="schema-info">
    <h4>Schema Information</h4>
    <pre>{schema}</pre>
  </div>
</div>

<script>
function selectDatabase() {
  const select = document.getElementById('database-select');
  const selectedDb = select.value;
  // Handle the database selection
  console.log('Selected database:', selectedDb);
  // Here you would typically make an API call to set the active database
}
</script>
"""

MODEL_SELECT_TEMPLATE = """
<div class="model-selector">
  <h3>Available Models</h3>
  <form>
    <select name="model" id="model-select">
      {options}
    </select>
    <button onclick="selectModel()">Select Model</button>
  </form>

  <div class="model-info">
    <h4>Model Information</h4>
    <pre>{info}</pre>
  </div>
</div>

<script>
function selectModel() {
  const select = document.getElementById('model-select');
  const selectedModel = select.value;
  // Handle the model selection
  console.log('Selected model:', selectedModel);
  // Here you would typically make an API call to set the active model
}
</script>
"""