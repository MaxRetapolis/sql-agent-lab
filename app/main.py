import os
import gradio as gr
import atexit
import threading
import time
from sql_agent.agno_agent import Text2SQLAgent
from sql_agent.utils import logger 
from sql_agent.utils.status_reporter import StatusReporter
from sql_agent.prompt import FULL_REPORT

log = logger.get_logger(__name__)
log = logger.init(level="DEBUG", save_log=True)

# Configuration
UI_PORT: int = int(os.getenv("UI_PORT", "8046"))
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://192.168.1.37:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen2.5-coder:7b")
STATUS_INTERVAL = int(os.getenv("STATUS_INTERVAL", "60"))  # Update status every 60 seconds
PLACE_HOLDER = "Ask a question about the data..."
BOTH_ICON = "app/assets/bot.png"
USER_ICON = "app/assets/user.png"

# Create a singleton agent instance
# Default to attempting local Ollama first, but provide remote as fallback
agent = Text2SQLAgent(ollama_host=OLLAMA_HOST, model_id=DEFAULT_MODEL)
current_db = agent.current_db_name
current_model = agent.current_model_id
ollama_mode = agent.ollama_mode  # Will be "local" or "remote"

# Query tracking
query_history = []
start_time = time.time()

# Create a status reporter
def get_additional_status():
    """Get additional status information."""
    uptime = time.time() - start_time
    hours, remainder = divmod(uptime, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    # Get last query info
    last_query = status_reporter.persistence.state.get("last_query", {})
    last_query_str = ""
    if last_query:
        last_query_str = f"Time: {last_query.get('timestamp', 'Unknown')}\n"
        last_query_str += f"Question: {last_query.get('last_question', 'Unknown')}\n"
        if "sql_query" in last_query:
            last_query_str += f"SQL: {last_query.get('sql_query', 'Unknown')}\n"
        if "execution_time" in last_query:
            last_query_str += f"Execution time: {last_query.get('execution_time', 'Unknown')}\n"
        if "error" in last_query:
            last_query_str += f"Error: {last_query.get('error', 'Unknown')}\n"
    
    return {
        "System Info": f"Uptime: {int(hours)}h {int(minutes)}m {int(seconds)}s\nStarted: {time.ctime(start_time)}",
        "Latest Query": last_query_str if last_query_str else "No queries executed yet"
    }

status_reporter = StatusReporter(
    state_file="app/data/session_state.json",
    status_file="SESSION_STATUS.md",
    auto_save_interval=STATUS_INTERVAL,
    status_callback=get_additional_status
)

# Initialize the status reporter with current state
status_reporter.update_database_info(agent.databases, current_db)
status_reporter.update_model_info(agent.models, current_model)
status_reporter.update_config({
    "ollama_host": OLLAMA_HOST,
    "ui_port": UI_PORT
})

# Start the status reporter thread
status_reporter.start()

# Register cleanup function
@atexit.register
def cleanup():
    """Clean up resources before exit."""
    log.info("Shutting down...")
    status_reporter.update_now(force=True)
    status_reporter.stop()
    log.info("Cleanup complete")

def respond(question, history):
    """Respond to user input."""
    global agent, current_db, current_model, ollama_mode, status_reporter
    
    # Initialize statistics
    query_stats = {
        "last_question": question,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Check if it's a database selection command
    if question.startswith("/db "):
        db_name = question[4:].strip()
        success = agent.set_active_database(db_name)
        if success:
            current_db = db_name
            # Update status file with new database info
            status_reporter.update_database_info(agent.databases, current_db)
            return f"Database changed to: {db_name}\n\n{agent.db_discovery.get_formatted_schema(db_name)}"
        else:
            return f"Error: Database '{db_name}' not found. Available databases: {', '.join(agent.databases.keys())}"
    
    # Check if it's a model selection command
    if question.startswith("/model "):
        model_name = question[7:].strip()
        success = agent.set_active_model(model_name)
        if success:
            current_model = model_name
            # Update status file with new model info
            status_reporter.update_model_info(agent.models, current_model)
            return f"Model changed to: {model_name}"
        else:
            return f"Error: Model '{model_name}' not found or failed to initialize"
    
    # Handle database listing command
    if question.strip() == "/list_db":
        db_list = list(agent.databases.keys())
        if db_list:
            return f"Available databases: {', '.join(db_list)}\nCurrent database: {current_db}\n\nUse /db [name] to switch databases."
        else:
            return "No databases found in the data directory."
    
    # Handle model listing command
    if question.strip() == "/list_models":
        # Refresh models
        agent.get_model_list()
        model_list = list(agent.models.keys())
        
        # Update status file with model info
        status_reporter.update_model_info(agent.models, current_model)
        
        if model_list:
            model_info = []
            for name, info in agent.models.items():
                model_info.append(f"- {name} ({info.size})")
            
            return f"Available models:\n" + "\n".join(model_info) + f"\n\nCurrent model: {current_model}\nMode: {ollama_mode.upper()}\n\nUse /model [name] to switch models.\nUse /local or /remote to switch Ollama mode."
        else:
            return f"No Ollama models found in {ollama_mode.upper()} mode.\nTry switching modes with /local or /remote."
    
    # Handle switch to local Ollama
    if question.strip() == "/local":
        if agent.ollama_mode == "local":
            return "Already in LOCAL mode."
        
        success = agent.switch_to_local_mode()
        if success:
            current_model = agent.current_model_id
            ollama_mode = "local"
            status_reporter.update_config({"ollama_mode": "local"})
            return f"Switched to LOCAL Ollama mode.\nUsing model: {current_model}\nAvailable models: {', '.join(agent.models.keys()) if agent.models else 'None'}"
        else:
            return "Failed to switch to LOCAL mode. Check if Ollama is installed and running on this machine."
    
    # Handle switch to remote Ollama
    if question.strip() == "/remote":
        if agent.ollama_mode == "remote":
            return "Already in REMOTE mode."
        
        success = agent.switch_to_remote_mode()
        if success:
            current_model = agent.current_model_id
            ollama_mode = "remote"
            status_reporter.update_config({"ollama_mode": "remote", "ollama_host": agent.ollama_host})
            return f"Switched to REMOTE Ollama mode.\nHost: {agent.ollama_host}\nUsing model: {current_model}\nAvailable models: {', '.join(agent.models.keys()) if agent.models else 'None'}"
        else:
            return f"Failed to connect to remote Ollama at {agent.ollama_host}. Try setting a different host with /set_ollama_host."
    
    # Handle connection status
    if question.strip() == "/status":
        ollama_status = "Connected" if agent.ollama_available else "Not connected"
        
        # Force update status file
        status_reporter.update_now(force=True)
        
        return f"""System Status:
- Ollama: {ollama_status} (mode: {ollama_mode.upper()})
- Ollama host: {agent.ollama_host}
- Current model: {current_model}
- Current database: {current_db}
- Available databases: {', '.join(agent.databases.keys())}
- Available models: {', '.join(agent.models.keys()) if agent.models else "None"}
- Status file: {status_reporter.status_file}
- State file: {status_reporter.persistence.state_file}

Use /local to switch to local Ollama
Use /remote to switch to remote Ollama
"""
        
    # Handle Ollama test command
    if question.strip() == "/test_ollama" or question.strip() == "/check_ollama":
        # Get detailed Ollama info
        model_discovery = agent.model_discovery
        ollama_info = model_discovery.get_ollama_info()
        
        status_msg = "✅ Connected" if ollama_info["status"] == "available" else "❌ Connection failed"
        version = ollama_info.get("version", "Unknown")
        model_count = ollama_info.get("model_count", "Unknown")
        error = ollama_info.get("error", "None")
        
        result = f"""Ollama Connection Test:
- Host: {OLLAMA_HOST}
- Status: {status_msg}
- Version: {version}
"""
        
        if model_count != "Unknown":
            result += f"- Models available: {model_count}\n"
            
        if error and error != "None":
            result += f"- Error: {error}\n"
            
        # Add additional troubleshooting info
        if ollama_info["status"] != "available":
            result += """
Troubleshooting steps:
1. Verify Ollama is running on the specified host
2. Check network connectivity to the host
3. Ensure port 11434 is open on the host
4. Try running this command on the host: curl http://localhost:11434/api/version

To change the Ollama host, use:
/set_ollama_host http://new-host:11434
"""
        else:
            result += "\nConnection successful! You can use /list_models to see available models."
            
        return result
        
    # Handle scan for Ollama servers
    if question.strip() == "/scan_ollama":
        return """Running network scan for Ollama servers...

This will scan your network for Ollama servers. To run the scan, execute this command in a terminal:

```bash
cd /home/coder/claude_code/sql-agent
python3 scripts/scan_ollama.py
```

For a limited scan of specific IP range:
```bash
cd /home/coder/claude_code/sql-agent
SCAN_START=30 SCAN_END=50 python3 scripts/scan_ollama.py
```

Results will be saved to OLLAMA_SCAN_RESULTS.md
"""
        
    # Handle set Ollama host command
    if question.strip().startswith("/set_ollama_host "):
        new_host = question[17:].strip()
        
        if not new_host.startswith(("http://", "https://")):
            return "Error: Host URL must start with http:// or https://"
        
        global OLLAMA_HOST
        old_host = OLLAMA_HOST
        OLLAMA_HOST = new_host
        
        # Update agent with new host
        try:
            # Create a new model discovery with the new host
            agent.model_discovery = agent.utils.models.discovery.OllamaDiscovery(ollama_host=new_host)
            
            # Test connection
            ollama_info = agent.model_discovery.get_ollama_info()
            if ollama_info["status"] == "available":
                # Update config in status file
                status_reporter.update_config({"ollama_host": new_host})
                
                # Refresh models
                agent.get_model_list()
                status_reporter.update_model_info(agent.models, agent.current_model_id)
                
                return f"✅ Ollama host changed from {old_host} to {new_host}\nConnection successful! Version: {ollama_info.get('version', 'Unknown')}"
            else:
                # If connection fails, revert to old host
                agent.model_discovery = agent.utils.models.discovery.OllamaDiscovery(ollama_host=old_host)
                OLLAMA_HOST = old_host
                return f"❌ Failed to connect to {new_host}: {ollama_info.get('error', 'Unknown error')}\nReverted to {old_host}\n\nTry using /scan_ollama to find available Ollama servers on your network."
        except Exception as e:
            # If any error occurs, revert to old host
            OLLAMA_HOST = old_host
            return f"❌ Error: {str(e)}\nReverted to {old_host}"
    
    # Handle recovery command        
    if question.strip() == "/recover":
        # Load state from file
        state = status_reporter.persistence.load_state()
        
        # Try to restore database
        db_name = state.get("current_db")
        if db_name and db_name in agent.databases:
            agent.set_active_database(db_name)
            current_db = db_name
        
        # Try to restore model
        model_name = state.get("current_model")
        if model_name:
            try:
                agent.set_active_model(model_name)
                current_model = model_name
            except:
                pass  # Ignore model errors, just continue with current model
        
        return f"""Recovery attempted from state file:
- Database set to: {current_db}
- Model set to: {current_model}

Use /status to verify the current state.
"""
            
    # Handle help command
    if question.strip() == "/help":
        return """
SQL Database Explorer - Available Commands:

Database Commands:
/list_db - List all available databases
/db [name] - Switch to the specified database
/schema - Show schema of the current database

Model Commands:
/list_models - List all available Ollama models
/model [name] - Switch to the specified model

Ollama Commands:
/local - Switch to local Ollama instance
/remote - Switch to remote Ollama instance
/test_ollama - Test connectivity to current Ollama server
/set_ollama_host [url] - Change remote Ollama server (e.g., /set_ollama_host http://192.168.1.100:11434)
/scan_ollama - Scan network for Ollama servers

System Commands:
/status - Show system status
/recover - Attempt to restore state from saved file
/help - Show this help message

Type your question in natural language to query the database.
"""
    
    # Handle schema command
    if question.strip() == "/schema":
        if current_db in agent.databases:
            return agent.db_discovery.get_formatted_schema(current_db)
        else:
            return f"Current database: {current_db} (custom connection)"
    
    # Process a regular query
    try:
        # Update statistics
        query_stats["type"] = "sql_query"
        query_stats["database"] = current_db
        query_stats["model"] = current_model
        
        # Execute query
        start_time = time.time()
        sql_query, answer = agent.request(question)
        query_time = time.time() - start_time
        
        # Update statistics
        query_stats["sql_query"] = sql_query
        query_stats["execution_time"] = f"{query_time:.2f}s"
        
        # Update status with latest query
        status_reporter.persistence.state["last_query"] = query_stats
        status_reporter.update_now()
        
        # Format response
        response = FULL_REPORT.format(
            db_name=current_db,
            sql_query=sql_query, 
            sql_results=answer
        )
        return response
    except Exception as e:
        log.error(f"Error processing query: {e}")
        
        # Update statistics for error
        query_stats["type"] = "error"
        query_stats["error"] = str(e)
        status_reporter.persistence.state["last_query"] = query_stats
        status_reporter.update_now()
        
        return f"Error processing query: {str(e)}\n\nPlease check if Ollama is running and try again with /status command."

# Set up examples based on available databases
examples = []
if "shop" in agent.databases:
    examples.extend([
        "What products are available in the 'Women' category?",
        "Which products were purchased in order ID 3?",
        "Which products have a price higher than $120?"
    ])
elif "inventory" in agent.databases:
    examples.extend([
        "How many items are in stock?",
        "Which products have low inventory?",
        "What's the average lead time for products?"
    ])

with gr.Blocks() as app:
    gr.Markdown("# SQL Database Explorer")
    gr.Markdown("Ask questions about your data in natural language")
    
    with gr.Row():
        with gr.Column(scale=1):
            # System info section
            with gr.Accordion("System Information", open=True):
                sys_info = gr.Markdown(f"""
**Ollama Status:** {"Connected" if agent.ollama_available else "Not Connected"}
**Ollama Mode:** {ollama_mode.upper()}
**Ollama Host:** {agent.ollama_host}
**Type /status for more details**
                """)
                
                # Add Ollama mode selection
                with gr.Row():
                    local_btn = gr.Button("Use Local Ollama")
                    remote_btn = gr.Button("Use Remote Ollama")
                
                # Add an Ollama test button
                test_ollama_btn = gr.Button("Test Ollama Connection")
                ollama_test_result = gr.Markdown("Click the button to test connection")
            
            # Database info section
            with gr.Accordion("Database Information", open=True):
                db_info = gr.Markdown(f"**Current Database:** {current_db}")
                db_list = gr.Markdown("\n".join([
                    "**Available Databases:**",
                    ", ".join(agent.databases.keys()),
                    "\nUse /list_db to see all databases and /db [name] to switch"
                ]))
                
            # Model info section
            with gr.Accordion("Model Information", open=True):
                model_info = gr.Markdown(f"**Current Model:** {current_model}")
                model_list = gr.Markdown("\n".join([
                    "**Available Models:**",
                    ", ".join(agent.models.keys()) if agent.models else "None (Ollama not available)",
                    "\nUse /list_models to see all models and /model [name] to switch"
                ]))
                
            # Command reference
            with gr.Accordion("Available Commands", open=False):
                gr.Markdown("""
- **/help** - Show help
- **/status** - System status
- **/list_db** - List databases  
- **/db [name]** - Switch database
- **/schema** - Show schema
- **/list_models** - List models
- **/model [name]** - Switch model
- **/test_ollama** - Test Ollama connection
- **/recover** - Restore session
                """)
                
            # Add refresh buttons
            with gr.Row():
                refresh_db_btn = gr.Button("Refresh Databases")
                refresh_model_btn = gr.Button("Refresh Models")
        
        with gr.Column(scale=2):
            # Chat interface
            chat = gr.ChatInterface(
                fn=respond,
                chatbot=gr.Chatbot(elem_id="chatbot", height="700px", avatar_images=[USER_ICON, BOTH_ICON]),
                textbox=gr.Textbox(placeholder=PLACE_HOLDER, container=False, scale=7),
                submit_btn="Send",
                retry_btn=None,
                undo_btn=None,
                clear_btn=None,
                examples=examples
            )
    
    # Add refresh functions
    def refresh_db_list():
        agent.get_database_list()
        return f"**Current Database:** {agent.current_db_name}", "\n".join([
            "**Available Databases:**",
            ", ".join(agent.databases.keys()),
            "\nUse /list_db to see all databases and /db [name] to switch"
        ])
    
    def refresh_model_list():
        agent.get_model_list()
        return f"**Current Model:** {agent.current_model_id}", "\n".join([
            "**Available Models:**",
            ", ".join(agent.models.keys()) if agent.models else "None (Ollama not available)",
            "\nUse /list_models to see all models and /model [name] to switch"
        ])
    
    def refresh_system_info():
        ollama_status = "Connected" if agent.ollama_available else "Not Connected"
        return f"""
**Ollama Status:** {ollama_status}
**Ollama Mode:** {ollama_mode.upper()}
**Ollama Host:** {agent.ollama_host}
**Type /status for more details**
        """
    
    # Define the Ollama test function
    def test_ollama_connection():
        """Test connection to Ollama server."""
        model_discovery = agent.model_discovery
        ollama_info = model_discovery.get_ollama_info()
        
        status_msg = "✅ Connected" if ollama_info["status"] == "available" else "❌ Connection failed"
        version = ollama_info.get("version", "Unknown")
        model_count = ollama_info.get("model_count", "Unknown")
        error = ollama_info.get("error", "None")
        
        result = f"""**Ollama Connection Test:**\n
- **Host:** {OLLAMA_HOST}
- **Status:** {status_msg}
- **Version:** {version}
"""
        
        if model_count != "Unknown":
            result += f"- **Models available:** {model_count}\n"
            
        if error and error != "None":
            result += f"- **Error:** {error}\n"
            
        # Add additional troubleshooting info
        if ollama_info["status"] != "available":
            result += """
**Troubleshooting steps:**
1. Verify Ollama is running on the specified host
2. Check network connectivity to the host
3. Ensure port 11434 is open on the host
4. Try running this command on the host: `curl http://localhost:11434/api/version`
"""
        else:
            # If connection is successful, update the UI
            refresh_model_list()
            result += "\n**Connection successful!** Model list has been refreshed."
            
        # Update the system status too
        sys_status = f"""
**Ollama Status:** {"Connected" if ollama_info["status"] == "available" else "Not Connected"}
**Ollama Host:** {OLLAMA_HOST}
**Version:** {version if ollama_info["status"] == "available" else "Unknown"}
**Type /status for more details**
"""
            
        return result, sys_status
    
    # Connect all buttons
    refresh_db_btn.click(
        fn=refresh_db_list,
        outputs=[db_info, db_list]
    )
    
    refresh_model_btn.click(
        fn=refresh_model_list,
        outputs=[model_info, model_list]
    )
    
    # Define Ollama mode switching functions
    def switch_to_local_ollama():
        """Switch to local Ollama mode."""
        global agent, current_model, ollama_mode
        if agent.ollama_mode == "local":
            return f"Already in LOCAL mode.", refresh_system_info()
        
        success = agent.switch_to_local_mode()
        if success:
            current_model = agent.current_model_id
            ollama_mode = "local"
            status_reporter.update_config({"ollama_mode": "local"})
            
            # Update model list
            new_model_info, new_model_list = refresh_model_list()
            
            return f"Switched to LOCAL Ollama mode.\nUsing model: {current_model}", refresh_system_info()
        else:
            return f"Failed to switch to LOCAL mode.\nCheck if Ollama is installed on this machine.", refresh_system_info()
    
    def switch_to_remote_ollama():
        """Switch to remote Ollama mode."""
        global agent, current_model, ollama_mode
        if agent.ollama_mode == "remote":
            return f"Already in REMOTE mode.", refresh_system_info()
        
        success = agent.switch_to_remote_mode()
        if success:
            current_model = agent.current_model_id
            ollama_mode = "remote"
            status_reporter.update_config({"ollama_mode": "remote", "ollama_host": agent.ollama_host})
            
            # Update model list
            new_model_info, new_model_list = refresh_model_list()
            
            return f"Switched to REMOTE Ollama mode.\nHost: {agent.ollama_host}\nUsing model: {current_model}", refresh_system_info()
        else:
            return f"Failed to connect to remote Ollama at {agent.ollama_host}.", refresh_system_info()
    
    # Connect all buttons
    test_ollama_btn.click(
        fn=test_ollama_connection,
        outputs=[ollama_test_result, sys_info]
    )
    
    local_btn.click(
        fn=switch_to_local_ollama,
        outputs=[ollama_test_result, sys_info]
    )
    
    remote_btn.click(
        fn=switch_to_remote_ollama,
        outputs=[ollama_test_result, sys_info]
    )

if __name__ == "__main__":
    log.info("Starting SQL Explorer...")
    
    # Test Ollama connection on startup
    log.info(f"Testing connection to Ollama at {OLLAMA_HOST}...")
    ollama_info = agent.model_discovery.get_ollama_info()
    
    if ollama_info["status"] == "available":
        log.info(f"✅ Successfully connected to Ollama v{ollama_info.get('version', 'unknown')}")
        if "model_count" in ollama_info:
            log.info(f"Found {ollama_info['model_count']} models on the server")
    else:
        log.warning(f"❌ Failed to connect to Ollama at {OLLAMA_HOST}")
        if ollama_info.get("error"):
            log.warning(f"Error: {ollama_info['error']}")
        log.warning("Application will start, but Ollama functionality may be limited")
    
    # Create a file with the test results
    with open("OLLAMA_TEST_RESULTS.md", "w") as f:
        f.write(f"# Ollama Connection Test\n\n")
        f.write(f"- **Test time:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- **Host:** {OLLAMA_HOST}\n")
        f.write(f"- **Status:** {'Connected' if ollama_info['status'] == 'available' else 'Failed'}\n")
        
        if ollama_info["status"] == "available":
            f.write(f"- **Version:** {ollama_info.get('version', 'unknown')}\n")
            if "model_count" in ollama_info:
                f.write(f"- **Models available:** {ollama_info['model_count']}\n")
            f.write("\nConnection successful! The application should work correctly.")
        else:
            f.write(f"- **Error:** {ollama_info.get('error', 'Unknown error')}\n\n")
            f.write("Troubleshooting steps:\n")
            f.write("1. Verify Ollama is running on the specified host\n")
            f.write("2. Check network connectivity to the host\n")
            f.write("3. Ensure port 11434 is open on the host\n")
            f.write("4. Try running this command on the host: `curl http://localhost:11434/api/version`\n")
    
    # Start the application
    app.launch(server_port=UI_PORT)
