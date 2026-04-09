@echo off
"C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\MSBuild.exe" "%~dp0TimeSeriesLab.sln" /t:Build /p:Configuration=Release /p:Platform=x64 /v:minimal
