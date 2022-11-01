@echo off

setlocal EnableDelayedExpansion
set agent_config_file=gse_agent.conf
set cu_date=%date:~0,4%-%date:~5,2%-%date:~8,2%
set cu_time=%time:~0,8%
set gse_agent_daemon_path=%cd%
set gse_agent_path=%cd%
set gse_winagent_home=%cd:~0,-10%
for %%a in ("%gse_winagent_home%") do ( set service_id=%%~nxa)
if %service_id%=="gse" (set _service_id=) else (set _service_id=_%service_id%)
set gse_winagent_home=%gse_winagent_home:\=\\%
set gse_agent_config_path=%gse_winagent_home:"=%\\agent\\etc\\%agent_config_file%
set TMP_DIR=C:\tmp
set gse_agent_restart_log=%TMP_DIR%\restart_gse_agent.log

echo ================ [%date%-%time%] start ======================  >>%gse_agent_restart_log%

if not "%1"=="start" if not "%1"=="stop" if not "%1"=="restart" if not "%1"=="status" if not "%1"=="version" goto :usage
if "%1"=="start"    goto :start
if "%1"=="stop"        goto :stop
if "%1"=="restart"    goto :restart
if "%1"=="status"    goto :status
if "%1"=="version"    goto :version


:start
    sc query gse_agent_daemon%_service_id% 2>&1 | findstr /r /i /C:"RUNNING" 1>nul 2>&1
    if %errorlevel% NEQ 0 (
        gse_agent_daemon.exe --start --name gse_agent_daemon%_service_id% 1>nul 2>&1
    )

    ping -n 5 127.0.0.1 >nul 2>&1
    sc query gse_agent_daemon%_service_id% 2>&1 | findstr /r /i /C:"RUNNING" 1>nul 2>&1
    if %errorlevel% NEQ 0 (
        echo [%date%-%time%] gse_agent_daemon%_service_id% Service Status: NOT RUNNING >>%gse_agent_restart_log%
        echo [%date%-%time%] start fail -- gse_agent start fail/start process >>%gse_agent_restart_log%
        sc query gse_agent_daemon%_service_id% >>%gse_agent_restart_log%
        exit /b 1
    )
    call :status

goto :EOF

:stop
    sc query gse_agent_daemon%_service_id% | findstr /i "SERVICE_NAME" 1>nul 2>&1
    if %errorlevel% neq 0 (
        echo [%date%-%time%] stop fail -- service not exist >>%gse_agent_restart_log%
        goto :EOF
    )

    sc query gse_agent_daemon%_service_id% | findstr /r /i /C:" *STOPPED" 1>nul 2>&1
    if %errorlevel% equ 0 (
        echo [%date%-%time%] already stoped >>%gse_agent_restart_log%
        goto :EOF
    )

    gse_agent_daemon.exe --quit --name gse_agent_daemon%_service_id% 1>nul 2>&1
    if %errorlevel% neq 0 (
        echo [%date%-%time%] stop Service gse_agent_daemon%_service_id% failed, then user wmic to terminate process >>%gse_agent_restart_log%
        ping -n 5 127.0.0.1 1>nul 2>&1
        wmic process where name="'gse_agent_daemon.exe' and ExecutablePath='%gse_winagent_home:"=%\\agent\\bin\\gse_agent_daemon.exe'" call terminate 1>nul 2>&1
        wmic process where name="'gse_agent.exe' and ExecutablePath='%gse_winagent_home:"=%\\agent\\bin\\gse_agent.exe'" call terminate 1>nul 2>&1
        wmic process where name="'basereport.exe' and ExecutablePath='%gse_winagent_home:"=%\\plugins\\bin\\basereport.exe'" call terminate 1>nul 2>&1
        wmic process where name="'bkmetricbeat.exe' and ExecutablePath='%gse_winagent_home:"=%\\plugins\\bin\\bkmetricbeat.exe'" call terminate 1>nul 2>&1
        wmic process where name="'gsecmdline.exe' and ExecutablePath='%gse_winagent_home:"=%\\plugins\\bin\\gsecmdline.exe'" call terminate 1>nul 2>&1
        wmic process where name="'processbeat.exe' and ExecutablePath='%gse_winagent_home:"=%\\plugins\\bin\\processbeat.exe'" call terminate 1>nul 2>&1
    )

    sc query gse_agent_daemon%_service_id% | findstr /r /i /C:" *STOPPED" 1>nul 2>&1
    if %errorlevel% equ 0 (
        echo [%date%-%time%] stop Service gse_agent_daemon%_service_id% success >>%gse_agent_restart_log%
        goto :EOF
    ) else (
        sc stop gse_agent_daemon%_service_id% 
    )

    sc query gse_agent_daemon%_service_id% | findstr /r /i /C:" *STOPPED" 1>nul 2>&1
    if %errorlevel% equ 0 (
        echo [%date%-%time%] stop Service gse_agent_daemon%_service_id% success >>%gse_agent_restart_log%
        goto :EOF
    ) else (
        echo [%date%-%time%] stop Service gse_agent_daemon%_service_id% failed >>%gse_agent_restart_log%
    )
)
goto :EOF

:restart
    call :stop
    call :start
goto :EOF

:status
    sc query gse_agent_daemon%_service_id% 2>&1 | findstr /r /i /C:"RUNNING" 1>nul 2>&1
    if %errorlevel% NEQ 0 (
        echo [%date%-%time%] gse_agent_daemon%_service_id% Service Status: NOT RUNNING >>%gse_agent_restart_log%
        sc query gse_agent_daemon%_service_id%
        exit /b 1
    )

    ping -n 5 127.0.0.1 1>nul 2>&1
    netstat -an | findstr /r /C:":28668 *ESTABLISHED" 1>nul 2>&1
    if %errorlevel% EQU 0 (
        echo [%date%-%time%] echo gse_agent_daemon%_service_id% Service Status: RUNNING and Network Connection: ESTABLISHED >>%gse_agent_restart_log%
        sc query gse_agent_daemon%_service_id%
        netstat -an | findstr /r /C:":28668 *ESTABLISHED"
    ) else (
        echo [%date%-%time%] echo gse_agent_daemon%_service_id% Service Status: RUNNING and Network Connection: NOT ESTABLISHED >>%gse_agent_restart_log%
        sc query gse_agent_daemon%_service_id%
        netstat -an | findstr /r /C:":28668 *ESTABLISHED"
        exit /b 1
    )
goto :EOF

:version
%gse_agent_daemon_path%\gse_agent.exe --version
goto :EOF

:usage
    echo usage: gsectl.bat OPTIONS
    echo OPTIONS
    echo    start    start the gse_agent
    echo    stop     stop the gse_agent
    echo    restart  restart the gse_agent
    echo    status   status of the gse_agent
    echo    version  get the gse_agent version
goto :EOF

:EOF
