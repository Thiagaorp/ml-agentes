@echo off
cd /d "C:\Users\thiag\OneDrive\ml-agentes"
echo. >> logs\atendente.log
echo ===== %date% %time% ===== >> logs\atendente.log
"C:\Users\thiag\AppData\Local\Programs\Python\Python313\python.exe" main.py responder --enviar >> logs\atendente.log 2>&1
