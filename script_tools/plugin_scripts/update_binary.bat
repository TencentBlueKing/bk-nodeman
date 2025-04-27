@echo off

setlocal EnableDelayedExpansion
set cu_date=%date:~0,4%-%date:~5,2%-%date:~8,2%
set cu_time=%time:~0,8%

rem function switch
:loop
IF NOT "%1"=="" (
    IF "%1"=="-t" (
        SET SWWIN_TARGET_DIR=%2
        SHIFT
    )
    IF "%1"=="-p" (
        SET SWWIN_GSE_HOME=%2
        SHIFT
    )
    IF "%1"=="-n" (
        SET SWWIN_PLUGIN_NAME=%2
        SHIFT
    )
    IF "%1"=="-f" (
        SET SWWIN_PACKAGE=%2
        SHIFT
    )
    IF "%1"=="-z" (
        SET SWWIN_TMP=%2
        SHIFT
    )
    IF "%1"=="-m" (
        SET SWWIN_UPGRADE_TYPE=%2
        SHIFT
    )
    IF "%1"=="-i" (
        SET GROUP_DIR=%2
        SHIFT
    )
    IF "%1"=="-u" (
        SET TEMP_SUB_UNPACK_DIR=%2
        SHIFT
    )
    SHIFT
    GOTO :loop
)

set s7zPath=%SWWIN_TMP%

rem GSE folder
IF NOT EXIST %SWWIN_GSE_HOME% md %SWWIN_GSE_HOME%

rem 目标文件夹判断
if not "%SWWIN_TARGET_DIR%"=="official" if not "%SWWIN_TARGET_DIR%"=="1" if not "%SWWIN_TARGET_DIR%"=="external" if not "%SWWIN_TARGET_DIR%"=="2" if not "%SWWIN_TARGET_DIR%"=="scripts" if not "%SWWIN_TARGET_DIR%"=="3" echo error , -t must with official or 1, external or 2, scripts or 3, plz check ! & goto :EOF (
    if "%SWWIN_TARGET_DIR%"=="official" (
        set WIN_GSE_BINDIR=%SWWIN_GSE_HOME%\plugins\bin
        set WIN_GSE_ETCDIR=%SWWIN_GSE_HOME%\plugins\etc
        set WIN_GSE_BINDIR_1=%SWWIN_GSE_HOME%\plugins
        set WIN_GSE_ETCDIR_1=%SWWIN_GSE_HOME%\plugins
    ) else (
    if "%SWWIN_TARGET_DIR%"=="1" (
        set WIN_GSE_BINDIR=%SWWIN_GSE_HOME%\plugins\bin
        set WIN_GSE_ETCDIR=%SWWIN_GSE_HOME%\plugins\etc
        set WIN_GSE_BINDIR_1=%SWWIN_GSE_HOME%\plugins
        set WIN_GSE_ETCDIR_1=%SWWIN_GSE_HOME%\plugins
    )
)

if not "%SWWIN_TARGET_DIR%"=="official" if not "%SWWIN_TARGET_DIR%"=="1" if not "%SWWIN_TARGET_DIR%"=="external" if not "%SWWIN_TARGET_DIR%"=="2" if not "%SWWIN_TARGET_DIR%"=="scripts" if not "%SWWIN_TARGET_DIR%"=="3" echo error , -t must with official or 1, external or 2, scripts or 3, plz check ! & goto :EOF (
    if "%SWWIN_TARGET_DIR%"=="external" (
        set WIN_GSE_BINDIR=%SWWIN_GSE_HOME%\external_plugins\%GROUP_DIR%\%SWWIN_PLUGIN_NAME%\
        set WIN_GSE_ETCDIR=%SWWIN_GSE_HOME%\external_plugins\%GROUP_DIR%\%SWWIN_PLUGIN_NAME%\etc
    ) else (
    if "%SWWIN_TARGET_DIR%"=="2" (
        set WIN_GSE_BINDIR=%SWWIN_GSE_HOME%\external_plugins\%SWWIN_PLUGIN_NAME%\
        set WIN_GSE_ETCDIR=%SWWIN_GSE_HOME%\external_plugins\%SWWIN_PLUGIN_NAME%\etc
    )
)

if not "%SWWIN_TARGET_DIR%"=="official" if not "%SWWIN_TARGET_DIR%"=="1" if not "%SWWIN_TARGET_DIR%"=="external" if not "%SWWIN_TARGET_DIR%"=="2" if not "%SWWIN_TARGET_DIR%"=="scripts" if not "%SWWIN_TARGET_DIR%"=="3" echo error , -t must with official or 1, external or 2, scripts or 3, plz check ! & goto :EOF (
    if "%SWWIN_TARGET_DIR%"=="scripts" (
        set WIN_GSE_BINDIR=%SWWIN_GSE_HOME%\external_scripts\
        set WIN_GSE_ETCDIR=%SWWIN_GSE_HOME%\external_scripts\
    ) else (
    if "%SWWIN_TARGET_DIR%"=="3" (
        set WIN_GSE_BINDIR=%SWWIN_GSE_HOME%\external_scripts\
        set WIN_GSE_ETCDIR=%SWWIN_GSE_HOME%\external_scripts\
    )
)

rem WIN_GSE_BINDIR WIN_GSE_BINDIR目录判断
IF NOT EXIST %WIN_GSE_BINDIR% md %WIN_GSE_BINDIR%

rem 备份
:backup
    rem set filename_time=%date:~3,4%%date:~8,2%%date:~11,2%%time:~0,2%%time:~3,2%%time:~6,2%
    set WIN_backup_filename=%SWWIN_PLUGIN_NAME%-backup.zip
    %s7zPath%\7z.exe a -tzip %SWWIN_GSE_HOME%\%WIN_backup_filename% %WIN_GSE_BINDIR% %WIN_GSE_ETCDIR%
    rem move /Y %TMP%\%WIN_backup_filename% %SWWIN_GSE_HOME%\
goto:del_old_files

rem 移除插件
if %REMOVE% == 1 (
    if "%SWWIN_TARGET_DIR%"=="official" (
        del /F /Q %WIN_GSE_BINDIR%\%SWWIN_PLUGIN_NAME% %WIN_GSE_ETCDIR%\%SWWIN_PLUGIN_NAME%.conf
    ) else (
        rd /S /Q %WIN_GSE_BINDIR%
    )
    exit
)

rem 删除老文件操作
:del_old_files
if not "%SWWIN_UPGRADE_TYPE%"=="APPEND" if not "%SWWIN_TARGET_DIR%"=="official" (
    echo "removing plugin files"
    taskkill /f /im %SWWIN_PLUGIN_NAME%.exe
    rmdir /q /s %WIN_GSE_BINDIR% >>error.log 2>&1
)
if "%SWWIN_TARGET_DIR%"=="official" (
    taskkill /f /im %SWWIN_PLUGIN_NAME%.exe
)
goto:unzip_config

rem 解压配置到目标路径
:unzip_config
echo "coming into %SWWIN_GSE_HOME%"
cd %SWWIN_GSE_HOME%
echo "copy package into temp_sub_unpack_dir: %TEMP_SUB_UNPACK_DIR%"
xcopy %SWWIN_TMP%\%SWWIN_PACKAGE% %TEMP_SUB_UNPACK_DIR%\ /I /Y
%s7zPath%\7z.exe x -aoa %TEMP_SUB_UNPACK_DIR%\%SWWIN_PACKAGE% -o%SWWIN_GSE_HOME%
echo "unpack package into %SWWIN_GSE_HOME% from dir %TEMP_SUB_UNPACK_DIR%"
rd /S /Q %TEMP_SUB_UNPACK_DIR%
if exist %SWWIN_PACKAGE:~0,-4%.tar (
    set TAR_FILE_NAME=%SWWIN_PACKAGE:~0,-4%.tar
) else if exist %SWWIN_PACKAGE:~0,-4%.tgz (
    set TAR_FILE_NAME=%SWWIN_PACKAGE:~0,-4%.tgz
) else (
    set TAR_FILE_NAME="%SWWIN_PACKAGE:~0,-4%-windows-x86_64.tgz"
)
%s7zPath%\7z.exe x -aoa %SWWIN_GSE_HOME%\%TAR_FILE_NAME% -o%SWWIN_GSE_HOME%
rem 拷贝插件脚本到官方插件目录下,避免脚本老旧有bug或者不存在的情况

if "%SWWIN_TARGET_DIR%"=="external" if defined GROUP_DIR (
    rem 第三方插件指定了group_id，解压后需要将插件从标准路径移动到实例路径下
    rd /S /Q %WIN_GSE_BINDIR%
    move %SWWIN_GSE_HOME%\external_plugins\%SWWIN_PLUGIN_NAME% %WIN_GSE_BINDIR%\..\
)

:EOF
