@echo off
setlocal enabledelayedexpansion

rem Config (override via env vars where noted)
set "IMAGE_NAME=selenium-chrome"
set "CONTAINER_NAME=selenium-chrome-run"
if "%HTML_FILE%"=="" set "HTML_FILE=page.html"
if "%OUTPUT_JSON%"=="" set "OUTPUT_JSON=article.json"
if "%WAIT_SECONDS%"=="" set "WAIT_SECONDS=120"

rem URL argument (defaults to the requested VnExpress article)
set "URL=%~1"
if "%URL%"=="" set "URL=https://vnexpress.net/tuoi-35-lam-sep-nhung-so-khong-xin-duoc-viec-neu-that-nghiep-dot-xuat-4866122.html"

echo Using URL: %URL%
echo HTML_FILE: %HTML_FILE%
echo OUTPUT_JSON: %OUTPUT_JSON%
echo WAIT_SECONDS: %WAIT_SECONDS%

rem Stop any previous container
docker stop "%CONTAINER_NAME%" >nul 2>&1

rem Build image if missing
docker image inspect "%IMAGE_NAME%" >nul 2>&1
if errorlevel 1 (
  docker build -t "%IMAGE_NAME%" .
  if errorlevel 1 (
    echo Docker build failed.
    exit /b 1
  )
)

rem Start Selenium
docker run -d --rm --name "%CONTAINER_NAME%" -p 4444:4444 -p 7900:7900 --shm-size=2g "%IMAGE_NAME%"
if errorlevel 1 (
  echo Failed to start Selenium container.
  exit /b 1
)

rem Wait for readiness (best effort, proceeds on warning)
powershell -NoLogo -Command "param($wait) $u='http://localhost:4444/wd/hub/status'; for($i=0;$i -lt [int]$wait;$i++){ try { $resp=Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 $u; if($resp.Content -match '\"ready\"\\s*:\\s*true'){ exit 0 } } catch {} Start-Sleep -Seconds 1 } exit 1" %WAIT_SECONDS%
if errorlevel 1 (
  echo Warning: Selenium readiness not confirmed after %WAIT_SECONDS%s, continuing...
)

rem Download and extract
python crawler.py --url "%URL%" --download --html-file "%HTML_FILE%"
if errorlevel 1 goto cleanup_fail

python crawler.py --url "%URL%" --extract --html-file "%HTML_FILE%" --output "%OUTPUT_JSON%"
if errorlevel 1 goto cleanup_fail

echo Saved HTML to %HTML_FILE%
echo Saved JSON to %OUTPUT_JSON%
echo URL: %URL%

:cleanup
docker stop "%CONTAINER_NAME%" >nul 2>&1
exit /b 0

:cleanup_fail
echo Error during crawl/extract.
docker stop "%CONTAINER_NAME%" >nul 2>&1
exit /b 1
