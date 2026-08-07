param(
  [Parameter(Mandatory = $true)]
  [string]$PiHost,

  [string]$PiUser = "pi",
  [string]$AppDir = "/opt/planb-nas",
  [string]$NasUsername,
  [string]$NasPassword,
  [string]$NasServer = "192.168.0.204",
  [string]$NasShare = "PlanB_Media",
  [string]$NasMount = "/mnt/planb_media",
  [string]$AdminPassword,
  [string]$SudoPassword,
  [string]$KeyPath,
  [switch]$UseTailscaleProxy,
  [int]$Port = 5000
)

$ErrorActionPreference = "Stop"

if (-not $NasUsername) {
  $NasUsername = Read-Host "NAS username"
}

if (-not $NasPassword) {
  $secureNasPassword = Read-Host "NAS password" -AsSecureString
  $NasPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureNasPassword)
  )
}

if (-not $AdminPassword) {
  $secureAdminPassword = Read-Host "PlanB-NAS admin password" -AsSecureString
  $AdminPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureAdminPassword)
  )
}

if (-not $SudoPassword) {
  $secureSudoPassword = Read-Host "Raspberry Pi sudo password" -AsSecureString
  $SudoPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureSudoPassword)
  )
}

$remote = "$PiUser@$PiHost"
$archive = Join-Path $env:TEMP "planb-nas-deploy.tar.gz"
$sshArgs = @()
if ($KeyPath) {
  $sshArgs = @("-i", $KeyPath)
}
if ($UseTailscaleProxy) {
  $sshArgs += @("-o", "ProxyCommand=tailscale nc %h %p", "-o", "StrictHostKeyChecking=accept-new")
}

if (Test-Path $archive) {
  Remove-Item -LiteralPath $archive -Force
}

tar `
  --exclude .git `
  --exclude .venv `
  --exclude instance `
  --exclude .env `
  --exclude planb_nas_deploy `
  --exclude planb_nas_deploy.pub `
  -czf $archive .

ssh @sshArgs $remote "echo '$SudoPassword' | sudo -S -p '' mkdir -p '$AppDir' && echo '$SudoPassword' | sudo -S -p '' chown -R '$($PiUser):$($PiUser)' '$AppDir'"
scp @sshArgs $archive "${remote}:/tmp/planb-nas-deploy.tar.gz"
ssh @sshArgs $remote "tar -xzf /tmp/planb-nas-deploy.tar.gz -C '$AppDir'"

$escapedNasUsername = $NasUsername.Replace("'", "'\''")
$escapedNasPassword = $NasPassword.Replace("'", "'\''")
$escapedAdminPassword = $AdminPassword.Replace("'", "'\''")
$escapedSudoPassword = $SudoPassword.Replace("'", "'\''")

$escapedNasServer = $NasServer.Replace("'", "'\''")
$escapedNasShare = $NasShare.Replace("'", "'\''")
$escapedNasMount = $NasMount.Replace("'", "'\''")

ssh @sshArgs $remote "cd '$AppDir' && APP_USER='$PiUser' APP_GROUP='$PiUser' APP_DIR='$AppDir' NAS_SERVER='$escapedNasServer' NAS_SHARE='$escapedNasShare' NAS_MOUNT='$escapedNasMount' NAS_USERNAME='$escapedNasUsername' NAS_PASSWORD='$escapedNasPassword' ADMIN_PASSWORD='$escapedAdminPassword' SUDO_PASSWORD='$escapedSudoPassword' FLASK_PORT='$Port' bash deploy/remote_install.sh"

Remove-Item -LiteralPath $archive -Force
