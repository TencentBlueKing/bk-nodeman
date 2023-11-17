@echo off
rem gse agent scripts, for bk_nodeman 2.0
setlocal EnableDelayedExpansion
set cu_date=%date:~0,4%-%date:~5,2%-%date:~8,2%
set cu_time=%time:~0,8%
set timeinfo=%date% %time%
rem DEFAULT DEFINITION
set PKG_NAME=
set CLOUD_ID=
set UNINSTALL=1
set UNREGISTER_AGENT_ID=1
set BACKUP_CONFIG_FILE=procinfo.json

:CheckOpts
if "%1" EQU "-h" goto help
if "%1" EQU "-I" (set LAN_ETH_IP=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-i" (set CLOUD_ID=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-n" (set NAMES=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-t" (set PKG_VERSION=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-l" (set DOWNLOAD_URL=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-s" (set TASK_ID=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-u" (set UPGRADE=TRUE)
if "%1" EQU "-c" (set TOKEN=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-r" (set CALLBACK_URL=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-x" (set HTTP_PROXY=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-p" (set AGENT_SETUP_PATH=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-e" (set FILE_SERVER_IP=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-a" (set DATA_SERVER_IP=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-k" (set CLUSTER_SERVER_IP=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-N" (set UPSTREAM_TYPE=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-T" (set TMP_DIR=%~2) && shift && shift && goto CheckOpts && md -p %TMP_DIR%
if "%1" EQU "-v" (set VARS_LIST=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-o" (set OVERIDE=TRUE)
if "%1" EQU "-O" (set CLUSTER_PORT=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-E" (set FILE_SVR_PORT=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-A" (set DATA_PORT=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-V" (set BTSVR_THRIFT_PORT=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-B" (set BT_PORT=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-S" (set BT_PORT_START=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-Z" (set BT_PORT_END=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-K" (set TRACKER_PORT=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-U" (set INSTALL_USER=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-P" (set INSTALL_PASSWORD=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-R" (set UNINSTALL=0) && shift && shift && goto CheckOpts
if "%1" EQU "-F" (set UNREGISTER_AGENT_ID=0) && shift && goto CheckOpts
if "%1" NEQ "" echo Invalid option: "%1" && goto :EOF && exit /B 1
rem if "%1" EQU "-R" goto remove_agent_pro

if not defined UPSTREAM_TYPE (set UPSTREAM_TYPE=SERVER) else (set UPSTREAM_TYPE=%UPSTREAM_TYPE%)
if not defined HTTP_PROXY (set HTTP_PROXY=) else (set HTTP_PROXY=%HTTP_PROXY%)
if not defined INSTALL_USER (set INSTALL_USER=) else (set INSTALL_USER=%INSTALL_USER%)
if not defined INSTALL_PASSWORD (set INSTALL_PASSWORD=) else (set INSTALL_PASSWORD=%INSTALL_PASSWORD%)
rem if "%PROCESSOR_ARCHITECTURE%" == "x86" (set PKG_NAME=gse_client-windows-x86.tgz) else (set PKG_NAME=gse_client-windows-x86_64.tgz)
set PKG_NAME=%NAMES%-%PKG_VERSION%.tgz
if "%PROCESSOR_ARCHITECTURE%" == "x86" (set CPU_ARCH=x86) else (set CPU_ARCH=x86_64)
if "%CLOUD_ID%" == "0" (set NODE_TYPE=agent) else (set NODE_TYPE=pagent)
set gse_winagent_home=%AGENT_SETUP_PATH%
for %%a in ("%gse_winagent_home%") do (set service_id=%%~nxa)
if %service_id%=="gse" (set _service_id=) else (set _service_id=_%service_id%)

set gse_winagent_home=%gse_winagent_home:\=\\%
set report_line_num=3
set tmp_json_resp=%TMP_DIR%\nm.setup_agent.bat.%TASK_ID%
set tmp_json_resp_debug=%TMP_DIR%\nm.setup_agent.bat.%TASK_ID%.debug
set tmp_json_resp_report_log_1=%TMP_DIR%\nm.setup_agent.bat.%TASK_ID%.report_log.1
set tmp_json_resp_report_log_2=%TMP_DIR%\nm.setup_agent.bat.%TASK_ID%.report_log.2
set tmp_json_resp_report_log=%TMP_DIR%\nm.setup_agent.bat.%TASK_ID%.report_log
set tmp_check_deploy_result_files=%TMP_DIR%\nm.setup_agent.bat.check_deploy_result.temp.txt
set GSE_AGENT_RUN_DIR=%AGENT_SETUP_PATH%\agent\run
set GSE_AGENT_DATA_DIR=%AGENT_SETUP_PATH%\agent\data
set GSE_AGENT_LOG_DIR=%AGENT_SETUP_PATH%\agent\logs
set GSE_AGENT_ETC_DIR=%AGENT_SETUP_PATH%\agent\etc
set GSE_AGENT_BIN_DIR=%AGENT_SETUP_PATH%\agent\bin
set NEW_AGENT_SETUP_PATH=%AGENT_SETUP_PATH:\=/%
set special_AGENT_SETUP_PATH=%AGENT_SETUP_PATH:\=\\%
set PURE_AGENT_SETNUP_PATH=%AGENT_SETUP_PATH%\agent

if exist %tmp_json_resp% (DEL /F /S /Q %tmp_json_resp%)
if exist %tmp_json_resp_debug% (DEL /F /S /Q %tmp_json_resp_debug%)
if exist %tmp_json_resp_report_log_1% (DEL /F /S /Q %tmp_json_resp_report_log_1%)
if exist %tmp_json_resp_report_log_2% (DEL /F /S /Q %tmp_json_resp_report_log_2%)
if exist %tmp_json_resp_report_log% (DEL /F /S /Q %tmp_json_resp_report_log%)
if exist %tmp_check_deploy_result_files% (DEL /F /S /Q %tmp_check_deploy_result_files%)
if %UNINSTALL% EQU 0 (
    call :remove_agent_pro
    if !errorlevel! NEQ 0 (
        exit /b 1
    )
    exit /b 0
)
set /a nsttret=0
rem old for %%p in (check_env,download_pkg,remove_crontab,remove_agent_tmp,setup_agent,setup_startup_scripts,setup_crontab,check_deploy_result) do (
rem for %%p in (check_env,add_user_right,download_pkg,remove_crontab,remove_agent_tmp,setup_agent,setup_startup_scripts,check_deploy_result) do (
for %%p in (check_env,add_user_right,download_pkg,remove_agent_bin,setup_agent,setup_startup_scripts,check_deploy_result) do (
    echo %%p
    call :%%p
    if !errorlevel! NEQ 0 (
        exit /b 1
    )
    rem call :multi_report_step_status
)
if exist %tmp_json_resp_report_log% (call :last_log_process)
if %errorlevel% equ 0 (goto :EOF)

:print
    (set log_level=%1) && (set step=%2) && (set status=%3) && (set message=%4)
    set new_message=%message:"=\"%
    echo %timeinfo% %log_level% %step% %status% %message%
    echo %timeinfo% %log_level% %step% %status% %message% >> %tmp_json_resp%
    for /f %%i in ('%TMP_DIR%\unixdate.exe +%%s') do (set unixtimestamp=%%i)
    set tmp_json_body={\"timestamp\":\"%unixtimestamp%\",\"level\":\"%log_level%\",\"step\":\"%step%\",\"log\":%new_message%,\"status\":\"%status%\"}
    echo %tmp_json_body%>>%tmp_json_resp_report_log%
goto :EOF

:print_debug
    (set debug_info=%1)
    echo %debug_info% >> %tmp_json_resp_debug%
goto :EOF

:print_check_deploy_result
    (set log_level=%1) && (set step=%2) && (set status=%3) && (set message=%4)
    set new_message=%message:"=\"%
    echo %timeinfo% %log_level% %step% %status% %message% >> %tmp_check_deploy_result_files%
goto :EOF

:is_gsecmdline_ok
    copy /Y %AGENT_SETUP_PATH%\plugins\bin\gsecmdline.exe C:\Windows\System32\ 1>nul 2>&1
    if not exist %AGENT_SETUP_PATH%\plugins\bin\gsecmdline.exe (
        call :print INFO setup_agent - "gsecmdline not exist"
        call :multi_report_step_status
        goto :EOF
    )
    %AGENT_SETUP_PATH%\plugins\bin\gsecmdline.exe -D -d 1430 -s test 1>nul 2>&1
    if %errorlevel% equ 0 (
        call :print INFO setup_agent - "gsecmdline test success"
        call :multi_report_step_status
    ) else (
        call :print WARN setup_agent - "gsecmdline test failed"
        call :multi_report_step_status
    )
goto :EOF

:is_process_start_ok
    ping -n 10 127.0.0.1 >nul 2>&1
    wmic process where name='gse_agent_daemon.exe' get processid,executablepath,name 2>&1 | findstr /i ^"%AGENT_SETUP_PATH%^" 1>nul 2>&1
    if %errorlevel% neq 0 (
        call :print FAIL setup_agent FAILED "Process gse_agent_daemon.exe start failed"
        call :multi_report_step_status
        exit /b 2
    ) else (
        call :print_check_deploy_result INFO setup_agent - "Process gse_agent_daemon.exe start success" 1>nul 2>&1
        call :print INFO setup_agent - "Process gse_agent_daemon.exe start success"
        call :multi_report_step_status
    )
    wmic process where name='gse_agent.exe' get processid,executablepath,name 2>&1 | findstr /i ^"%AGENT_SETUP_PATH%^" 1>nul 2>&1
    if %errorlevel% neq 0 (
        call :print FAIL setup_agent FAILED "Process gse_agent.exe start failed"
        call :multi_report_step_status
        exit /b 2
    ) else (
        call :print_check_deploy_result INFO setup_agent - "Process gse_agent.exe start success" 1>nul 2>&1
        call :print INFO setup_agent - "Process gse_agent.exe start success"
        call :multi_report_step_status
    )
goto :EOF

:is_process_stop_ok
    wmic process where name='gse_agent_daemon.exe' get processid,executablepath,name 2>&1 | findstr /i ^"%AGENT_SETUP_PATH%^" 1>nul 2>&1
    if %errorlevel% neq 0 (
        call :print INFO setup_agent - "Process gse_agent_daemon.exe stop success"
        call :multi_report_step_status
    ) else (
        call :print FAIL setup_agent FAILED "Process gse_agent_daemon.exe stop failed"
        call :multi_report_step_status
        exit /b 3
    )
    wmic process where name='gse_agent.exe' get processid,executablepath,name 2>&1 | findstr /i ^"%AGENT_SETUP_PATH%^" 1>nul 2>&1
    if %errorlevel% neq 0 (
        call :print INFO setup_agent - "Process gse_agent.exe stop success"
        call :multi_report_step_status
    ) else (
        call :print FAIL setup_agent FAILED "Process gse_agent.exe stop failed"
        call :multi_report_step_status
        exit /b 3
    )
goto :EOF

:is_connected
    ping -n 1 127.0.0.1 >nul 2>&1
    for %%a in (%CLUSTER_PORT%,%DATA_PORT%) do (
        ping -n 1 127.0.0.1 >nul 2>&1
        netstat -an | findstr /r /C:":%%a *ESTABLISHED" 
        if !errorlevel! equ 0 (
            for /F "tokens=*" %%i in ('netstat -an ^| findstr /r /C:":%%a *ESTABLISHED"') do (set conninfo=%%i)
            call :print_check_deploy_result INFO check_deploy_result - "%%a connect to gse server success" 1>nul 2>&1
            call :print INFO check_deploy_result - "!conninfo!"
            call :multi_report_step_status
        ) else (
            call :print FAIL check_deploy_result FAILED "%%a is not connect to gse server , failed"
            call :multi_report_step_status
            exit /b 1
        )
    )
goto :EOF

:check_polices_pagent_to_upstream
    rem pagent_to_proxy_port_policies=(gse_task:28668 gse_data:28625 gse_btsvr:28925 gse_btsvr:10020-10030)
    rem pagent_listen_ports=(gse_agent:60020-60030)
    call :print INFO check_env - "check if it is reachable to port %CLUSTER_PORT% of %CLUSTER_SERVER_IP% GSE PROXY"
    call :multi_report_step_status
    echo=
    set network_not_reachable=
    for %%p in (%CLUSTER_SERVER_IP%) do (
        rem goto is_target_reachable
        for /f %%i in ('%TMP_DIR%\tcping.exe -i 0.01 %%p %CLUSTER_PORT% ^| findstr successful') do (
            rem echo %%i
            for /f "tokens=1,2 delims=successful" %%s in ("%%i") do (
            rem echo %%s
                if %%s GEQ 2 (
                    call :print INFO check_env - "%%p %CLUSTER_PORT% is reachable"
                    call :multi_report_step_status
                ) else (
                    call :print WARN check_env - "connect to upstream cluster server: %%p %CLUSTER_PORT% failed"
                    set network_not_reachable=%network_not_reachable% %%p to %CLUSTER_PORT% 
                    call :multi_report_step_status
                )
            )
        )
    )
    if "!network_not_reachable!" == "" (
        echo "reachable"
    ) else (
        call :print FAIL check_env FAILED "%network_not_reachable% is not reachable"
        call :multi_report_step_status
        exit /b 1
    )
    call :print INFO check_env - "check if it is reachable to port %DATA_PORT% of %DATA_SERVER_IP% GSE PROXY"
    call :multi_report_step_status
    echo=
    set data_network_not_reachable=
    for %%p in (%DATA_SERVER_IP%) do (
        rem goto is_target_reachable
        for /f %%i in ('%TMP_DIR%\tcping.exe -i 0.01 %%p %DATA_PORT% ^| findstr successful') do (
            rem echo %%i
            for /f "tokens=1,2 delims=successful" %%s in ("%%i") do (
            rem echo %%s
                if %%s GEQ 2 (
                    call :print INFO check_env - "%%p %DATA_PORT% is reachable"
                    call :multi_report_step_status
                ) else (
                    call :print WARN check_env - "connect to upstream data server: %%p %DATA_PORT% failed"
                    set data_network_not_reachable=%data_network_not_reachable% %%p to %DATA_PORT% 
                    call :multi_report_step_status
                )
            )
        )
    )
    if "!data_network_not_reachable!" == "" (
        echo "reachable"
    ) else (
        call :print FAIL check_env FAILED "%data_network_not_reachable% is not reachable"    
        call :multi_report_step_status
        exit /b 1
    )
    call :print INFO check_env - "check if it is reachable to port %FILE_SVR_PORT% of %FILE_SERVER_IP% GSE PROXY"
    call :multi_report_step_status
    echo=
    set file_network_not_reachable=
    for %%p in (%FILE_SERVER_IP%) do (
        for %%a in (%FILE_SVR_PORT%) do (
            rem goto is_target_reachable
            for /f %%i in ('%TMP_DIR%\tcping.exe -i 0.01 %%p %%a ^| findstr successful') do (
                rem echo %%i
                for /f "tokens=1,2 delims=successful" %%s in ("%%i") do (
                rem echo %%s
                    if %%s GEQ 2 (
                        call :print INFO check_env - "%%p %%a is reachable"
                        call :multi_report_step_status
                    ) else (
                        call :print WARN check_env - "connect to upstream file server: %%p %%a failed"
                        set file_network_not_reachable=%file_network_not_reachable% %%p to %%a 
                        call :multi_report_step_status
                    )
                )
            )
        )
    )
    if "!file_network_not_reachable!" == "" (
        echo "reachable"
    ) else (
        call :print FAIL check_env FAILED "%file_network_not_reachable% is not reachable"    
        call :multi_report_step_status
        exit /b 1
    )
goto :EOF

:check_polices_agent_to_upstream
    rem agent_to_server_port_policies=(gse_cluster:28668 gse_data:28625 gse_btsvr:28925 gse_btsvr:10020-10030)
    rem agent_listen_ports=(gse_agent:60020-60030)
    rem agent-GSE Server
    rem set NEW_UPSTREAM_IP=%UPSTREAM_IP:~2,-1%
    call :print INFO check_env - "check if it is reachable to port %CLUSTER_PORT% of %CLUSTER_SERVER_IP% GSE_CLUSTER_SERVER"
    call :multi_report_step_status
    echo=
    set network_not_reachable=
    for %%p in (%CLUSTER_SERVER_IP%) do (
        rem for %%a in (28668,28625,28925,10020) do (
        for /f %%i in ('%TMP_DIR%\tcping.exe -i 0.01 %%p %CLUSTER_PORT% ^| findstr successful') do (
            rem echo %%i
            for /f "tokens=1,2 delims=successful" %%s in ("%%i") do (
            rem echo %%s
                if %%s GEQ 2 (
                    call :print INFO check_env - "gse server %%p %CLUSTER_PORT% is reachable"
                    call :multi_report_step_status
                ) else (
                    call :print WARN check_env - "gse server %%p %CLUSTER_PORT% can not reachable"
                    set network_not_reachable=%network_not_reachable% %%p to %CLUSTER_PORT% 
                    call :multi_report_step_status
                )
            )
        )
    )
    if "!network_not_reachable!" == "" (
        echo "reachable"
    ) else (
        call :print FAIL check_env FAILED "%network_not_reachable% is not reachable"    
        call :multi_report_step_status
        exit /b 1
    )
    call :print INFO check_env - "check if it is reachable to port %DATA_PORT% of %DATA_SERVER_IP% GSE_DATA_SERVER"
    call :multi_report_step_status
    set network_not_reachable=
    for %%p in (%DATA_SERVER_IP%) do (
        rem for %%a in (28668,28625,28925,10020) do (
        for /f %%i in ('%TMP_DIR%\tcping.exe -i 0.01 %%p %DATA_PORT% ^| findstr successful') do (
            rem echo %%i
            for /f "tokens=1,2 delims=successful" %%s in ("%%i") do (
            rem echo %%s
                if %%s GEQ 2 (
                    call :print INFO check_env - "gse server %%p %DATA_PORT% is reachable"
                    call :multi_report_step_status
                ) else (
                    call :print WARN check_env - "gse server %%p %DATA_PORT% can not reachable"
                    set network_not_reachable=%network_not_reachable% %%p to %DATA_PORT% 
                    call :multi_report_step_status
                )
            )
        )
    )
    if "!network_not_reachable!" == "" (
        echo "reachable"
    ) else (
        call :print FAIL check_env FAILED "%network_not_reachable% is not reachable"    
        call :multi_report_step_status
        exit /b 1
    )
    call :print INFO check_env - "check if it is reachable to port %FILE_SVR_PORT% of %FILE_SERVER_IP% GSE_FILE_SERVER"
    call :multi_report_step_status
    set network_not_reachable=
    for %%p in (%FILE_SERVER_IP%) do (
        rem for %%a in (28668,28625,28925,10020) do (
        for %%a in (%FILE_SVR_PORT%) do (
            for /f %%i in ('%TMP_DIR%\tcping.exe -i 0.01 %%p %%a ^| findstr successful') do (
                rem echo %%i
                for /f "tokens=1,2 delims=successful" %%s in ("%%i") do (
                rem echo %%s
                    if %%s GEQ 2 (
                        call :print INFO check_env - "gse server %%p %%a is reachable"
                        call :multi_report_step_status
                    ) else (
                        set network_not_reachable=%network_not_reachable% %%p to %%a
                        call :print INFO check_env - "gse server %%p %%a can not reachable"
                        call :multi_report_step_status
                    )
                )
            )
        )
    )
    if "!network_not_reachable!" == "" (
        echo "reachable"
    ) else (
        rem set to - for test continue
        rem call :print FAIL check_env FAILED "%network_not_reachable% is not reachable"
        call :print FAIL check_env - "%network_not_reachable% is not reachable"
        call :multi_report_step_status
        exit /b 1
    )
goto :EOF

:setup_crontab
    echo Set shell = CreateObject("Wscript.Shell") > %AGENT_SETUP_PATH%\agent\bin\gsectl.vbs 1>nul 2>&1
    echo shell.run "cmd /c cd /d %AGENT_SETUP_PATH%\agent\bin\ && gsectl.bat start",0 >> %AGENT_SETUP_PATH%\agent\bin\gsectl.vbs 1>nul 2>&1
    schtasks /create /tn gse_agent /tr "cscript %AGENT_SETUP_PATH%\agent\bin\gsectl.vbs" /sc minute /mo 1 /F 1>nul 2>&1
    ping -n 1 127.0.0.1 >nul 2>&1
    schtasks /Query | findstr gse_agent 1>nul 2>&1
    if %errorlevel% equ 0 (
        call :print INFO setup_crontab - "gse_agent schtasks setup success"
        call :multi_report_step_status
    ) else (
        call :print FAIL setup_crontab FAILED "gse_agent schtasks setup failed"
        call :multi_report_step_status
    )
goto :EOF

:remove_crontab
    schtasks /Query | findstr gse_agent 1>nul 2>&1
    if %errorlevel% neq 0 (
        call :print INFO remove_agent - "gse_agent schtasks not exist , no need remove schtasks"
        call :multi_report_step_status
    ) else (
        schtasks /Delete /tn gse_agent /F 1>nul 2>&1
        schtasks /Query | findstr gse_agent 1>nul 2>&1
        if %errorlevel% neq 0 (
            call :print INFO remove_agent - "gse_agent schtasks remove success"
            call :multi_report_step_status
        )
    )
goto :EOF

:setup_startup_scripts
    reg add "HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run" /v gse_agent /t reg_sz /d "%AGENT_SETUP_PATH%\agent\bin\gsectl.bat start" /f 1>nul 2>&1
    for /f "tokens=1,2,*" %%i in ('REG QUERY HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run /v gse_agent ^| findstr /i "gse_agent"') do (
        if "%%i" == "gse_agent" (
            call :print INFO setup_startup_scripts - "set startup with os success"
        ) else (
            call :print WARN setup_startup_scripts - "set startup with os failed"
        )
    )
goto :EOF

:remove_startup_scripts
    reg delete "HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run" /v gse_agent /f 1>nul 2>&1
    REG QUERY HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run /v gse_agent 1>nul 2>&1
    if %errorlevel% neq 0 (
        call :print INFO remove_agent - "remove startup with os success"
        call :multi_report_step_status
    ) else (
        call :print WARN remove_agent - "remove startup with os failed"
        call :multi_report_step_status
    )
goto :EOF

:uninstall_agent_service
    sc query gse_agent_daemon_%service_id% 1>nul 2>&1
    if %errorlevel% neq 0 (
        call :print INFO uninstall_agent_service - "service gse_agent_daemon_%service_id% already uninstalled"
        call :multi_report_step_status
        goto :EOF
    )
    sc query gse_agent_daemon_%service_id% | findstr /r /i /C:" *STOPPED" 1>nul 2>&1
    if %errorlevel% equ 0 (
        call :print INFO uninstall_agent_service - "service gse_agent_daemon_%service_id% stopped"
        call :multi_report_step_status
    )
    %PURE_AGENT_SETNUP_PATH%\bin\gse_agent_daemon.exe --uninstall --name gse_agent_daemon_%service_id%
    if %errorlevel% equ 0 (
        call :print INFO uninstall_agent_service - "service gse_agent_daemon_%service_id% remove success"
        call :multi_report_step_status
    ) else (
        call :print FAIL uninstall_agent_service FAILED "service gse_agent_daemon_%service_id% remove failed"
        call :multi_report_step_status
        exit /b 1
    )
goto :EOF

:stop_agent
    if exist %PURE_AGENT_SETNUP_PATH% (
        cd /d %PURE_AGENT_SETNUP_PATH%\bin && .\gsectl stop 1>nul 2>&1
        ping -n 3 127.0.0.1 1>nul 2>&1
        wmic process where "name='gse_agent_daemon.exe' and ExecutablePath='%special_AGENT_SETUP_PATH%\\agent\\bin\\gse_agent_daemon.exe'" call terminate 1>nul 2>&1
        wmic process where "name='gse_agent.exe' and ExecutablePath='%special_AGENT_SETUP_PATH%\\agent\\bin\\gse_agent.exe'" call terminate 1>nul 2>&1
        cd /d %TMP_DIR%
        call :is_process_stop_ok
    ) else (
        call :print WARN stop_agent - "%PURE_AGENT_SETNUP_PATH% not exist , ERROR"
        call :multi_report_step_status
    )
goto :EOF

:remove_agent_bin
    rem install and reinstall agent
    call :print INFO remove_agent START "trying to remove old agent and bin dir"
    call :multi_report_step_status
    if exist %PURE_AGENT_SETNUP_PATH% (
        call :remove_startup_scripts
        if !errorlevel! NEQ 0 (
            exit /b 1
        )
        echo=
        call :remove_crontab
        if !errorlevel! NEQ 0 (
            exit /b 1
        )
        echo=
        call :backup_config_file_action
        if !errorlevel! NEQ 0 (
            exit /b 1
        )
        rem gseAgent 2.0 no need to remove plugin
        rem call :stop_basic_gse_plugin
        call :stop_agent
        if !errorlevel! NEQ 0 (
            exit /b 1
        )
        call :uninstall_agent_service
        if !errorlevel! NEQ 0 (
            exit /b 1
        )
    )
    if exist %PURE_AGENT_SETNUP_PATH% (
        wmic process where "name='gse_agent_daemon.exe' and ExecutablePath='%special_AGENT_SETUP_PATH%\\agent\\bin\\gse_agent_daemon.exe'" call terminate 1>nul 2>&1
        wmic process where "name='gse_agent.exe' and ExecutablePath='%special_AGENT_SETUP_PATH%\\agent\\bin\\gse_agent.exe'" call terminate 1>nul 2>&1
        wmic process where "name='basereport.exe' and ExecutablePath='%special_AGENT_SETUP_PATH%\\plugins\\bin\\basereport.exe'" call terminate 1>nul 2>&1
        wmic process where "name='gsecmdline.exe' and ExecutablePath='%special_AGENT_SETUP_PATH%\\plugins\\bin\\gsecmdline.exe'" call terminate 1>nul 2>&1
    )
    RD /Q /S %GSE_AGENT_BIN_DIR% 1>nul 2>&1
    if not exist %GSE_AGENT_BIN_DIR% (
        call :print INFO setup_agent DONE "Directory %GSE_AGENT_BIN_DIR% removed, agent\bin dir removed succeed"
        call :multi_report_step_status
    ) else (
        for /f "skip=1 delims= " %%i in ('%TMP_DIR%\handle.exe %GSE_AGENT_BIN_DIR% -nobanner') do (
            echo %%i
            taskkill /f /im %%i
        )
        RD /Q /S %GSE_AGENT_BIN_DIR% 1>nul 2>&1
        ping -n 1 127.0.0.1 >nul 2>&1
        call :print INFO setup_agent - "Directory %GSE_AGENT_BIN_DIR% removed, agent\bin dir removed succeed"
        call :multi_report_step_status
    )
goto :EOF

:get_config
    call :print INFO get_config - "request %NODE_TYPE% config files"
    call :multi_report_step_status
    set PARAM="{\"bk_cloud_id\":%CLOUD_ID%,\"filename\":\"gse_agent.conf\",\"node_type\":\"%NODE_TYPE%\",\"inner_ip\":\"%LAN_ETH_IP%\",\"token\":\"%TOKEN%\"}"
    echo call :print INFO get_config - "request config files with: %PARAM%"
    for %%p in (gse_agent.conf) do (
        if "%HTTP_PROXY%" == "" (
            %TMP_DIR%\curl.exe -g -o %TMP_DIR%\%%p --silent -w "%%{http_code}" -X POST %CALLBACK_URL%/get_gse_config/ -d %PARAM%  1>%TMP_DIR%\nm.test.HHHHHHH 2>&1
        ) else (
            %TMP_DIR%\curl.exe -g -o %TMP_DIR%\%%p --silent -w "%%{http_code}" -X POST %CALLBACK_URL%/get_gse_config/ -d %PARAM% -x %HTTP_PROXY% 1>%TMP_DIR%\nm.test.HHHHHHH 2>&1
        )
        for /f %%i in (%TMP_DIR%\nm.test.HHHHHHH) do (
            if %%i equ 200 (
                call :print INFO get_config - "request config %%p success. http status:%%i"
                call :multi_report_step_status
            ) else (
                call :print FAIL get_config FAILED "request config %%p failed. request info:%CLOUD_ID%,%LAN_ETH_IP%,%node_type%,%%p,%TOKEN%. http status:%%i"
                call :multi_report_step_status
                exit /b 1
            )
        )
    DEL /F /S /Q %TMP_DIR%\nm.test.HHHHHHH 1>nul 2>&1
    )
goto :EOF

:setup_agent
    call :print INFO setup_agent START "setup agent , extract, render config"
    call :multi_report_step_status
    if not exist %AGENT_SETUP_PATH% (md %AGENT_SETUP_PATH%)
    if exist %TMP_DIR%\agent (RD /Q /S %TMP_DIR%\agent 1>nul 2>&1)
    set TEMP_PKG_NAME=%PKG_NAME:~0,-4%
    %TMP_DIR%\7z.exe x %TMP_DIR%\%PKG_NAME% -so | %TMP_DIR%\7z.exe x -aoa -si -ttar -o%TMP_DIR% 1>nul 2>&1
    xcopy /Y /v /e %TMP_DIR%\agent\cert %AGENT_SETUP_PATH%\agent\cert\
    if %errorlevel% EQU 0 (
        call :print INFO setup_agent - "setup agent , copy cert dir success"
        call :multi_report_step_status
    ) else (
        call :print FAIL setup_agent FAILED "setup agent , copy cert dir failed"
        call :multi_report_step_status
        exit /b 1
    )
    xcopy /Y /v /e %TMP_DIR%\agent\bin  %AGENT_SETUP_PATH%\agent\bin\
    if %errorlevel% EQU 0 (
        call :print INFO setup_agent - "setup agent , copy bin dir success"
        call :multi_report_step_status
    ) else (
        call :print FAIL setup_agent FAILED "setup agent , copy bin dir failed"
        call :multi_report_step_status
        exit /b 1
    )
    if exist %AGENT_SETUP_PATH%\plugins\bin\gsecmdline.exe (copy /Y %AGENT_SETUP_PATH%\plugins\bin\gsecmdline.exe C:\Windows\System32\ 1>nul 2>&1)
    call :recovery_config_file_action
    if exist %TMP_DIR%\gse_agent.conf (DEL /F /S /Q %TMP_DIR%\gse_agent.conf 1>nul 2>&1)
    call :get_config
    set FILE_IS_OK=0
    if exist %TMP_DIR%\gse_agent.conf (
        set FILE_IS_OK=1
    ) else (
        call :print FAIL setup_agent FAILED "get config file gse_agent.conf failed"
        call :multi_report_step_status
        exit /b 1
    )
    jq --version 1>nul 2>&1
    if %errorlevel% EQU 0 (
        if %FILE_IS_OK% EQU 1 (
            jq <%TMP_DIR%\gse_agent.conf
        )
    ) else (
        if exist %TMP_DIR%\jq.exe (
            %TMP_DIR%\jq.exe <%TMP_DIR%\gse_agent.conf
        )
    )
    if %errorlevel% EQU 0 (
        call :print INFO setup_agent - "setup agent , config file gse_agent.conf is right"
        call :multi_report_step_status
    ) else (
        call :print FAIL setup_agent FAILED "setup agent , config file gse_agent.conf is error"
        call :multi_report_step_status
        exit /b 1
    )
    if not exist %GSE_AGENT_ETC_DIR% (md %GSE_AGENT_ETC_DIR%)
    for %%p in (gse_agent.conf) do (
        if exist %TMP_DIR%\%%p (
            copy /Y %TMP_DIR%\%%p %AGENT_SETUP_PATH%\agent\etc\%%p 1>nul 2>&1
            if not exist %GSE_AGENT_ETC_DIR%\%%p (
                call :print FAIL setup_agent FAILED "setup agent , copy config file to %AGENT_SETUP_PATH%\agent\etc\ failed"
                call :multi_report_step_status
                exit /b 1
            )
        ) else (
            call :print FAIL setup_agent FAILED "%%p file download failed. please check."
            call :multi_report_step_status
            exit /b 1
        )
    )
    if not exist %GSE_AGENT_RUN_DIR% (md %GSE_AGENT_RUN_DIR%)
    if not exist %GSE_AGENT_DATA_DIR% (md %GSE_AGENT_DATA_DIR%)
    if not exist %GSE_AGENT_LOG_DIR% (md %GSE_AGENT_LOG_DIR%)
    call :register_agent_id
    if !errorlevel! NEQ 0 (
        exit /b 1
    )
    call :quit_legacy_agent
    if !errorlevel! NEQ 0 (
        exit /b 1
    )
    call :install_gse_agent_service_with_user_special
    if !errorlevel! NEQ 0 (
        exit /b 1
    )
    ping -n 1 127.0.0.1 >nul 2>&1
    call :report_gse_healthz
    if !errorlevel! NEQ 0 (
        exit /b 1
    )
    call :check_gse_healthz
    if !errorlevel! NEQ 0 (
        exit /b 1
    )
    call :print INFO setup_agent DONE "agent setup successfully"
    call :multi_report_step_status
goto :EOF

:stop_basic_gse_plugin
    call :print INFO stop_plugin - "stop gse plugin: basereport, processbeat"
    call :multi_report_step_status
    if exist %AGENT_SETUP_PATH%\plugins\bin (
        cd /d %AGENT_SETUP_PATH%\plugins\bin
        @cmd /C "stop.bat" basereport 1>nul 2>&1
        if %errorlevel% neq 0 (
            call :print FAIL stop_plugin FAILED "Process basereport.exe stop failed"
            call :multi_report_step_status
            exit /b 1
        ) else (
            call :print INFO stop_plugin - "Process basereport.exe stop success"
            call :multi_report_step_status
        )
        @cmd /C "stop.bat" processbeat 1>nul 2>&1
        if %errorlevel% neq 0 (
            call :print FAIL stop_plugin FAILED "Process processbeat.exe stop failed"
            call :multi_report_step_status
            exit /b 1
        ) else (
            call :print INFO stop_plugin - "Process processbeat.exe stop success"
            call :multi_report_step_status
        )
    ) else (
        call :print INFO stop_plugin - "gse plugin basereport,processbeat stop DONE"
        call :multi_report_step_status
    )
goto :EOF

:download_pkg
    call :print INFO download_pkg - "download gse agent package from %DOWNLOAD_URL%/agent/windows/%CPU_ARCH%/%PKG_NAME% START"
    call :multi_report_step_status
    set TEMP_PKG_NAME=%PKG_NAME:~0,-4%
    cd %TMP_DIR% && DEL /F /S /Q %PKG_NAME% %TEMP_PKG_NAME%.tar gse_agent.conf.%LAN_ETH_IP% 1>nul 2>&1
    for %%p in (%PKG_NAME%) do (
        for /F %%i in ('%TMP_DIR%\curl.exe -g --connect-timeout 5 -o %TMP_DIR%/%%p --progress-bar -sL -w "%%{http_code}" %DOWNLOAD_URL%/agent/windows/%CPU_ARCH%/%%p') do (set http_status=%%i)
    )
        if %http_status% EQU 200 (
            call :print INFO download_pkg - "gse_agent package %PKG_NAME% download succeeded, http_status:%http_status%"
            call :print INFO report_cpu_arch - "%CPU_ARCH%"
            call :multi_report_step_status
        ) else (
            call :print FAIL download_pkg FAILED "file %PKG_NAME% download failed. url:%DOWNLOAD_URL%/agent/windows/%CPU_ARCH%/%PKG_NAME%, http_status:%http_status%"
            call :multi_report_step_status
            exit /b 1
        )
goto :EOF

:check_pkgtool
    if exist %TMP_DIR%\curl.exe (
        set special_curl_PATH=%TMP_DIR:\=\\%
        call :print INFO check_env - "%TMP_DIR%\curl.exe exist"
        call :multi_report_step_status
    ) else (
        call :print FAIL check_env FAILED "%TMP_DIR%\curl.exe not found"
        call :multi_report_step_status
        exit /b 1
    )
goto :EOF

:download_exe
    call :print INFO download_exe - "Download dependent files START"
    call :multi_report_step_status
    cd /d %TMP_DIR%
    for %%p in (unixdate.exe,jq.exe,7z.dll,7z.exe,handle.exe,tcping.exe,ntrights.exe) do (
        %TMP_DIR%\curl.exe -g -o %TMP_DIR%\%%p --silent -w "%%{http_code}" %DOWNLOAD_URL%/%%p 1> %TMP_DIR%\nm.test.EEEEEEE 2>&1
        for /f %%i in (%TMP_DIR%\nm.test.EEEEEEE) do (
            if %%i equ 200 (
                call :print INFO download_exe - "dependent files %%p download success, http_status:%%i"
                call :multi_report_step_status
            ) else (
                call :print FAIL download_exe FAILED "file %%p download failed, url:%DOWNLOAD_URL%/%%p, http_status:%%i"
                call :multi_report_step_status
                exit /b 1
            )
        DEL /F /S /Q %TMP_DIR%\nm.test.EEEEEEE 1>nul 2>&1
        )
    )
    call :print INFO download_exe - "Download dependent files DONE"
    call :multi_report_step_status
goto :EOF

:check_disk_space
    for /f "tokens=1,2 delims=\" %%s in ("%AGENT_SETUP_PATH%") do (
        for /f %%i in ('wmic LogicalDisk where "Caption='%%s'" get FreeSpace ^| findstr "[0-9]"') do (
            if %%i LSS 307200 (
                call :print FAIL check_env FAILED "no enough space left on %TMP_DIR%"
                call :multi_report_step_status
                exit /b 1
            ) else (
                call :print INFO check_env - "check free disk space. done"
                call :multi_report_step_status
            )
        )
    )
goto :EOF

:check_dir_permission
    echo "" > %TMP_DIR%\nm.test.KKKKKKK
    if %errorlevel% equ 0 (
        call :print INFO check_env - "check temp dir write access: yes"
        call :multi_report_step_status
        DEL /F /S /Q %TMP_DIR%\nm.test.KKKKKKK
    ) else (
        call :print FAIL check_env FAILED "create temp files failed in %TMP_DIR%"
        call :multi_report_step_status
        exit /b 1
    )
goto :EOF

:check_download_url
    for /f "delims=" %%i in ('%TMP_DIR%\curl.exe -g --silent %DOWNLOAD_URL%/agent/windows/%CPU_ARCH%/%PKG_NAME% -Iw "%%{http_code}"') do (set http_status=%%i)
        if "%http_status%" == "200" (
            call :print INFO check_env - "check resource %DOWNLOAD_URL%/agent/windows/%CPU_ARCH%/%PKG_NAME% url succeed"
            call :multi_report_step_status
        ) else (
            call :print FAIL check_env FAILED "check resource %DOWNLOAD_URL%/agent/windows/%CPU_ARCH%/%PKG_NAME% url failed, http_status:%http_status%"
            call :multi_report_step_status
            exit /b 1
        )
    )
goto :EOF

:check_target_clean
    if exist %AGENT_SETUP_PATH% (
        call :print WARN check_env - "directory is not clean. everything will be wiped unless -u was specified"
        call :multi_report_step_status
    ) else (
        call :print INFO check_env - "directory is clean"
        call :multi_report_step_status
    )
goto :EOF

:check_env
    cd /d %TMP_DIR%
    call :download_exe
    if !errorlevel! NEQ 0 (
        exit /b 1
    )
    call :print INFO check_env START "checking prerequisite. NETWORK_POLICY,DISK_SPACE,PERMISSION,RESOURCE etc."
    call :multi_report_step_status
    if "%NODE_TYPE%" == "agent" (
        call :check_polices_agent_to_upstream
        if !errorlevel! NEQ 0 (
            exit /b 1
        )
    ) else if "%NODE_TYPE%" == "pagent" (
        call :check_polices_pagent_to_upstream
        if !errorlevel! NEQ 0 (
            exit /b 1
        )
    ) else (
        call :print FAIL check_env FAILED "NODE_TYPE exist , but it's not agent or pagent , plz check"
        call :multi_report_step_status
        exit /b 1
    )
    call :check_disk_space
    if !errorlevel! NEQ 0 (
        exit /b 1
    )
    call :check_dir_permission
    if !errorlevel! NEQ 0 (
        exit /b 1
    )
    call :check_pkgtool
    if !errorlevel! NEQ 0 (
        exit /b 1
    )
    call :check_download_url
    if !errorlevel! NEQ 0 (
        exit /b 1
    )
    call :check_target_clean
    if !errorlevel! NEQ 0 (
        exit /b 1
    )
    if !errorlevel! equ 0 (
        call :print INFO check_env DONE "checking prerequisite done, result: SUCCESS"
        call :multi_report_step_status
    ) else (
        call :print FAIL check_env FAILED "checking prerequisite done, result: FAIL"
        call :multi_report_step_status
        exit /b 1
    )
goto :EOF

:check_deploy_result
    call :is_process_start_ok
    if !errorlevel! NEQ 0 (
        exit /b 1
    )
    call :is_gsecmdline_ok
    if !errorlevel! NEQ 0 (
        exit /b 1
    )
    call :is_connected
    if !errorlevel! NEQ 0 (
        exit /b 1
    )
    for /f "tokens=1* delims=:" %%i in ('type %tmp_check_deploy_result_files% ^|findstr /n "."') do (set ret=%%i)
    echo %ret% ---------------------------------------------------------------------------------------------------------------------Final
    if %ret% GEQ 2 (
        rem DEL /F /S /Q %tmp_json_resp% %TMP_DIR%\nm.setup_agent.bat.%TASK_ID% %TMP_DIR%\nm.test.XXXXXXXX %TMP_DIR%\nm.test.ZZZZZZZ
        ping -n 3 127.0.0.1 >nul 2>&1
        call :print INFO check_deploy_result DONE "gse agent has been deployed successfully"
        call :multi_report_step_status
        rem call :last_log_process
        rem if exist %tmp_json_resp_report_log% (call :last_log_process)
    ) else (
        call :print FAIL check_deploy_result FAILED "gse agent has bean deployed unsuccessfully"
        call :multi_report_step_status
        exit /b 1
        rem call :last_log_process
        rem if exist %tmp_json_resp_report_log% (call :last_log_process)
    )
goto :EOF

:report_step_status
    if %CALLBACK_URL% == "" (
        goto :EOF
    )
    if !status! == FAILED (
        echo report_step_status %tmp_json_body_temp% >> %TMP_DIR%\status_failed.txt
        echo " ---  " >> %TMP_DIR%\status_failed.txt
    )
    for /f %%i in ('%TMP_DIR%\unixdate.exe +%%s') do (set unixtimestamp=%%i)
    set tmp_json_body_temp=%tmp_json_body_temp:}{=},{%
    set tmp_json_body_temp=%tmp_json_body_temp:rav_0_++++++++++=%
    echo "[%tmp_json_body_temp%]" >%TMP_DIR%\tmp.json
    %TMP_DIR%\jq.exe <%TMP_DIR%\tmp.json
    if !errorlevel! NEQ 0 (
        SET /A anu=%RANDOM% * 100 / 32768 + 1
        move %TMP_DIR%\tmp.json %TMP_DIR%\tmp.json.%anu%
    )
    set tmp_json_body="{\"task_id\":\"%TASK_ID%\",\"token\":\"%TOKEN%\",\"logs\":[%tmp_json_body_temp%]}"
    rem set tmp_json_body_fail="{\"task_id\":\"%TASK_ID%\",\"token\":\"%TOKEN%\",\"logs\":[{\"timestamp\":\"%unixtimestamp%\",\"level\":\"FAIL\",\"step\":\"check_deploy_result\",\"log\":\"gse agent has bean deployed unsuccessfully\",\"status\":\"FAILED\"}]}"
    echo %tmp_json_body%
    echo %tmp_json_body% >> %tmp_json_resp%
    if "%UPSTREAM_TYPE%" == "SERVER" (
        echo "check_report_log %tmp_json_body%"
        %TMP_DIR%\curl.exe -g -s -S -X POST %CALLBACK_URL%/report_log/ -d %tmp_json_body% >> %tmp_json_resp%
        echo=
        echo= >> %tmp_json_resp%
        echo= >> %tmp_json_resp%
        if %status% == FAILED ( exit /B 1 )
        goto :EOF
    ) else if "%UPSTREAM_TYPE%" == "PROXY" (
        %TMP_DIR%\curl.exe -g -s -S -X POST %CALLBACK_URL%/report_log/ -d %tmp_json_body% -x %HTTP_PROXY% >> %tmp_json_resp%
        echo=
        echo= >> %tmp_json_resp%
        echo= >> %tmp_json_resp%
        if %status% == FAILED ( exit /B 1 )
        goto :EOF
    ) else (
        call :print FAILED report_step_status DONE "UPSTREAM_TYPE exist , but it's not SERVER or PROXY , plz check"
        call :multi_report_step_status
        exit /b 1
    )
goto :EOF

:multi_report_step_status
    if %CALLBACK_URL% == "" (
        goto :EOF
    )
    rem 判断行数进行处理
    for /f "tokens=1* delims=:" %%i in ('type %tmp_json_resp_report_log% ^| findstr /n "."') do (set ret=%%i)
    echo %ret%
    if !status! == FAILED (
        for /f "tokens=*" %%i in (%tmp_json_resp_report_log%) do (set /p "var=%%i,"<nul>>%tmp_json_resp_report_log_1%)
        for /f "delims=" %%i in (!tmp_json_resp_report_log_1!) do call set var=%%var%%%%i
        set var=!var:~0,-1!
        echo !var!>!tmp_json_resp_report_log_2!.failed.txt
        for /f "tokens=2-20 delims=++++++++++" %%i in (!tmp_json_resp_report_log_2!.failed.txt) do (set tmp_json_body_temp=%%i)
        echo multi_report_step_status %tmp_json_body_temp% >> %TMP_DIR%\status_failed.txt
        DEL /F /S /Q %tmp_json_resp_report_log% %tmp_json_resp_report_log_1% %tmp_json_resp_report_log_2%
        call :report_step_status
        rem exit /b 1
        goto :EOF
    ) else if %ret% GEQ %report_line_num% (
        set var=rav_%nsttret%_++++++++++
        for /f "tokens=*" %%i in (%tmp_json_resp_report_log%) do (set /p "var=%%i,"<nul>>%tmp_json_resp_report_log_1%)
        for /f "delims=" %%i in (!tmp_json_resp_report_log_1!) do call set var=%%var%%%%i
        set var=!var:~0,-1!
        echo !var!>!tmp_json_resp_report_log_2!.%nsttret%.txt
        for /f "tokens=2-20 delims=++++++++++" %%i in (!tmp_json_resp_report_log_2!.%nsttret%.txt) do (set tmp_json_body_temp=%%i)
        DEL /F /S /Q %tmp_json_resp_report_log_1% %tmp_json_resp_report_log_2% %tmp_json_resp_report_log%
        echo %tmp_json_body% 000000000000000000000000
        call :report_step_status
        goto :EOF
    ) else (
        echo '00000-----00000 type %tmp_json_resp_report_log%'
        type %tmp_json_resp_report_log%
        goto :EOF
    )
    set /a nsttret+=1
goto :EOF

:last_log_process
    set /a nsttret+=1
    if exist %tmp_json_resp_report_log% (
        type %tmp_json_resp_report_log%
        for /f "tokens=*" %%k in (%tmp_json_resp_report_log%) do (set /p "tnk=%%k,"<nul>>%tmp_json_resp_report_log_1%)
        for /f "delims=" %%k in (!tmp_json_resp_report_log_1!) do call set tnk=%%tnk%%%%k
		set tnk=!tnk:~0,-1!
		echo !tnk!>!tmp_json_resp_report_log_2!.%nsttret%.txt
        for /f "delims=" %%i in (!tmp_json_resp_report_log_2!.%nsttret%.txt) do (set tmp_json_body_temp=%%i)
        DEL /F /S /Q %tmp_json_resp_report_log_1% %tmp_json_resp_report_log_2%)
        echo %tmp_json_body_temp% 000000000000000000000000
        call :report_step_status
goto :EOF

:remove_agent_pro
    rem delete agent all, 卸载Agent
    if "%_service_id%" == "" (
        call :print FAIL check_deploy_result FAILED "service_id -%_service_id%- get failed"
        call :multi_report_step_status
        exit /b 1
        rem call :last_log_process
        rem if exist %tmp_json_resp_report_log% (call :last_log_process)
    )
    set tmp_json_resp=%TMP_DIR%\nm.setup_agent.bat.%TASK_ID%
    if exist %tmp_json_resp% (DEL /F /S /Q %tmp_json_resp%)
    for /f %%i in ('%TMP_DIR%\unixdate.exe +%%s') do (set unixtimestamp=%%i)
    set report_line_num=3
    set tmp_json_resp=%TMP_DIR%\nm.setup_agent.bat.%TASK_ID%
    set tmp_json_resp_debug=%TMP_DIR%\nm.setup_agent.bat.%TASK_ID%.debug
    set tmp_json_resp_report_log_1=%TMP_DIR%\nm.setup_agent.bat.%TASK_ID%.report_log.1
    set tmp_json_resp_report_log_2=%TMP_DIR%\nm.setup_agent.bat.%TASK_ID%.report_log.2
    set tmp_json_resp_report_log=%TMP_DIR%\nm.setup_agent.bat.%TASK_ID%.report_log
    set tmp_check_deploy_result_files=%TMP_DIR%\nm.setup_agent.bat.check_deploy_result.temp.txt
    set GSE_AGENT_RUN_DIR=%AGENT_SETUP_PATH%\agent\run
    set GSE_AGENT_DATA_DIR=%AGENT_SETUP_PATH%\agent\data
    set GSE_AGENT_LOG_DIR=%AGENT_SETUP_PATH%\agent\logs
    set NEW_AGENT_SETUP_PATH=%AGENT_SETUP_PATH:\=/%
    set special_AGENT_SETUP_PATH=%AGENT_SETUP_PATH:\=\\%
    set PURE_AGENT_SETNUP_PATH=%AGENT_SETUP_PATH%\agent
    if exist %tmp_json_resp% (DEL /F /S /Q %tmp_json_resp%)
    if exist %tmp_json_resp_debug% (DEL /F /S /Q %tmp_json_resp_debug%)
    if exist %tmp_json_resp_report_log_1% (DEL /F /S /Q %tmp_json_resp_report_log_1%)
    if exist %tmp_json_resp_report_log_2% (DEL /F /S /Q %tmp_json_resp_report_log_2%)
    if exist %tmp_json_resp_report_log% (DEL /F /S /Q %tmp_json_resp_report_log%)
    if exist %tmp_check_deploy_result_files% (DEL /F /S /Q %tmp_check_deploy_result_files%)
    call :print INFO remove_agent START "trying to remove old agent"
    call :multi_report_step_status
    if exist %PURE_AGENT_SETNUP_PATH% (
        call :remove_startup_scripts
        if !errorlevel! NEQ 0 (
            exit /b 1
        )
        echo=
        call :remove_crontab
        if !errorlevel! NEQ 0 (
            exit /b 1
        )
        echo=
        call :unregister_agent_id SKIP
        if !errorlevel! NEQ 0 (
            exit /b 1
        )
        echo=
        call :backup_config_file_action
        if !errorlevel! NEQ 0 (
            exit /b 1
        )
        echo=
        rem gseAgent 2.0 no need to remove plugin
        rem call :stop_basic_gse_plugin
        echo=
        call :stop_agent
        if !errorlevel! NEQ 0 (
            exit /b 1
        )
        echo=
        call :uninstall_agent_service
        if !errorlevel! NEQ 0 (
            exit /b 1
        )
    )
    if exist %PURE_AGENT_SETNUP_PATH% (
        wmic process where "name='gse_agent_daemon.exe' and ExecutablePath='%special_AGENT_SETUP_PATH%\\agent\\bin\\gse_agent_daemon.exe'" call terminate 1>nul 2>&1
        wmic process where "name='gse_agent.exe' and ExecutablePath='%special_AGENT_SETUP_PATH%\\agent\\bin\\gse_agent.exe'" call terminate 1>nul 2>&1
        wmic process where "name='basereport.exe' and ExecutablePath='%special_AGENT_SETUP_PATH%\\plugins\\bin\\basereport.exe'" call terminate 1>nul 2>&1
        wmic process where "name='gsecmdline.exe' and ExecutablePath='%special_AGENT_SETUP_PATH%\\plugins\\bin\\gsecmdline.exe'" call terminate 1>nul 2>&1
    )
    RD /Q /S %PURE_AGENT_SETNUP_PATH% 1>nul 2>&1
    if not exist %PURE_AGENT_SETNUP_PATH% (
        call :print INFO remove_agent DONE "directory %PURE_AGENT_SETNUP_PATH% removed, agent removed succeed"
        call :multi_report_step_status
        rem if exist %tmp_json_resp_report_log% (call :last_log_process)
    ) else (
        for /f "skip=1 delims= " %%i in ('%TMP_DIR%\handle.exe %PURE_AGENT_SETNUP_PATH% -nobanner') do (
            echo %%i
            taskkill /f /im %%i
        )
        RD /Q /S %PURE_AGENT_SETNUP_PATH% 1>nul 2>&1
        call :print INFO remove_agent DONE "agent removed succeed"
        rem if exist %tmp_json_resp_report_log% (call :last_log_process)
        call :multi_report_step_status
    )
    call :check_uninstall_result
    if !errorlevel! NEQ 0 (
        exit /b 1
    )
goto :EOF

:check_uninstall_result

    set service=1
    sc query gse_agent_daemon_%service_id% 1>nul 2>&1
    if %errorlevel% NEQ 0 (
        set service=0
    )
    if %service% EQU 0 (
        call :print INFO remove_agent DONE "gse agent has been uninstalled successfully"
        call :multi_report_step_status
    ) else (
        call :print FAIL remove_agent FAILED "gse agent has been uninstalled failed"
        call :multi_report_step_status
        exit /b 1
    )
goto :EOF

:register_agent_id
    if NOT EXIST %gse_winagent_home%\\agent\\bin\\gse_agent.exe (
        call :print FAIL register_agent_id FAILED "gse_agent.exe not exists"
        call :multi_report_step_status
        exit /b 1
    )

    if %UNREGISTER_AGENT_ID% EQU 0 (
        call :unregister_agent_id SKIP
    )

    %gse_winagent_home%\\agent\\bin\\gse_agent.exe --agent-id -f %GSE_AGENT_ETC_DIR%\\gse_agent.conf
    if %errorlevel% EQU 0 (
        call :re_register_agent_id
    ) else (
        call :start_register_agent_id
    )
goto :EOF

:start_register_agent_id
    call :print INFO start_register_agent_id - "trying to register agent id"
    call :multi_report_step_status
    if EXIST %GSE_AGENT_ETC_DIR%\\gse_agent.conf (
        %gse_winagent_home%\\agent\\bin\\gse_agent.exe --register -f %GSE_AGENT_ETC_DIR%\\gse_agent.conf
    ) else (
        %gse_winagent_home%\\agent\\bin\\gse_agent.exe --register
    )

    for /F "tokens=*" %%i in ('%GSE_AGENT_BIN_DIR%\gse_agent.exe --agent-id -f %GSE_AGENT_ETC_DIR%\gse_agent.conf') do (set agentidinfo=%%i)

    echo %agentidinfo% | findstr /I /C:"agent-id:" >nul 2>&1 && (
        call :print INFO start_register_agent_id - "register agent id success"
        call :print INFO report_agent_id DONE "!agentidinfo!"
        call :multi_report_step_status
    ) || (
        call :print FAIL start_register_agent_id FAILED "register agent id failed"
        call :multi_report_step_status
        exit /b 1
    )
goto :EOF

:re_register_agent_id
    call :print INFO re_register_agent_id - "trying to get registered agent id"
    call :multi_report_step_status
    for /F "tokens=2" %%i in ('%GSE_AGENT_BIN_DIR%\gse_agent.exe --agent-id -f %GSE_AGENT_ETC_DIR%\gse_agent.conf') do (set agentid=%%i)
    call :print INFO re_register_agent_id - "get registered agent id: %agentid%"
    call :multi_report_step_status
    if EXIST %GSE_AGENT_ETC_DIR%\\gse_agent.conf (
        %gse_winagent_home%\\agent\\bin\\gse_agent.exe --register %agentid% -f %GSE_AGENT_ETC_DIR%\\gse_agent.conf
    ) else (
        %gse_winagent_home%\\agent\\bin\\gse_agent.exe --register %agentid%
    )

    for /F "tokens=2" %%i in ('%GSE_AGENT_BIN_DIR%\gse_agent.exe --agent-id -f %GSE_AGENT_ETC_DIR%\gse_agent.conf') do (set agentidinfo=%%i)
    
    if %agentid% == %agentidinfo% (
        call :print INFO re_register_agent_id - "re_register agent id success"
        call :print INFO report_agent_id DONE "!agentidinfo!"
        call :multi_report_step_status
    ) else (
        call :print INFO re_register_agent_id - "re_register agent id failed, try to register"
        call :multi_report_step_status
        call :unregister_agent_id SKIP
        call :start_register_agent_id
    )
goto :EOF

:report_gse_healthz
    set "healthzbase64info="
    for /F "tokens=*" %%i in ('%GSE_AGENT_BIN_DIR%\gse_agent.exe --healthz -f %GSE_AGENT_ETC_DIR%\gse_agent.conf ^| %TMP_DIR%\base64.exe') do (set "healthzbase64info=!healthzbase64info!%%i")
    call :print INFO report_healthz DONE "!healthzbase64info!"
    call :multi_report_step_status
goto :EOF

:check_gse_healthz
    set healthz_result=%TMP_DIR%\healthz.json
    for /F "tokens=*" %%i in ('%gse_winagent_home%\\agent\\bin\\gse_agent.exe --healthz -f %gse_winagent_home%\\agent\\etc\\gse_agent.conf') do (set res=%%i)
    set res=%res:healthz:=%
    echo %res% >%healthz_result%
    rem {"ok":true,"data":{"base":"ok","cluster":"ok","data":"ok","file":"ok"}}
    for /F %%i in ('%TMP_DIR%\jq.exe -r .ok ^<%healthz_result%') do (set allRESULT=%%i)
    if [%allRESULT%] == [true] (
        echo all is ok
        call :print INFO check_gse_healthz - "All is OK"
        call :multi_report_step_status
        goto :EOF
    )
    for /F "tokens=*" %%i in ('%TMP_DIR%\jq.exe -r .data.base ^<%healthz_result%') do (set base=%%i)
    if "%base%" == "ok" (
        call :print INFO check_gse_healthz - "data.base is OK"
        call :multi_report_step_status
    ) else (
        echo data.base is error: %base%
        call :print FAIL check_gse_healthz FAILED "data.base is unhealth: %base%"
        call :multi_report_step_status
        exit /b 1
    )
    for /F "tokens=*" %%i in ('%TMP_DIR%\jq.exe -r .data.cluster ^<%healthz_result%') do (set cluster=%%i)
    if "%cluster%" == "ok" (
        call :print INFO check_gse_healthz - "data.cluster is OK"
        call :multi_report_step_status
    ) else (
        call :print FAIL check_gse_healthz FAILED "data.cluster is unhealth: %cluster%"
        call :multi_report_step_status
        exit /b 1
    )
    for /F "tokens=*" %%i in ('%TMP_DIR%\jq.exe -r .data.data ^<%healthz_result%') do (set data=%%i)
    if "%data%" == "ok" (
        call :print INFO check_gse_healthz - "data.data is OK"
        call :multi_report_step_status
    ) else (
        call :print FAIL check_gse_healthz FAILED "data.data is unhealth: %data%"
        call :multi_report_step_status
        exit /b 1
    )
    for /F "tokens=*" %%i in ('%TMP_DIR%\jq.exe -r .data.file ^<%healthz_result%') do (set file=%%i)
    if "%file%" == "ok" (
        call :print INFO check_gse_healthz - "data.file is OK"
        call :multi_report_step_status
    ) else (
        call :print FAIL check_gse_healthz FAILED "data.file is unhealth: %file%"
        call :multi_report_step_status
        exit /b 1
    )
goto :EOF

:unregister_agent_id
    (set skip=%1)
    if NOT EXIST %gse_winagent_home%\\agent\\bin\\gse_agent.exe (
        if "%skip%" == "SKIP" (
            call :print WARN unregister_agent_id - "%gse_winagent_home%\\agent\\bin\\gse_agent.exe not exists"
            call :multi_report_step_status
            goto :EOF
        ) else (
            call :print FAIL unregister_agent_id FAILED "%gse_winagent_home%\\agent\\bin\\gse_agent.exe not exists"
            call :multi_report_step_status
            exit /b 1
        )
    )
    %gse_winagent_home%\\agent\\bin\\gse_agent.exe --agent-id -f %GSE_AGENT_ETC_DIR%\\gse_agent.conf
    if %errorlevel% NEQ 0 (
        call :print INFO unregister_agent_id - "have not register agent id"
        call :multi_report_step_status
        goto :EOF
    )
    call :print INFO unregister_agent_id - "trying to unregister agent id"
    if EXIST %GSE_AGENT_ETC_DIR%\\gse_agent.conf (
        %gse_winagent_home%\\agent\\bin\\gse_agent.exe --unregister -f %GSE_AGENT_ETC_DIR%\\gse_agent.conf
    ) else (
        %gse_winagent_home%\\agent\\bin\\gse_agent.exe --unregister
    )
    if %errorlevel% EQU 0 (
        call :print INFO unregister_agent_id - "unregister agent id success"
        call :multi_report_step_status
    ) else (
        if "%skip%" == "SKIP" (
            call :print WARN unregister_agent_id - "unregister agent id failed, but skip it"
            call :multi_report_step_status
        ) else (
            call :print FAIL unregister_agent_id FAILED "unregister agent id failed"
            call :multi_report_step_status
            exit /b 1
        )
    )
goto :EOF

:install_gse_agent_service_with_user_special
    if "%INSTALL_USER%" == "" (
        %gse_winagent_home%\\agent\\bin\\gse_agent_daemon.exe --install -f %gse_winagent_home%\\agent\\etc\\gse_agent.conf --name gse_agent_daemon_%service_id%
        if !errorlevel! equ 0 (
            call :print INFO setup_agent DONE "create gse_agent service without special user succeed"
            call :multi_report_step_status
        ) else (
            call :print FAIL setup_agent FAILED "create gse_agent service without special user failed"
            call :multi_report_step_status
            exit /b 1
        )
    ) else (
        %gse_winagent_home%\\agent\\bin\\gse_agent_daemon.exe --install -f %gse_winagent_home%\\agent\\etc\\gse_agent.conf --name gse_agent_daemon_%service_id% --user .\\%INSTALL_USER% --pwd %INSTALL_PASSWORD% --encode
        if !errorlevel! equ 0 (
            call :print INFO setup_agent - "create gse_agent service with special user: %INSTALL_USER%, succeed"
            call :multi_report_step_status
        ) else (
            call :print FAIL setup_agent FAILED "create gse_agent service with special user %INSTALL_USER% failed"
            call :multi_report_step_status
            exit /b 1
        )
    )
    %gse_winagent_home%\\agent\\bin\\gse_agent_daemon.exe --start --name gse_agent_daemon_%service_id%
    if %errorlevel% NEQ 0 (
        sc start gse_agent_daemon_%service_id%
    ) else (
        call :print INFO setup_agent - "start service gse_agent_daemon_%service_id% succeed"
        call :multi_report_step_status
        goto :EOF
    )
    if %errorlevel% NEQ 0 (
        for /F "tokens=*" %%i in ('sc start gse_agent_daemon_%service_id%') do (set res=%%i)
        call :print FAIL setup_agent FAILED "start service gse_agent_daemon_%service_id% failed, with error info: !res!"
        call :multi_report_step_status
        exit /b 1
    ) else (
        call :print INFO setup_agent - "start service gse_agent_daemon_%service_id% succeed"
        call :multi_report_step_status
    )
goto :EOF

:quit_legacy_agent
    rem 兼容性处理，停用并删除老版本agent
    sc stop gse_agent_daemon_%service_id% 1>nul 2>&1
    sc delete gse_agent_daemon_%service_id% 1>nul 2>&1
    sc stop gseDaemon 1>nul 2>&1
    sc delete gseDaemon 1>nul 2>&1
    cd C:
    RD /S /Q  C:\gse\gseagentw 1>nul 2>&1
goto :EOF

:add_user_right
    rem 使用 ntrights 给用户添加权限
    if not "%INSTALL_USER%" == "" (
        %TMP_DIR%\ntrights.exe -u %INSTALL_USER% +r SeServiceLogonRight
        %TMP_DIR%\ntrights.exe -u %INSTALL_USER% +r SeAssignPrimaryTokenPrivilege
        call :print INFO add_user_right - "add user Privilege success"
        call :multi_report_step_status
    )
goto :EOF

:backup_config_file_action
    if exist %GSE_AGENT_ETC_DIR%\%BACKUP_CONFIG_FILE%  (
        copy /Y  %GSE_AGENT_ETC_DIR%\%BACKUP_CONFIG_FILE% %TMP_DIR%\%BACKUP_CONFIG_FILE%
        call :print INFO backup_config_file - "backup config file %BACKUP_CONFIG_FILE% "
        call :multi_report_step_status
    ) else (
        call :print INFO backup_config_file - "backup config file not found"
        call :multi_report_step_status
    )
goto :EOF

:recovery_config_file_action
    forfiles /P %TMP_DIR% /s /d +0 |findstr /i %BACKUP_CONFIG_FILE%  1>nul 2>&1
    if %errorlevel% neq 0 (
        call :print INFO backup_config_file - "not found config file %BACKUP_CONFIG_FILE% where modefied in one day in %TMP_DIR%\"
        call :multi_report_step_status
    ) else (
        copy /Y %TMP_DIR%\%BACKUP_CONFIG_FILE% %GSE_AGENT_ETC_DIR%\%BACKUP_CONFIG_FILE%
        call :print INFO backup_config_file - "recovery config file %BACKUP_CONFIG_FILE% from %TMP_DIR%"
        call :multi_report_step_status
        DEL /F /S /Q %TMP_DIR%\%BACKUP_CONFIG_FILE%
    )
goto :EOF

:help
    echo usage: setup_agent.bat -i CLOUD_ID -l URL -i CLOUD_ID -I LAN_IP [OPTIONS]
    echo for example: setup_agent.bat -i 0 -I gse_ethernet_ip -s task_id -l DOWNLOAD_URL -p C:\gse -r CALLBACK_URL -n GSE_SERVER_IP -N SERVER -T Temp_folder
    echo  -I lan ip address on ethernet
    echo  -i CLOUD_ID
    echo  -n NAMES
    echo  -t PKG_VERSION
    echo  -l DOWNLOAD_URL
    echo  -s TASK_ID. [optional]
    echo  -c TOKEN. [optional]
    echo  -u upgrade action. [optional]
    echo  -r CALLBACK_URL, [optional]
    echo  -x HTTP_PROXY, [optional]
    echo  -p AGENT_SETUP_PATH, [optional]
    echo  -N UPSTREAM_TYPE, 'server' or 'proxy' [optional]
    echo  -v CUSTOM VARIABLES ASSIGNMENT LISTS. [optional]
    echo    valid variables:
    echo        GSE_AGENT_RUN_DIR
    echo        GSE_AGENT_DATA_DIR
    echo        GSE_AGENT_LOG_DIR
    echo -o enable override OPTION DEFINED VARIABLES by -v. [optional]
    echo -O CLUSTER_PORT
    echo -E FILE_SVR_PORT
    echo -R UNINSTALL_AGENT
    echo -F UNREGISTER_AGENT_ID [optional]
goto :EOF

:EOF
