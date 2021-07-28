@echo off

echo Showing used ports

echo ===== list of used ports begin =====

for /f "tokens=2" %%a in ('netstat -ano') do set $%%a=Y
for /f "delims=$=" %%a in ('set $ 2^>Nul') do echo %%a

echo ===== list of used ports end =====
