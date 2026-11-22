@echo off
setlocal
set "TEMP=E:\chatbotModels\FinalChatBot\backend\.pip-tmp"
set "TMP=%TEMP%"
set "PIP_NO_CACHE_DIR=1"
E:\chatbotModels\.venv\Scripts\python.exe -c "import tempfile; print('pip temp:', tempfile.gettempdir())"
E:\chatbotModels\.venv\Scripts\python.exe -m pip install --quiet --no-cache-dir -r requirements.txt
exit /b %ERRORLEVEL%
