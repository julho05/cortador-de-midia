@echo off
rem Gera dist\CortadorDeMidia.exe com o ffmpeg embutido
cd /d "%~dp0"
for /f "delims=" %%i in ('python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"') do set FFMPEG=%%i
copy /y "%FFMPEG%" ffmpeg.exe >nul
python -m PyInstaller --noconfirm --onefile --windowed --name CortadorDeMidia --collect-data customtkinter --add-binary "ffmpeg.exe;." cortador.py
del ffmpeg.exe
echo.
echo Pronto: dist\CortadorDeMidia.exe
