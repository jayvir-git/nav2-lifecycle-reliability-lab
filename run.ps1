$ErrorActionPreference = 'Stop'
$linuxPath = (& wsl -d Nav2-Jazzy --exec wslpath -u $PSScriptRoot.Replace('\','/')).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve lab path in WSL' }
& wsl -d Nav2-Jazzy -u learner --exec bash "$linuxPath/run.sh" @args
exit $LASTEXITCODE
