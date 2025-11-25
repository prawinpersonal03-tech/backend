#!/usr/bin/env bash
python -m pip install --upgrade pip
pip install -r requirements.txt
exec gunicorn whisper_server:app --preload --timeout 200 --bind 0.0.0.0:$PORT
