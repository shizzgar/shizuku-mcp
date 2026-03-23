#!/bin/bash
if [ -d "venv" ]; then
    source venv/bin/activate
fi
export PYTHONUNBUFFERED=1
python src/main.py
