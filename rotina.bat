@echo off
cd /d "C:\Users\thiag\OneDrive\ml-agentes"
echo. >> logs\rotina.log
echo ===== %date% %time% ===== >> logs\rotina.log
"C:\Users\thiag\AppData\Local\Programs\Python\Python313\python.exe" main.py tudo >> logs\rotina.log 2>&1
