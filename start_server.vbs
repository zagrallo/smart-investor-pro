Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\hlifc\OneDrive\Desktop\MARKTG~1\SMART-~1"
WshShell.Run "python -m uvicorn main:app --host 127.0.0.1 --port 8000", 0, False
