@echo off
REM _conf.bat - dipanggil bat lain di folder deploy\. Baca deploy\server.env (IP=...),
REM siapin kunci SSH (default %USERPROFILE%\.ssh\trade-vps) + opsi ssh/scp. Login sebagai user trade.
if not exist "deploy\server.env" (
  echo [!] deploy\server.env belum ada. Copy deploy\server.env.example jadi deploy\server.env lalu isi IP-nya.
  pause
  exit /b 1
)
for /f "usebackq eol=# tokens=1,* delims==" %%a in ("deploy\server.env") do set "%%a=%%b"
if not defined IP (
  echo [!] IP server belum diisi di deploy\server.env
  pause
  exit /b 1
)
if not defined KEY set "KEY=%USERPROFILE%\.ssh\trade-vps"
if not exist "%KEY%" (
  echo [!] File kunci SSH gak ketemu: %KEY%
  echo     Bikin dulu: ssh-keygen -t ed25519 -f "%USERPROFILE%\.ssh\trade-vps" -N ""
  pause
  exit /b 1
)
REM OpenSSH Windows nolak kunci yang bisa dibaca user lain -> kunci cuma buat user ini
icacls "%KEY%" /inheritance:r /grant:r "%USERNAME%:R" >nul 2>&1
set "SERVER=trade@%IP%"
set SSHOPT=-i "%KEY%" -o StrictHostKeyChecking=accept-new
exit /b 0
