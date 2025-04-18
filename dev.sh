#!/bin/bash

# Run FastAPI in the background
cd be
uvicorn main:app --host 0.0.0.0 --port 8101 &
cd ..

# Run Streamlit (foreground)
cd fe
streamlit run page_controller.py --server.port 8501
