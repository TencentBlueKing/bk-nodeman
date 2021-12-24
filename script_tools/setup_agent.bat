@echo off
rem gse agent scripts, for bk_nodeman 2.0
setlocal EnableDelayedExpansion
set cu_date=%date:~0,4%-%date:~5,2%-%date:~8,2%
set cu_time=%time:~0,8%
set timeinfo=%date% %time%
rem DEFAULT DEFINITION
set PKG_NAME=
set CLOUD_ID=

:CheckOpts
if "%1" EQU "-h" goto help
if "%1" EQU "-R" goto remove_agent_pro
if "%1" EQU "-I" (set LAN_ETH_IP=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-i" (set CLOUD_ID=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-l" (set DOWNLOAD_URL=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-s" (set TASK_ID=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-u" (set UPGRADE=TRUE)
if "%1" EQU "-c" (set TOKEN=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-r" (set CALLBACK_URL=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-x" (set HTTP_PROXY=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-p" (set AGENT_SETUP_PATH=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-e" (set BT_FILE_SERVER_IP=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-a" (set DATA_SERVER_IP=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-k" (set TASK_SERVER_IP=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-N" (set UPSTREAM_TYPE=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-T" (set TMP_DIR=%~2) && shift && shift && goto CheckOpts && md -p %TMP_DIR%
if "%1" EQU "-v" (set VARS_LIST=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-o" (set OVERIDE=TRUE)
if "%1" EQU "-O" (set IO_PORT=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-E" (set FILE_SVR_PORT=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-A" (set DATA_PORT=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-V" (set BTSVR_THRIFT_PORT=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-B" (set BT_PORT=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-S" (set BT_PORT_START=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-Z" (set BT_PORT_END=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-K" (set TRACKER_PORT=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-U" (set INSTALL_USER=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "-P" (set INSTALL_PASSWORD=%~2) && shift && shift && goto CheckOpts
if "%1" NEQ "" echo Invalid option: "%1" && goto :EOF && exit /B 1

if not defined UPSTREAM_TYPE (set UPSTREAM_TYPE=SERVER) else (set UPSTREAM_TYPE=%UPSTREAM_TYPE%)
if not defined HTTP_PROXY (set HTTP_PROXY=) else (set HTTP_PROXY=%HTTP_PROXY%)
if not defined INSTALL_USER (set INSTALL_USER=) else (set INSTALL_USER=%INSTALL_USER%)
if not defined INSTALL_PASSWORD (set INSTALL_PASSWORD=) else (set INSTALL_PASSWORD=%INSTALL_PASSWORD%)
if "%PROCESSOR_ARCHITECTURE%" == "x86" (set PKG_NAME=gse_client-windows-x86.tgz) else (set PKG_NAME=gse_client-windows-x86_64.tgz)
if "%PROCESSOR_ARCHITECTURE%" == "x86" (set CPU_ARCH=x86) else (set CPU_ARCH=x86_64)
if "%CLOUD_ID%" == "0" (set NODE_TYPE=agent) else (set NODE_TYPE=pagent)
set gse_winagent_home=%AGENT_SETUP_PATH%
set service_id=%gse_winagent_home:~3,20%
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
set NEW_AGENT_SETUP_PATH=%AGENT_SETUP_PATH:\=/%
set special_AGENT_SETUP_PATH=%AGENT_SETUP_PATH:\=\\%

if exist %tmp_json_resp% (DEL /F /S /Q %tmp_json_resp%)
if exist %tmp_json_resp_debug% (DEL /F /S /Q %tmp_json_resp_debug%)
if exist %tmp_json_resp_report_log_1% (DEL /F /S /Q %tmp_json_resp_report_log_1%)
if exist %tmp_json_resp_report_log_2% (DEL /F /S /Q %tmp_json_resp_report_log_2%)
if exist %tmp_json_resp_report_log% (DEL /F /S /Q %tmp_json_resp_report_log%)
if exist %tmp_check_deploy_result_files% (DEL /F /S /Q %tmp_check_deploy_result_files%)

set /a nsttret=0
rem for %%p in (check_env,download_pkg,remove_crontab,remove_agent_tmp,setup_agent,start_basic_gse_plugin,setup_startup_scripts,setup_crontab,check_deploy_result) do (
for %%p in (check_env,download_pkg,remove_crontab,remove_agent_tmp,setup_agent,start_basic_gse_plugin,setup_startup_scripts,check_deploy_result) do (
    call :%%p
    call :multi_report_step_status
)

if exist %tmp_json_resp_report_log% (call :last_log_process)
if !errorlevel! equ 0 (goto :EOF)

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
    %AGENT_SETUP_PATH%\plugins\bin\gsecmdline.exe -D -d 1430 -s test 1>nul 2>&1
    if !errorlevel! equ 0 (
        call :print INFO setup_agent - "gsecmdline test success"
        call :multi_report_step_status
    ) else (
        call :print WARN setup_agent - "gsecmdline test failed"
        call :multi_report_step_status
    )
goto :EOF

:is_process_start_ok
    ping -n 5 127.0.0.1 >nul 2>&1
    wmic process where name='gse_agent_daemon.exe' get processid,executablepath,name 2>&1 | findstr /i ^"%AGENT_SETUP_PATH%^" 1>nul 2>&1
    if !errorlevel! neq 0 (
        call :print FAIL setup_agent FAILED "Process gse_agent_daemon.exe start failed"
        call :multi_report_step_status
    ) else (
        call :print_check_deploy_result INFO setup_agent - "Process gse_agent_daemon.exe start success" 1>nul 2>&1
        call :print INFO setup_agent - "Process gse_agent_daemon.exe start success"
        call :multi_report_step_status
        wmic process where name='gse_agent.exe' get processid,executablepath,name 2>&1 | findstr /i ^"%AGENT_SETUP_PATH%^" 1>nul 2>&1
        if !errorlevel! neq 0 (
            call :print FAIL setup_agent FAILED "Process gse_agent.exe start failed"
            call :multi_report_step_status
        ) else (
            call :print_check_deploy_result INFO setup_agent - "Process gse_agent.exe start success" 1>nul 2>&1
            call :print INFO setup_agent - "Process gse_agent.exe start success"
            call :multi_report_step_status
        )
    )
goto :EOF

:is_process_stop_ok
    wmic process where name='gse_agent_daemon.exe' get processid,executablepath,name 2>&1 | findstr /i ^"%AGENT_SETUP_PATH%^" 1>nul 2>&1
    if !errorlevel! neq 0 (
        call :print INFO setup_agent - "Process gse_agent_daemon.exe stop success"
        call :multi_report_step_status
    ) else (
        call :print FAIL setup_agent FAILED "Process gse_agent_daemon.exe stop failed"
        call :multi_report_step_status
        wmic process where name='gse_agent.exe' get processid,executablepath,name 2>&1 | findstr /i ^"%AGENT_SETUP_PATH%^" 1>nul 2>&1
        if !errorlevel! neq 0 (
            call :print INFO setup_agent - "Process gse_agent.exe stop success"
            call :multi_report_step_status
        ) else (
            call :print FAIL setup_agent FAILED "Process gse_agent.exe stop failed"
            call :multi_report_step_status
        )
    )
goto :EOF

:is_connected
    ping -n 10 127.0.0.1 >nul 2>&1
    for %%a in (%IO_PORT%,%DATA_PORT%) do (
        ping -n 5 127.0.0.1 >nul 2>&1
        for /f %%i in ('netstat -an ^| findstr %%a ^| findstr ESTABLISHED') do (
            if !errorlevel! equ 0 (
                call :print_check_deploy_result INFO check_deploy_result - "%%a connect to gse server success" 1>nul 2>&1
                call :print INFO check_deploy_result - "%%a connect to gse server success"
                call :multi_report_step_status
            ) else (
                call :print FAIL check_deploy_result FAILED "%%a is not connect to gse server , failed"
                call :multi_report_step_status
            )
        )
    )
goto :EOF

:check_polices_pagent_to_upstream
    rem pagent_to_proxy_port_policies=(gse_task:48668 gse_data:58625 gse_btsvr:58925 gse_btsvr:10020-10030)
    rem pagent_listen_ports=(gse_agent:60020-60030)
    call :print INFO check_env - "check if it is reachable to port %IO_PORT% of %ip% GSE PROXY"
    echo=
    for %%p in (%TASK_SERVER_IP%) do (
        rem goto is_target_reachable
        for /f %%i in ('%TMP_DIR%\tcping.exe %%p %IO_PORT% ^| findstr successful') do (
            rem echo %%i
            for /f "tokens=1,2 delims=successful" %%s in ("%%i") do (
            rem echo %%s
                if %%s GEQ 2 (
                    call :print INFO check_env - "%%p %%a is reachable"
                    call :multi_report_step_status
                ) else (
                    call :print FAIL check_env FAILED "connect to upstream server: %%p %%a failed"
                    call :multi_report_step_status
                )
            )
        )
    )

    call :print INFO check_env - "check if it is reachable to port %DATA_PORT% of %ip% GSE PROXY"
    echo=
    for %%p in (%DATA_SERVER_IP%) do (
        rem goto is_target_reachable
        for /f %%i in ('%TMP_DIR%\tcping.exe %%p %DATA_PORT% ^| findstr successful') do (
            rem echo %%i
            for /f "tokens=1,2 delims=successful" %%s in ("%%i") do (
            rem echo %%s
                if %%s GEQ 2 (
                    call :print INFO check_env - "%%p %%a is reachable"
                    call :multi_report_step_status
                ) else (
                    call :print FAIL check_env FAILED "connect to upstream server: %%p %%a failed"
                    call :multi_report_step_status
                )
            )
        )

    )

    call :print INFO check_env - "check if it is reachable to port %FILE_SVR_PORT%,%BT_PORT%-%TRACKER_PORT% of %ip% GSE PROXY"
    echo=
    for %%p in (%BT_FILE_SERVER_IP%) do (
        for %%a in (%FILE_SVR_PORT%,%BT_PORT%) do (
            rem goto is_target_reachable
            for /f %%i in ('%TMP_DIR%\tcping.exe %%p %%a ^| findstr successful') do (
                rem echo %%i
                for /f "tokens=1,2 delims=successful" %%s in ("%%i") do (
                rem echo %%s
                    if %%s GEQ 2 (
                        call :print INFO check_env - "%%p %%a is reachable"
                        call :multi_report_step_status
                    ) else (
                        call :print FAIL check_env FAILED "connect to upstream server: %%p %%a failed"
                        call :multi_report_step_status
                    )
                )
            )
        )
    )
goto :EOF

:check_polices_agent_to_upstream
    rem agent_to_server_port_policies=(zookeeper:2181 gse_task:48668 gse_data:58625 gse_btsvr:58925 gse_btsvr:10020-10030)
    rem agent_listen_ports=(gse_agent:60020-60030)
    rem agent-GSE Server
    rem set NEW_UPSTREAM_IP=%UPSTREAM_IP:~2,-1%
    call :print INFO check_env - "check if it is reachable to port %IO_PORT% of %UPSTREAM_IP% GSE_TASK_SERVER"
    echo=
    call :multi_report_step_status
    for %%p in (%TASK_SERVER_IP%) do (
        rem for %%a in (48668,58625,58925,10020) do (
        for /f %%i in ('%TMP_DIR%\tcping.exe %%p %IO_PORT% ^| findstr successful') do (
            rem echo %%i
            for /f "tokens=1,2 delims=successful" %%s in ("%%i") do (
            rem echo %%s
                if %%s GEQ 2 (
                    call :print INFO check_env - "gse server %%p %%a is reachable"
                    call :multi_report_step_status
                ) else (
                    call :print FAIL check_env FAILED "gse server %%p %%a can not reachable"
                    call :multi_report_step_status
                )
            )
        )

    )

    call :print INFO check_env - "check if it is reachable to port %DATA_PORT% of %UPSTREAM_IP% GSE_DATA_SERVER"
    echo=
    call :multi_report_step_status
    for %%p in (%DATA_SERVER_IP%) do (
        rem for %%a in (48668,58625,58925,10020) do (
        for /f %%i in ('%TMP_DIR%\tcping.exe %%p %DATA_PORT% ^| findstr successful') do (
            rem echo %%i
            for /f "tokens=1,2 delims=successful" %%s in ("%%i") do (
            rem echo %%s
                if %%s GEQ 2 (
                    call :print INFO check_env - "gse server %%p %%a is reachable"
                    call :multi_report_step_status
                ) else (
                    call :print FAIL check_env FAILED "gse server %%p %%a can not reachable"
                    call :multi_report_step_status
                )
            )
        )
    )

    call :print INFO check_env - "check if it is reachable to port %FILE_SVR_PORT%,%BT_PORT%-%TRACKER_PORT% of %UPSTREAM_IP% GSE_BTFILE_SERVER"
    echo=
    call :multi_report_step_status
    for %%p in (%BT_FILE_SERVER_IP%) do (
        rem for %%a in (48668,58625,58925,10020) do (
        for %%a in (%FILE_SVR_PORT%,%BT_PORT%) do (
            for /f %%i in ('%TMP_DIR%\tcping.exe %%p %%a ^| findstr successful') do (
                rem echo %%i
                for /f "tokens=1,2 delims=successful" %%s in ("%%i") do (
                rem echo %%s
                    if %%s GEQ 2 (
                        call :print INFO check_env - "gse server %%p %%a is reachable"
                        call :multi_report_step_status
                    ) else (
                        call :print FAIL check_env FAILED "gse server %%p %%a can not reachable"
                        call :multi_report_step_status
                    )
                )
            )
        )
    )
goto :EOF

:setup_crontab
    echo Set shell = CreateObject("Wscript.Shell") > %AGENT_SETUP_PATH%\agent\bin\gsectl.vbs 1>nul 2>&1
    echo shell.run "cmd /c cd /d %AGENT_SETUP_PATH%\agent\bin\ && gsectl.bat start",0 >> %AGENT_SETUP_PATH%\agent\bin\gsectl.vbs 1>nul 2>&1
    schtasks /create /tn gse_agent /tr "cscript %AGENT_SETUP_PATH%\agent\bin\gsectl.vbs" /sc minute /mo 1 /F 1>nul 2>&1
    ping -n 7 127.0.0.1 >nul 2>&1
    schtasks /Query | findstr gse_agent 1>nul 2>&1
    if %errorlevel% equ 0 (
        call :print INFO setup_crontab - "gse_agent schtasks setup success"
    ) else (
        call :print FAIL setup_crontab FAILED "gse_agent schtasks setup failed"
    )
goto :EOF

:remove_crontab
    schtasks /Query | findstr gse_agent 1>nul 2>&1
    if %errorlevel% neq 0 (
        call :print WARN remove_agent - "gse_agent schtasks not exist , no need remove schtasks"
        call :multi_report_step_status
    ) else (
        schtasks /Delete /tn gse_agent /F 1>nul 2>&1
        schtasks /Query | findstr gse_agent 1>nul 2>&1
        if %errorlevel% neq 0 (
            call :print INFO remove_agent - "gse_agent schtasks remove success"
        )
    )
goto :EOF

:setup_startup_scripts
    reg add "HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run" /v gse_agent /t reg_sz /d "%AGENT_SETUP_PATH%\agent\bin\gsectl.bat start" /f 1>nul 2>&1
    for /f "tokens=1,2,*" %%i in ('REG QUERY HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run /v gse_agent ^| findstr /i "gse_agent"') do (
        if "%%i" == "gse_agent" (
            call :print INFO setup_startup_scripts - "set startup with os success"
        ) else (
            call :print FAIL setup_startup_scripts FAILED "set startup with os failed"
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
        call :print FAIL remove_agent FAILED "remove startup with os failed"
        call :multi_report_step_status
    )
goto :EOF

:stop_agent
    if exist %AGENT_SETUP_PATH% (
        cd /d %AGENT_SETUP_PATH%\agent\bin && .\gsectl stop 1>nul 2>&1
        ping -n 3 127.0.0.1 1>nul 2>&1
        wmic process where "name='gse_agent_daemon.exe' and ExecutablePath='%special_AGENT_SETUP_PATH%\\agent\\bin\\gse_agent_daemon.exe'" call terminate 1>nul 2>&1
        wmic process where "name='gse_agent.exe' and ExecutablePath='%special_AGENT_SETUP_PATH%\\agent\\bin\\gse_agent.exe'" call terminate 1>nul 2>&1
        cd /d %TMP_DIR%
        call :is_process_stop_ok
    ) else (
        call :print FAIL stop_agent FAILED "%AGENT_SETUP_PATH% not exist , ERROR"
        call :multi_report_step_status
    )
goto :EOF

:remove_agent_tmp
    call :print INFO remove_agent START "trying to remove old agent"
    call :multi_report_step_status
    if exist %AGENT_SETUP_PATH% (
        call :remove_startup_scripts
        echo=
        call :remove_crontab
        echo=
        call :stop_basic_gse_plugin
        call :stop_agent
    )

    if exist %AGENT_SETUP_PATH% (
        wmic process where "name='gse_agent_daemon.exe' and ExecutablePath='%special_AGENT_SETUP_PATH%\\agent\\bin\\gse_agent_daemon.exe'" call terminate 1>nul 2>&1
        wmic process where "name='gse_agent.exe' and ExecutablePath='%special_AGENT_SETUP_PATH%\\agent\\bin\\gse_agent.exe'" call terminate 1>nul 2>&1
        wmic process where "name='basereport.exe' and ExecutablePath='%special_AGENT_SETUP_PATH%\\plugins\\bin\\basereport.exe'" call terminate 1>nul 2>&1
        wmic process where "name='gsecmdline.exe' and ExecutablePath='%special_AGENT_SETUP_PATH%\\plugins\\bin\\gsecmdline.exe'" call terminate 1>nul 2>&1
    )
    RD /Q /S %AGENT_SETUP_PATH% 1>nul 2>&1
    if not exist %AGENT_SETUP_PATH% (
        call :print INFO setup_agent DONE "agent removed succeed"
    ) else (
        for /f "skip=1 delims= " %%i in ('%TMP_DIR%\handle.exe %AGENT_SETUP_PATH% -nobanner') do (
            echo %%i
            taskkill /f /im %%i
        )
        RD /Q /S %AGENT_SETUP_PATH% 1>nul 2>&1
        ping -n 3 127.0.0.1 >nul 2>&1
        if not exist %AGENT_SETUP_PATH% (
            call :print INFO setup_agent DONE "agent removed succeed"
        ) else (
            call :print FAIL setup_agent DONE "agent removed failed"
        )
    )
goto :EOF

:get_config
    call :print INFO get_config - "request %NODE_TYPE% config files"
    call :multi_report_step_status
    set PARAM="{\"bk_cloud_id\":%CLOUD_ID%, \"filename\":\"%%p\", \"node_type\":\"%NODE_TYPE%\", \"inner_ip\":\"%LAN_ETH_IP%\", \"token\":\"%TOKEN%\"}"
    for %%p in (agent.conf) do (
        if "%HTTP_PROXY%" == "" (
            %TMP_DIR%\curl.exe -o %TMP_DIR%\%%p --silent -w "%%{http_code}" -X POST %CALLBACK_URL%/get_gse_config/ -d %PARAM%  1>%TMP_DIR%\nm.test.HHHHHHH 2>&1
        ) else (
            %TMP_DIR%\curl.exe -o %TMP_DIR%\%%p --silent -w "%%{http_code}" -X POST %CALLBACK_URL%/get_gse_config/ -d %PARAM% -x %HTTP_PROXY% 1>%TMP_DIR%\nm.test.HHHHHHH 2>&1
        )

        for /f %%i in (%TMP_DIR%\nm.test.HHHHHHH) do (
            if %%i equ 200 (
                call :print INFO get_config - "request config %%p success. request info:%CLOUD_ID%,%LAN_ETH_IP%,%node_type%,%%p,%TOKEN%. http status:%%i"
                call :multi_report_step_status
            ) else (
                call :print FAIL get_config FAILED "request config %%p failed. request info:%CLOUD_ID%,%LAN_ETH_IP%,%node_type%,%%p,%TOKEN%. http status:%%i"
                call :multi_report_step_status
            )
        )
    DEL /F /S /Q %TMP_DIR%\nm.test.HHHHHHH 1>nul 2>&1
    )
goto :EOF

:setup_agent
    call :print INFO setup_agent START "setup agent , extract, render config"
    call :multi_report_step_status

    if not exist %AGENT_SETUP_PATH% (md %AGENT_SETUP_PATH%)
    set TEMP_PKG_NAME=%PKG_NAME:~0,-4%
    %TMP_DIR%\7z.exe x %TMP_DIR%\%PKG_NAME% -o%TMP_DIR% -y 1>nul 2>&1
    %TMP_DIR%\7z.exe x %TMP_DIR%\%TEMP_PKG_NAME%.tar -o%AGENT_SETUP_PATH% -y 1>nul 2>&1

    if exist %AGENT_SETUP_PATH%\plugins\bin\gsecmdline.exe (copy /Y %AGENT_SETUP_PATH%\plugins\bin\gsecmdline.exe C:\Windows\System32\ 1>nul 2>&1)
    call :get_config
    for %%p in (agent.conf) do (
        if exist %TMP_DIR%\%%p (
            copy /Y %TMP_DIR%\%%p %AGENT_SETUP_PATH%\agent\etc\%%p 1>nul 2>&1
        ) else (
            call :print FAIL setup_agent FAILED "agent config %%p file lost. please check."
            call :multi_report_step_status
        )
    )

    if not exist %GSE_AGENT_RUN_DIR% (md %GSE_AGENT_RUN_DIR%)
    if not exist %GSE_AGENT_DATA_DIR% (md %GSE_AGENT_DATA_DIR%)
    if not exist %GSE_AGENT_LOG_DIR% (md %GSE_AGENT_LOG_DIR%)

    call :quit_legacy_agent
    call :install_gse_agent_service_with_user_special
    ping -n 3 127.0.0.1 >nul 2>&1

    call :print INFO setup_agent DONE "agent setup successfully"
goto :EOF

:start_basic_gse_plugin
    call :print INFO start_plugin - "start gse plugin: basereport, processbeat"
    call :multi_report_step_status

    cd /d %AGENT_SETUP_PATH%\plugins\bin
    @cmd /C "start.bat" basereport 1>nul 2>&1
    ping -n 3 127.0.0.1 >nul 2>&1

    if %errorlevel% neq 0 (
        call :print FAIL start_plugin FAILED "Process basereport.exe start failed"
        call :multi_report_step_status
    ) else (
        call :print INFO start_plugin - "Process basereport.exe start success"
        call :multi_report_step_status
    )

    @cmd /C "start.bat" processbeat 1>nul 2>&1
    ping -n 3 127.0.0.1 >nul 2>&1

    if %errorlevel% neq 0 (
        call :print FAIL start_plugin FAILED "Process processbeat.exe start failed"
        call :multi_report_step_status
    ) else (
        call :print INFO start_plugin - "Process processbeat.exe start success"
        call :multi_report_step_status
    )

    call :print INFO start_plugin - "gse plugin basereport,processbeat start DONE"
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
        ) else (
            call :print INFO stop_plugin - "Process basereport.exe stop success"
            call :multi_report_step_status
        )

        @cmd /C "stop.bat" processbeat 1>nul 2>&1

        if %errorlevel% neq 0 (
            call :print FAIL stop_plugin FAILED "Process processbeat.exe stop failed"
            call :multi_report_step_status
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
    call :print INFO download_pkg - "download gse agent package from %DOWNLOAD_URL%/%PKG_NAME% START"
    call :multi_report_step_status

    cd %TMP_DIR% && DEL /F /S /Q %PKG_NAME% agent.conf.%LAN_ETH_IP% 1>nul 2>&1

    for %%p in (%PKG_NAME%) do (
        for /F %%i in ('curl --connect-timeout 5 -o %TMP_DIR%/%%p --progress-bar -w "%%{http_code}" %DOWNLOAD_URL%/%%p') do (set http_status=%%i)
        if "%http_status%" == "200" (
            call :print INFO download_pkg - "gse_agent package %%p download succeeded"
            call :print INFO report_cpu_arch DONE "%CPU_ARCH%"
        ) else (
            call :print FAIL download_pkg FAILED "file %%p download failed. url:%DOWNLOAD_URL%/%%p, http_status:%http_status%"
        )
    )
goto :EOF

:check_pkgtool
    if exist %TMP_DIR%\curl.exe (
        set special_curl_PATH=%TMP_DIR:\=\\%
        call :print INFO check_env - "%TMP_DIR%\curl.exe exist"
    ) else (
        call :print FAIL check_env FAILED "%TMP_DIR%\curl.exe not found"
        goto :EOF
    )
goto :EOF

:download_exe
    call :print INFO download_exe - "Download dependent files START"
    call :multi_report_step_status

    cd /d %TMP_DIR%

    for %%p in (7z.dll,7z.exe,handle.exe,tcping.exe,unixdate.exe) do (
        %TMP_DIR%\curl.exe -o %TMP_DIR%\%%p --silent -w "%%{http_code}" %DOWNLOAD_URL%/%%p 1> %TMP_DIR%\nm.test.EEEEEEE 2>&1
        for /f %%i in (%TMP_DIR%\nm.test.EEEEEEE) do (
            if %%i equ 200 (
                call :print INFO download_exe - "dependent files %%p download success, http_status:%%i"
                call :multi_report_step_status
            ) else (
                call :print FAIL download_exe FAILED "file %%p download failed, url:%DOWNLOAD_URL%/%%p, http_status:%%i"
                call :multi_report_step_status
            )
        DEL /F /S /Q %TMP_DIR%\nm.test.EEEEEEE 1>nul 2>&1
        )
    )

    call :print INFO download_exe - "Download dependent files DONE"
goto :EOF

:check_disk_space
    for /f "tokens=1,2 delims=\" %%s in ("%AGENT_SETUP_PATH%") do (
        for /f %%i in ('wmic LogicalDisk where "Caption='%%s'" get FreeSpace ^| findstr "[0-9]"') do (
        if %%i LSS 307200 (
            call :print FAIL check_env FAILED "no enough space left on %TMP_DIR%"
        ) else (
            call :print INFO check_env - "check free disk space. done"
        )
        )
    )
goto :EOF

:check_dir_permission
    echo "" > %TMP_DIR%\nm.test.KKKKKKK

    if !errorlevel! equ 0 (
        call :print INFO check_env - "check temp dir write access: yes"
        DEL /F /S /Q %TMP_DIR%\nm.test.KKKKKKK
    ) else (
        call :print FAIL check_env FAILED "create temp files failed in %TMP_DIR%"
        goto :EOF
    )
goto :EOF

:check_download_url
    for /f "delims=" %%i in ('%TMP_DIR%\curl.exe --silent %DOWNLOAD_URL%/%PKG_NAME% -Iw "%%{http_code}"') do (set http_status=%%i)
        if "%http_status%" == "200" (
            call :print INFO check_env - "check resource %DOWNLOAD_URL%/%PKG_NAME% url succeed"
        ) else (
            call :print FAIL check_env FAILED "check resource %DOWNLOAD_URL%/%PKG_NAME% url failed, http_status:%http_status%"
            goto :EOF
        )
    )
goto :EOF

:check_target_clean
    if exist %AGENT_SETUP_PATH% (
        call :print WARN check_env - "directory is not clean. everything will be wiped unless -u was specified"
    ) else (
        call :print INFO check_env - "directory is clean"
    )
goto :EOF

:check_env
    cd /d %TMP_DIR%

    call :print INFO check_env - "Args are: -s %TASK_ID% -r %CALLBACK_URL% -l %DOWNLOAD_URL% -c %NEW_TOKEN% -n %UPSTREAM_IP% -i %CLOUD_ID% -I %LAN_ETH_IP% -N %UPSTREAM_TYPE% -p %AGENT_SETUP_PATH% -T %TMP_DIR%  %AGENT_SETUP_PATH% "
    call :multi_report_step_status

    call :download_exe
    call :multi_report_step_status

    call :print INFO check_env START "checking prerequisite. NETWORK_POLICY,DISK_SPACE,PERMISSION,RESOURCE etc."
    call :multi_report_step_status

    if "%NODE_TYPE%" == "agent" (
        call :check_polices_agent_to_upstream
        call :multi_report_step_status
    ) else if "%NODE_TYPE%" == "pagent" (
        call :check_polices_pagent_to_upstream
        call :multi_report_step_status
    ) else (
        call :print FAIL check_env FAILED "NODE_TYPE exist , but it's not agent or pagent , plz check"
        goto :EOF
    )

    call :check_disk_space
    call :multi_report_step_status

    call :check_dir_permission
    call :multi_report_step_status

    call :check_pkgtool
    call :multi_report_step_status

    call :check_download_url
    call :multi_report_step_status

    call :check_target_clean
    call :multi_report_step_status

    if %errorlevel% equ 0 (
        call :print INFO check_env DONE "checking prerequisite done, result: SUCCESS"
    ) else (
        call :print FAIL check_env DONE "checking prerequisite done, result: SUCCESS"
    )
goto :EOF

:check_deploy_result
    call :is_process_start_ok
    call :is_gsecmdline_ok
    call :is_connected

    for /f "tokens=1* delims=:" %%i in ('type %tmp_check_deploy_result_files% ^|findstr /n "."') do (set ret=%%i)
    echo %ret% ---------------------------------------------------------------------------------------------------------------------Final
    if %ret% GEQ 2 (
        rem DEL /F /S /Q %tmp_json_resp% %TMP_DIR%\nm.setup_agent.bat.%TASK_ID% %TMP_DIR%\nm.test.XXXXXXXX %TMP_DIR%\nm.test.ZZZZZZZ
        call :print INFO check_deploy_result DONE "gse agent has been deployed successfully"
        rem call :multi_report_step_status
        call :last_log_process
        if exist %tmp_json_resp_report_log% (call :last_log_process)
    ) else (
        call :print FAIL check_deploy_result FAILED "gse agent has bean deployed unsuccessfully"
        rem call :multi_report_step_status
        call :last_log_process
        if exist %tmp_json_resp_report_log% (call :last_log_process)
    )
goto :EOF

:report_step_status
    if %CALLBACK_URL% == "" (
        goto :EOF
    )

    for /f %%i in ('%TMP_DIR%\unixdate.exe +%%s') do (set unixtimestamp=%%i)
    set tmp_json_body="{\"task_id\":\"%TASK_ID%\",\"token\":\"%TOKEN%\",\"logs\":[%tmp_json_body_temp%]}"

    rem set tmp_json_body_fail="{\"task_id\":\"%TASK_ID%\",\"token\":\"%TOKEN%\",\"logs\":[{\"timestamp\":\"%unixtimestamp%\",\"level\":\"FAIL\",\"step\":\"check_deploy_result\",\"log\":\"gse agent has bean deployed unsuccessfully\",\"status\":\"FAILED\"}]}"

    echo %tmp_json_body%
    echo %tmp_json_body% >> %tmp_json_resp%

    if "%UPSTREAM_TYPE%" == "SERVER" (
        %TMP_DIR%\curl.exe -s -S -X POST %CALLBACK_URL%/report_log/ -d %tmp_json_body% >> %tmp_json_resp%
        echo=
        echo= >> %tmp_json_resp%
        echo= >> %tmp_json_resp%
        if %status% == FAILED ( exit /B 1 )
        goto :EOF
    ) else if "%UPSTREAM_TYPE%" == "PROXY" (
        %TMP_DIR%\curl.exe -s -S -X POST %CALLBACK_URL%/report_log/ -d %tmp_json_body% -x %HTTP_PROXY% >> %tmp_json_resp%
        echo=
        echo= >> %tmp_json_resp%
        echo= >> %tmp_json_resp%
        if %status% == FAILED ( exit /B 1 )
        goto :EOF
    ) else (
        call :print FAIL report_step_status FAILED "UPSTREAM_TYPE exist , but it's not SERVER or PROXY , plz check"
        goto :EOF
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
        for /f %%i in (!tmp_json_resp_report_log_2!.failed.txt) do (set tmp_json_body_temp=%%i)
		DEL /F /S /Q %tmp_json_resp_report_log% %tmp_json_resp_report_log_1% %tmp_json_resp_report_log_2%
        call :report_step_status
        exit /b 1
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
    if exist %tmp_json_resp% (DEL /F /S /Q %tmp_json_resp%)
    if exist %tmp_json_resp_debug% (DEL /F /S /Q %tmp_json_resp_debug%)
    if exist %tmp_json_resp_report_log_1% (DEL /F /S /Q %tmp_json_resp_report_log_1%)
    if exist %tmp_json_resp_report_log_2% (DEL /F /S /Q %tmp_json_resp_report_log_2%)
    if exist %tmp_json_resp_report_log% (DEL /F /S /Q %tmp_json_resp_report_log%)
    if exist %tmp_check_deploy_result_files% (DEL /F /S /Q %tmp_check_deploy_result_files%)

    call :print INFO remove_agent START "trying to remove old agent"
    call :multi_report_step_status

    if exist %AGENT_SETUP_PATH% (
        call :remove_startup_scripts
        echo=
        call :remove_crontab
        echo=
        call :stop_basic_gse_plugin
        echo=
        call :stop_agent
        echo=
    )

    if exist %AGENT_SETUP_PATH% (
        wmic process where "name='gse_agent_daemon.exe' and ExecutablePath='%special_AGENT_SETUP_PATH%\\agent\\bin\\gse_agent_daemon.exe'" call terminate 1>nul 2>&1
        wmic process where "name='gse_agent.exe' and ExecutablePath='%special_AGENT_SETUP_PATH%\\agent\\bin\\gse_agent.exe'" call terminate 1>nul 2>&1
        wmic process where "name='basereport.exe' and ExecutablePath='%special_AGENT_SETUP_PATH%\\plugins\\bin\\basereport.exe'" call terminate 1>nul 2>&1
        wmic process where "name='gsecmdline.exe' and ExecutablePath='%special_AGENT_SETUP_PATH%\\plugins\\bin\\gsecmdline.exe'" call terminate 1>nul 2>&1
    )
    RD /Q /S %AGENT_SETUP_PATH% 1>nul 2>&1

    if not exist %AGENT_SETUP_PATH% (
        call :print INFO remove_agent DONE "agent removed succeed"
        call :multi_report_step_status
        if exist %tmp_json_resp_report_log% (call :last_log_process)
    ) else (
        for /f "skip=1 delims= " %%i in ('%TMP_DIR%\handle.exe %AGENT_SETUP_PATH% -nobanner') do (
            echo %%i
            taskkill /f /im %%i
        )

        RD /Q /S %AGENT_SETUP_PATH% 1>nul 2>&1
        ping -n 3 127.0.0.1 >nul 2>&1
        if not exist %AGENT_SETUP_PATH% (
            call :print INFO remove_agent DONE "agent removed succeed"
            if exist %tmp_json_resp_report_log% (call :last_log_process)
            if %errorlevel% equ 0 (goto :EOF)
        ) else (
            call :print FAIL remove_agent DONE "agent removed failed"
            if exist %tmp_json_resp_report_log% (call :last_log_process)
            if %errorlevel% equ 1 (goto :EOF)
        )
    )
goto :EOF

:install_gse_agent_service_with_user_special
    if "%INSTALL_USER%" == "" (
        %gse_winagent_home%\\agent\\bin\\gse_agent_daemon.exe -f %gse_winagent_home%\\agent\\etc\\agent.conf --name gse_agent_daemon_%service_id%
        if %errorlevel% equ 0 (
            call :print INFO setup_agent DONE "create gse_agent service without special user succeed"
        ) else (
            call :print FAIL setup_agent DONE "create gse_agent service without special user failed"
        )
    ) else (
        %gse_winagent_home%\\agent\\bin\\gse_agent_daemon.exe -f %gse_winagent_home%\\agent\\etc\\agent.conf --name gse_agent_daemon_%service_id% --user .\\%INSTALL_USER% --pwd %INSTALL_PASSWORD% --encode
        if %errorlevel% equ 0 (
            call :print INFO setup_agent DONE "create gse_agent service with special user: %INSTALL_USER%, pwd: %INSTALL_PASSWORD% succeed"
        ) else (
            call :print FAIL setup_agent DONE "create gse_agent service with special user %INSTALL_USER% failed"
        )
    )
    %gse_winagent_home%\\agent\\bin\\gse_agent_daemon.exe --start --name gse_agent_daemon_%service_id%
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

:help
    echo usage: setup_agent.bat -i CLOUD_ID -l URL -i CLOUD_ID -I LAN_IP [OPTIONS]
    echo for example: setup_agent.bat -i 0 -I gse_ethernet_ip -s task_id -l DOWNLOAD_URL -p C:\gse -r CALLBACK_URL -n GSE_SERVER_IP -N SERVER -T Temp_folder

    echo  -I lan ip address on ethernet
    echo  -i CLOUD_ID
    echo  -l DOWNLOAD_URL
    echo  -s TASK_ID. [optional]
    echo  -c TOKEN. [optional]
    echo  -u upgrade action. [optional]
    echo  -r CALLBACK_URL, [optional]
    echo  -x HTTP_PROXY, [optional]
    echo  -p AGENT_SETUP_PATH, [optional]
    echo  -n UPSTREAM_IP, [optional]
    echo  -N UPSTREAM_TYPE, 'server' or 'proxy' [optional]
    echo  -v CUSTOM VARIABLES ASSIGNMENT LISTS. [optional]
    echo    valid variables:
    echo        GSE_AGENT_RUN_DIR
    echo        GSE_AGENT_DATA_DIR
    echo        GSE_AGENT_LOG_DIR
    echo -o enable override OPTION DEFINED VARIABLES by -v. [optional]
    echo -O IO_PORT
    echo -E FILE_SVR_PORT
goto :EOF

:EOF