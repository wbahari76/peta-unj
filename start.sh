#!/bin/bash
pkill -f "streamlit run" 2>/dev/null
sleep 1
venv/bin/streamlit run app.py \
  --server.sslCertFile ~/.streamlit/ssl/cert.pem \
  --server.sslKeyFile  ~/.streamlit/ssl/key.pem
