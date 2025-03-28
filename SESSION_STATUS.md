# SQL Agent Session State
Last Updated: Thu Mar 28 14:54:00 2025

## Configuration
- Ollama Host: http://192.168.1.37:11434
- UI Port: 8046

## Database Information
- Current Database: shop
- Available Databases:
  - shop
  - inventory
  - usage

## Model Information
- Current Model: qwen2.5-coder:0.5b
- Available Models:
  - qwen2.5-coder:0.5b (531 MB) - ❌ Tensor initialization error
  - qwen2.5-coder:1.5b (986 MB) - ❌ Tensor initialization error
  - deepseek-r1:1.5b (1.1 GB) - ⚠️ Timeout (60 seconds)
  - llama3.2:1b (1.3 GB) - ❌ Tensor initialization error
  - phi:latest (1.6 GB) - ⚠️ Timeout (60 seconds)
  - gemma2:latest (5.4 GB) - ❌ Unknown model architecture

## Additional Information

### System Info
Uptime: 0h 0m 0s
Started: Wed Mar 27 00:00:00 2025

### Latest Query
No queries executed yet

## Recovery Instructions
If the application crashes or disconnects, use the following steps to recover:

1. Check the state file at `app/data/session_state.json` for the latest state
2. Restart the application - it will automatically load the saved state
3. If automatic recovery fails, manually set the database and model using commands:
   - `/db shop`
   - `/model qwen2.5-coder:0.5b`

Last Updated: 2025-03-28 14:54:00