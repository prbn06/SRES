@echo off
title SRES - Student Registration & Enrollment System

echo  [*] Starting Flask server...
echo  [*] Opening browser at http://127.0.0.1:5000
echo.
echo  Press Ctrl+C to stop the server.
echo.

start "" "http://127.0.0.1:5000"

:: Run the Flask app
python app.py

pause
