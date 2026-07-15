@echo off
cd /d "c:\Users\Win10\salomon ai ss"
set "PATH=C:\Program Files\Git\cmd;%PATH%"

echo === 1. git init ===
git init
if errorlevel 1 exit /b 1

echo === 2. git add . ===
git add .
if errorlevel 1 exit /b 1

echo === 3. git commit ===
git -c user.name=Israel -c user.email=israel@users.noreply.github.com commit -m "Primer commit de Salomon AI Studio"
if errorlevel 1 (
  echo No hay cambios nuevos; amend del commit local...
  git -c user.name=Israel -c user.email=israel@users.noreply.github.com commit --amend -m "Primer commit de Salomon AI Studio"
)

echo === 4. git branch -M main ===
git branch -M main
if errorlevel 1 exit /b 1

echo === 5. git remote add origin ===
git remote remove origin 2>nul
git remote add origin https://github.com/israelmontas63-lgtm/salomon-ai-studio.git
if errorlevel 1 exit /b 1
git remote -v

echo === 6. git push -u origin main ===
git push -u origin main
exit /b %ERRORLEVEL%
