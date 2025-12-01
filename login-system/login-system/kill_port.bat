@echo off
echo Killing process on port 8080...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8080 ^| findstr LISTENING') do (
    echo Found process %%a
    taskkill /F /PID %%a
    echo Process killed.
)
echo Done.
pause



