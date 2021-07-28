@echo off
set prog_name=%1
set script_dir=%~dp0
cd /d %script_dir%
call stop.bat !prog_name!
call start.bat !prog_name!
