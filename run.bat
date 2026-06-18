@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Premier lancement : creation de l'environnement...
    py -3.10 -m venv .venv
    if errorlevel 1 (
        echo Erreur: Python 3.10 introuvable. Installe-le depuis python.org.
        pause
        exit /b 1
    )
)

".venv\Scripts\python.exe" -m pip show customtkinter >nul 2>&1
if errorlevel 1 (
    echo Installation des dependances...
    ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
)

".venv\Scripts\python.exe" main.py
if errorlevel 1 pause
