@echo off
title Llama Monitor

echo Starting server...

cd /d K:\AI\llama.cpp GUI

start "" cmd /c ^
"llama-server.exe ^
  -m Xiaomi-MiMo-VL-Miloco-7B.Q2_K.gguf ^
  --mmproj Xiaomi-MiMo-VL-Miloco-7B.mmproj-Q8_0.gguf ^
  -c 8192 ^
  -ngl 60 ^
  --host 0.0.0.0 ^
  --port 8080"

echo Waiting for server to start...
timeout /t 5 >nul

start http://localhost:8080

echo Done. Launcher will exit automatically.
exit
