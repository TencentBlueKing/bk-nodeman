@echo off

setlocal EnableDelayedExpansion
set cu_date=%date:~0,4%-%date:~5,2%-%date:~8,2%
set cu_time=%time:~0,8%
set gse_agent_daemon_path=%cd%
set gse_agent_path=%cd%
set gse_winagent_home=%cd:~0,-10%
set service_id=%gse_winagent_home:~3,20%
if %service_id%=="gse" (set _service_id=) else (set _service_id=_%service_id%)
rem set _service_id=_%service_id%
set gse_winagent_home=%gse_winagent_home:\=\\%
set gse_agent_etc_path=%cd:~0,-3%etc
rem if not exist %cd:~0,-9%.service_id (set _service_id=) else (set /p service_id=<%cd:~0,-9%.service_id && set _service_id=_%service_id%)

if not "%1"=="start" if not "%1"=="stop" if not "%1"=="restart" if not "%1"=="version" goto :usage

if "%1"=="start"    goto :start
if "%1"=="stop"        goto :stop
if "%1"=="restart"    goto :restart
if "%1"=="version"    goto :version

:start
rem 判断进程是否已经启动
wmic process where name='gse_agent_daemon.exe' get processid,executablepath,name 2>&1 | findstr /i "%gse_agent_daemon_path%" 1>nul 2>&1
if !errorlevel! equ 0 (
    wmic process where name='gse_agent.exe' get processid,executablepath,name 2>&1 | findstr /i "%gse_agent_path%" 1>nul 2>&1
    if !errorlevel! equ 0 (
    echo [%cu_date% %cu_time%] start fail -- gse_agent already exist
    goto :EOF
    )
)

rem 启动进程
gse_agent_daemon.exe --file %gse_agent_etc_path%\agent.conf --name gse_agent_daemon%_service_id% 1>nul 2>&1
ping -n 1 127.0.0.1 >nul 2>&1
wmic process where name='gse_agent_daemon.exe' get processid,executablepath,name 2>&1 | findstr /i "%gse_agent_daemon_path%" 1>nul 2>&1
if !errorlevel! neq 0 (
    wmic process where name='gse_agent.exe' get processid,executablepath,name 2>&1 | findstr /i "%gse_agent_path%" 1>nul 2>&1
    if !errorlevel! neq 0 (
    echo [%cu_date% %cu_time%] start fail -- gse_agent start fail/start process
    goto :EOF
    )
) else (
    echo [%cu_date% %cu_time%] start done -- start done/start process
)
goto :EOF

:stop
rem 判断gse服务是否存在
sc query gse_agent_daemon%_service_id% | findstr /i "SERVICE_NAME" 1>nul 2>&1
if !errorlevel! neq 0 (
    echo [%cu_date% %cu_time%] stop fail -- service not exist
    goto :EOF
) else (
    rem 判断进程是否已经停止
    wmic process where name='gse_agent_daemon.exe' get processid,executablepath,name 2>&1 | findstr /i "%gse_agent_daemon_path%" 1>nul 2>&1
    if !errorlevel! neq 0 (
    wmic process where name='gse_agent.exe' get processid,executablepath,name 2>&1 | findstr /i "%gse_agent_path%" 1>nul 2>&1
        if !errorlevel! neq 0 (
            echo [%cu_date% %cu_time%] stop fail -- gse_agent not exist , already stopped !
            wmic process where name="'gse_agent_daemon.exe' and ExecutablePath='%gse_winagent_home:"=%\\agent\\bin\\gse_agent_daemon.exe'" call terminate 1>nul 2>&1
            wmic process where name="'gse_agent.exe' and ExecutablePath='%gse_winagent_home:"=%\\agent\\bin\\gse_agent.exe'" call terminate 1>nul 2>&1
            wmic process where name="'basereport.exe' and ExecutablePath='%gse_winagent_home:"=%\\plugins\\bin\\basereport.exe'" call terminate 1>nul 2>&1
            wmic process where name="'bkmetricbeat.exe' and ExecutablePath='%gse_winagent_home:"=%\\plugins\\bin\\bkmetricbeat.exe'" call terminate 1>nul 2>&1
            wmic process where name="'gsecmdline.exe' and ExecutablePath='%gse_winagent_home:"=%\\plugins\\bin\\gsecmdline.exe'" call terminate 1>nul 2>&1
            wmic process where name="'processbeat.exe' and ExecutablePath='%gse_winagent_home:"=%\\plugins\\bin\\processbeat.exe'" call terminate 1>nul 2>&1
            sc delete gse_agent_daemon%_service_id% 
            goto :EOF
        )
    )

    rem 停止进程
    gse_agent_daemon.exe --quit --name gse_agent_daemon%_service_id% 1>nul 2>&1
    ping -n 1 127.0.0.1 >nul 2>&1
    wmic process where name="'gse_agent_daemon.exe' and ExecutablePath='%gse_winagent_home:"=%\\agent\\bin\\gse_agent_daemon.exe'" call terminate 1>nul 2>&1
    wmic process where name="'gse_agent.exe' and ExecutablePath='%gse_winagent_home:"=%\\agent\\bin\\gse_agent.exe'" call terminate 1>nul 2>&1
    wmic process where name="'basereport.exe' and ExecutablePath='%gse_winagent_home:"=%\\plugins\\bin\\basereport.exe'" call terminate 1>nul 2>&1
    wmic process where name="'bkmetricbeat.exe' and ExecutablePath='%gse_winagent_home:"=%\\plugins\\bin\\bkmetricbeat.exe'" call terminate 1>nul 2>&1
    wmic process where name="'gsecmdline.exe' and ExecutablePath='%gse_winagent_home:"=%\\plugins\\bin\\gsecmdline.exe'" call terminate 1>nul 2>&1
    wmic process where name="'processbeat.exe' and ExecutablePath='%gse_winagent_home:"=%\\plugins\\bin\\processbeat.exe'" call terminate 1>nul 2>&1
    ping -n 1 127.0.0.1 >nul 2>&1
    wmic process where name='gse_agent_daemon.exe' get processid,executablepath,name 2>&1 | findstr /i "%gse_agent_daemon_path%" 1>nul 2>&1
    if !errorlevel! neq 0 (
        wmic process where name='gse_agent.exe' get processid,executablepath,name 2>&1 | findstr /i "%gse_agent_path%" 1>nul 2>&1
        if !errorlevel! neq 0 (
            echo [%cu_date% %cu_time%] stop done -- stop done/stop process
            exit /b 0
            goto :EOF
        )
    ) else (
        echo [%cu_date% %cu_time%] stop fail -- gse_agent stop fail/stop process
        exit /b 1
    )
)
goto :EOF

:restart
call :stop
call :start
goto :EOF

:version
gse_agent.exe --version
goto :EOF

:usage
    echo usage: gsectl.bat OPTIONS
    echo OPTIONS
    echo    start    start the gse_agent
    echo    stop     stop the gse_agent
    echo    restart  restart the gse_agent
    echo    version  get the gse_agent version
goto :EOF

:EOF