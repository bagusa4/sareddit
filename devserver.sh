#!/bin/sh
source .venv/bin/activate
python -m streamlit run mysite/app.py --server.port=$PORT --server.enableCORS=false --server.enableXsrfProtection=false
 