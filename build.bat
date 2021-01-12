:: Script for windows to build&push docker images
@echo off

SET BUILD_LOG=build.log
SET DOCKER_REPO=oskaras/kryabot
SET DOCKER_TAG=latest

call :log "Starting new build at %DATE% %TIME%"
call :log "Pulling changes from git repo"
git reset --hard >> %BUILD_LOG% || goto :error
git clean -f -d >> %BUILD_LOG% || goto :error
git pull >> %BUILD_LOG% || goto :error
call :log "Building docker image"
docker build -t %DOCKER_REPO%:%DOCKER_TAG% . >> %BUILD_LOG% || goto :error
call :log "Pushing docker image to repository %DOCKER_REPO%"
docker push %DOCKER_REPO%:%DOCKER_TAG% >> %BUILD_LOG% || goto :error
call :log "Success"

exit /b 0

:error
CALL :log "[91mScript failed, check %BUILD_LOG% file for full log. Exit code (%errorlevel%)[0m"
exit /b %errorlevel%

:log
echo [[92mKryaBot[0m] %~1
echo [KryaBot] %~1 >> %BUILD_LOG%

