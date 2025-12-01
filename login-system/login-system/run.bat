@echo off
echo ========================================
echo Project Delegation Platform
echo ========================================
echo.
echo Installing/updating dependencies...
pip install -r requirements.txt
echo.
echo Starting server...
echo The application will automatically find an available port.
echo.
python app.py
pause

