@echo off
setlocal enabledelayedexpansion

rem function switch
:loop
	IF NOT "%1"=="" (
		IF "%1"=="-t" (
			SET CATEGORY=%2
			SHIFT
		)
		IF "%1"=="-p" (
			SET INSTALL_PATH=%2
			SHIFT
		)
		IF "%1"=="-n" (
			SET PLUGIN_NAME=%2
			SHIFT
		)
		IF "%1"=="-c" (
			SET RUN_CMD=%2
			SHIFT
		)
		IF "%1"=="-g" (
			SET GROUP_ID=%2
			SHIFT
		)
		SHIFT
		GOTO :loop
	)
	if "!CATEGORY!"=="" goto :usage
	if "!PLUGIN_NAME!"=="" goto :usage
	if "!INSTALL_PATH!"=="" goto :usage
	if "!RUN_CMD!"=="" goto :usage
	if "!GROUP_ID!"=="" goto :usage
	goto :guess_target_dir

:guess_target_dir
	if not "!CATEGORY!"=="official" if not "!CATEGORY!"=="1" if not "!CATEGORY!"=="external" if not "!CATEGORY!"=="2" if not "!CATEGORY!"=="scripts" if not "!CATEGORY!"=="3" echo error , -t must with official or 1, external or 2, scripts or 3, plz check ! & goto :EOF (
		if "%CATEGORY%"=="official" (
			set BINDIR=!INSTALL_PATH!\plugins\bin &goto :main
		) else (
		if "%CATEGORY%"=="1" (
			set BINDIR=!INSTALL_PATH!\plugins\bin &goto :main
		)
	)

	if not "!CATEGORY!"=="official" if not "!CATEGORY!"=="1" if not "!CATEGORY!"=="external" if not "!CATEGORY!"=="2" if not "!CATEGORY!"=="scripts" if not "!CATEGORY!"=="3" echo error , -t must with official or 1, external or 2, scripts or 3, plz check ! & goto :EOF (
		if "!CATEGORY!"=="external" (
			set BINDIR=!INSTALL_PATH!\external_plugins\!GROUP_ID!\!PLUGIN_NAME!\ &goto :main
		) else (
		if "!CATEGORY!"=="2" (
			set BINDIR=!INSTALL_PATH!\external_plugins\!GROUP_ID!\!PLUGIN_NAME!\ &goto :main
		)
	)

	if not "!CATEGORY!"=="official" if not "!CATEGORY!"=="1" if not "!CATEGORY!"=="external" if not "!CATEGORY!"=="2" if not "!CATEGORY!"=="scripts" if not "!CATEGORY!"=="3" echo error , -t must with official or 1, external or 2, scripts or 3, plz check ! & goto :EOF (
		if "%CATEGORY%"=="scripts" (
			set BINDIR=!INSTALL_PATH!\external_scripts\ &goto :main
		) else (
		if "%CATEGORY%"=="3" (
			set BINDIR=!INSTALL_PATH!\external_scripts\ &goto :main
		)
	)
	
:usage
	echo "usage: operate_plugin OPTIONS"
	echo "OPTIONS"
	echo "  -t  plugin category, could be: official/external/scripts"
	echo "  -n  plugin name"
	echo "  -p  home path of plugin"
	echo "  -c  command to run"
	echo "  -g  group id"
	exit 0



:main
if not exist !BINDIR! echo error, not found target_dir &exit 0
cd !BINDIR!
!RUN_CMD!

goto :eof