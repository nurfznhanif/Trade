@echo off
REM Launcher dashboard Trade — DOUBLE-KLIK file ini buat buka dashboard.
REM (nggak perlu ngetik apa-apa, nggak perlu aktifin venv)
cd /d "%~dp0"
".venv\Scripts\python.exe" -m streamlit run dashboard.py
