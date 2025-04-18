#!/bin/bash

# Activate and start Assistant (uses its own venv)
source /venv/assistant/bin/activate
cd /app/assistant
echo "Starting Assistant on port 12393..."
python run_server.py &

# Activate and start BE (FastAPI) - shared venv
source /venv/another/bin/activate
cd /app/be
echo "Starting FastAPI BE on port 8101..."
uvicorn main:app --host 0.0.0.0 --port 8101 &

# Start FE (Streamlit) - shared venv
cd /app/fe
echo "Starting Streamlit FE on port 8501..."
streamlit run page_controller.py --server.port 8501
