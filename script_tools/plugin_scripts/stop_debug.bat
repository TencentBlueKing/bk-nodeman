@echo off
setlocal enabledelayedexpansion

echo "clean debug plugin"

:loop
	IF NOT "%1"=="" (
		IF "%1"=="-p" (
			SET INSTALL_PATH=%2
			SHIFT
		)
		IF "%1"=="-n" (
			SET PLUGIN_NAME=%2
			SHIFT
		)
		IF "%1"=="-g" (
			SET GROUP_ID=%2
			SHIFT
		)
		SHIFT
		GOTO :loop
	)
	if "!PLUGIN_NAME!"=="" goto :usage
	if "!INSTALL_PATH!"=="" goto :usage
	if "!GROUP_ID!"=="" goto :usage

:usage
	echo "usage: stop debug OPTIONS"
	echo "OPTIONS"
	echo "  -n  plugin name"
	echo "  -p  home path of plugin"
	echo "  -g  group id"
	exit 0


set BINDIR=!INSTALL_PATH!\external_plugins\!GROUP_ID!\!PLUGIN_NAME!\

echo "Stopping debug process..."

for %%i in (%BINDIR%\pid\*.pid) do (
	for /f %%j in (%%i) do (
		set pid=%%j
		echo "Found PID file: %%i"
		echo "PID to be killed: %%j"
		taskkill /F /PID !pid!))

echo "Removing plugin directory..."
echo Y | rd /S %BINDIR%
exit 0