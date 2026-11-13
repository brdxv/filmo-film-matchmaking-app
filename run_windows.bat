@echo off
echo Installing Python backend requirements...
cd backend
py -m pip install -r requirements.txt
cd ..
echo Installing Electron dependencies...
npm install
echo Starting FILMO...
npm start
pause
