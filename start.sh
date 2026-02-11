#!/bin/bash
cd "$(dirname "$0")"
.venv/Scripts/python.exe -m streamlit run app.py
