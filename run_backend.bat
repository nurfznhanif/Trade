@echo off
REM Launcher BACKEND app HP - DOUBLE-KLIK file ini (nggak perlu ngetik apa-apa).
REM Nyalain backend + tunnel, nyetak ALAMAT RUMAH & ALAMAT LUAR. Tutup jendela = backend mati.
cd /d "%~dp0"
".venv\Scripts\python.exe" scripts\serve.py
pause
