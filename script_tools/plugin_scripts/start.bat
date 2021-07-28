@echo off
setlocal EnableDelayedExpansion
set prog_name=%1
set cu_date=%date:~0,4%-%date:~5,2%-%date:~8,2%
set cu_time=%time:~0,8%

rem 判断进程是否已经启动
tasklist|findstr /i "!prog_name!.exe" >nul 2>&1
if %errorlevel% equ 0 (
    echo [%cu_date% %cu_time%] !prog_name! already exist
    goto EOF
)

rem 启动进程
start /b ./"!prog_name!.exe" -c ../etc/!prog_name!.conf >nul
ping -n 2 127.0.0.1 >nul 2>&1
tasklist|findstr /i "!prog_name!.exe" >nul 2>&1
if %errorlevel% neq 0 (
    echo [%cu_date% %cu_time%] start !prog_name! fail
    goto EOF
)

echo [%cu_date% %cu_time%] start !prog_name! done

:EOF
