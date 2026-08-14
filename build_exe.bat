@echo off
REM Builds Local Document Assistant into a single standalone .exe
REM Run this from inside the rag_app folder, with your venv activated.

pyinstaller --noconfirm --onefile --windowed ^
  --name "LocalDocumentAssistant" ^
  --collect-all pptx ^
  --collect-all docx ^
  --collect-all openpyxl ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  desktop.py

echo.
echo Build complete. Find LocalDocumentAssistant.exe inside the "dist" folder.
pause
