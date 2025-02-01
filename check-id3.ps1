# Add this at the top of the file, after $ErrorActionPreference
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = 'Check-ID3'

# Function to check admin privileges
function Test-Admin {
    $currentUser = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentUser.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Function to elevate the script
function Elevate-Script {
    Write-Host 'Relaunching with elevated privileges...' -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    
    # Relaunch the script with admin rights
    Start-Process powershell -ArgumentList "-NoExit -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

# Function to relaunch the script as admin
function Launch-As-Admin {
    Write-Host 'Administrator privileges are required for installation.' -ForegroundColor Red
    $choice = Read-Host 'Do you want to elevate now? (Y/N)'
    if ($choice -eq 'Y' -or $choice -eq 'y') {
        Elevate-Script
    } else {
        Write-Host 'Please run this script as administrator to continue.' -ForegroundColor Red
        Pause
        exit
    }
}

# Colors and formatting
$ErrorActionPreference = 'Stop'

# At the top, after ErrorActionPreference
$settingsFile = "settings.ini"
$isInstalled = $false

# Check if settings file exists and read installation status
if (Test-Path $settingsFile) {
    $settingsContent = Get-Content $settingsFile
    # Look for the installed=true line specifically
    $isInstalled = $settingsContent | Where-Object { $_ -match 'installed=true' }
}

if ($isInstalled) {
    # Add variables to store last used paths and modes
    $lastTagsPath = $null
    $lastFolderPath = $null
    $verboseMode = $false
    $outputFileMode = $false

    # Run mode
    while ($true) {
        Clear-Host
        Write-Host '========================================' -ForegroundColor Blue
        Write-Host '            Check-ID3' -ForegroundColor Blue
        Write-Host '========================================' -ForegroundColor Blue
        Write-Host
        
        Write-Host "Available commands:" -ForegroundColor Yellow
        Write-Host "  help    - Show help text" -ForegroundColor Gray
        Write-Host "  exit    - Exit the program" -ForegroundColor Gray
        Write-Host "  verbose - Toggle verbose mode (currently: $(if ($verboseMode) { 'enabled' } else { 'disabled' }))" -ForegroundColor Gray
        Write-Host "  output  - Toggle results output to file (currently: $(if ($outputFileMode) { 'enabled' } else { 'disabled' }))" -ForegroundColor Gray
        if ($lastTagsPath -and $lastFolderPath) {
            Write-Host "  repeat  - Repeat last check" -ForegroundColor Gray
            Write-Host "           Last used:" -ForegroundColor Gray
            Write-Host "           Tags:   $($lastTagsPath)" -ForegroundColor Gray
            Write-Host "           Folder: $($lastFolderPath)" -ForegroundColor Gray
        }
        Write-Host
        Write-Host "Step 1: Enter the path to your tags file (CSV/TSV):" -ForegroundColor Yellow
        Write-Host "Drag and drop, or type/paste the path" -ForegroundColor DarkCyan
        Write-Host
        $tagsInput = Read-Host "> "
        
        switch ($tagsInput.ToLower()) {
            'exit' { exit }
            'verbose' {
                $verboseMode = -not $verboseMode
                Write-Host
                Write-Host "Verbose mode $(if ($verboseMode) { 'enabled' } else { 'disabled' })" -ForegroundColor Cyan
                Write-Host
                Write-Host "Press any key to continue..." -ForegroundColor Yellow
                $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
                continue
            }
            'output' {
                $outputFileMode = -not $outputFileMode
                Write-Host
                Write-Host "File output $(if ($outputFileMode) { 'enabled' } else { 'disabled' }). Results will be saved to audio files folder." -ForegroundColor Cyan
                Write-Host
                Write-Host "Press any key to continue..." -ForegroundColor Yellow
                $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
                continue
            }
            'repeat' {
                if ($lastTagsPath -and $lastFolderPath) {
                    Write-Host
                    Write-Host "Repeating last check..." -ForegroundColor Cyan
                    Write-Host "Using tags file: $lastTagsPath" -ForegroundColor Cyan
                    Write-Host "Checking files in: $lastFolderPath" -ForegroundColor Cyan
                    Write-Host
                    
                    try {
                        Write-Host "Starting ID3 tag verification..." -ForegroundColor Green
                        $verboseArg = if ($verboseMode) { "-v" } else { "" }
                        $outputArg = if ($outputFileMode) { "-o" } else { "" }
                        $result = & python tag_verifier.py -t "$lastTagsPath" -f "$lastFolderPath" $verboseArg $outputArg 2>&1
                        if ($LASTEXITCODE -ne 0) {
                            Write-Host "Python script failed with exit code: $LASTEXITCODE" -ForegroundColor Red
                            Write-Host "Output:" -ForegroundColor Red
                            $result -split "`n" | ForEach-Object { Write-Host $_ }
                        } else {
                            $result -split "`n" | ForEach-Object { Write-Host $_ }
                        }
                    } catch {
                        Write-Host "Error running tag verifier:" -ForegroundColor Red
                        Write-Host "Exception: $_" -ForegroundColor Red
                        Write-Host "Stack Trace:" -ForegroundColor Red
                        Write-Host $_.ScriptStackTrace -ForegroundColor Red
                    }
                    
                    Write-Host
                    Write-Host "Press any key to continue..." -ForegroundColor Yellow
                    $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
                    continue
                } else {
                    Write-Host "No previous check to repeat!" -ForegroundColor Red
                    Write-Host
                    Write-Host "Press any key to continue..." -ForegroundColor Yellow
                    $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
                    continue
                }
            }
            'help' {
                Write-Host
                Write-Host "Check-ID3 verifies ID3 tags in MP3 files against expected values." -ForegroundColor Cyan
                Write-Host
                Write-Host "This app was written by @mcarlssen and is distributed freely at github.com/mcarlssen/check-id3" -ForegroundColor Cyan
                Write-Host
                Write-Host "A list of expected ID3 tags and values should be provided in CSV or TSV format," -ForegroundColor Cyan
                Write-Host "with three columns containing TAG, DESCRIPTION, and VALUE data." -ForegroundColor Cyan
                Write-Host "The VALUE field may contain a string, or a regex expression." -ForegroundColor Cyan
                Write-Host
                Write-Host "This powershell script provides an interactive interface for the underlying python script." -ForegroundColor Cyan
                Write-Host "if you wish, you can call the python script directly with the following command:" -ForegroundColor Cyan
                & python tag_verifier.py --help
                Write-Host
                Write-Host "Press any key to continue..." -ForegroundColor Yellow
                $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
                continue
            }
            default {
                $tagsPath = $tagsInput.Trim('"').Trim("'")
                
                # Validate tags file
                if (-not (Test-Path $tagsPath)) {
                    Write-Host "Error: Tags file does not exist: $tagsPath" -ForegroundColor Red
                    Write-Host
                    Write-Host "Press any key to restart..." -ForegroundColor Yellow
                    $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
                    continue
                }
                
                $extension = [System.IO.Path]::GetExtension($tagsPath)
                if ($extension -notmatch '\.csv$|\.tsv$') {
                    Write-Host "Error: Tags file must be a CSV or TSV file" -ForegroundColor Red
                    Write-Host
                    Write-Host "Press any key to restart..." -ForegroundColor Yellow
                    $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
                    continue
                }

                # Now prompt for the audio files folder
                Write-Host
                Write-Host "Step 2: Enter the path to your audio files folder:" -ForegroundColor Yellow
                Write-Host "Drag and drop, or type/paste the path" -ForegroundColor Cyan
                Write-Host
                $folderInput = Read-Host "> "
                $folderPath = $folderInput.Trim('"').Trim("'")

                # Validate folder path
                if (-not (Test-Path $folderPath -PathType Container)) {
                    Write-Host "Error: Folder does not exist: $folderPath" -ForegroundColor Red
                    Write-Host
                    Write-Host "Press any key to restart..." -ForegroundColor Yellow
                    $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
                    continue
                }
                
                Write-Host
                Write-Host "Checking files in: $folderPath" -ForegroundColor Cyan
                Write-Host "Using tags file: $tagsPath" -ForegroundColor Cyan
                Write-Host
                
                # Store the paths after validation succeeds
                $lastTagsPath = $tagsPath
                $lastFolderPath = $folderPath

                # Run the verifier with both paths
                try {
                    Write-Host "Starting ID3 tag verification..." -ForegroundColor Green
                    $verboseArg = if ($verboseMode) { "-v" } else { "" }
                    $outputArg = if ($outputFileMode) { "-o" } else { "" }
                    $result = & python tag_verifier.py -t "$tagsPath" -f "$folderPath" $verboseArg $outputArg 2>&1
                    if ($LASTEXITCODE -ne 0) {
                        Write-Host "Python script failed with exit code: $LASTEXITCODE" -ForegroundColor Red
                        Write-Host "Output:" -ForegroundColor Red
                        $result -split "`n" | ForEach-Object { Write-Host $_ }
                    } else {
                        $result -split "`n" | ForEach-Object { Write-Host $_ }
                    }
                } catch {
                    Write-Host "Error running tag verifier:" -ForegroundColor Red
                    Write-Host "Exception: $_" -ForegroundColor Red
                    Write-Host "Stack Trace:" -ForegroundColor Red
                    Write-Host $_.ScriptStackTrace -ForegroundColor Red
                }
                
                Write-Host
                Write-Host "Press any key to continue..." -ForegroundColor Yellow
                $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
            }
        }
    }
}

# Installation mode - existing installation code continues here
# Add this near the top, after ErrorActionPreference
$installationPerformed = $false

function Show-Header {
    Clear-Host
    Write-Host '========================================' -ForegroundColor Blue
    Write-Host '    Check-ID3 Installer' -ForegroundColor Blue
    Write-Host '========================================' -ForegroundColor Blue
    Write-Host
}

# Initial setup
Show-Header
Write-Host 'This application will now verify and install any required dependencies.'
Write-Host ''

# Check for Python
Write-Host '1/3 Checking for Python installation...' -ForegroundColor Yellow
try {
    $pythonVersion = & python --version 2>&1
    Write-Host ('[OK] Python found: {0}' -f $pythonVersion) -ForegroundColor Green
    Write-Host ''
} catch {
    Write-Host 'WARNING: Python not found!' -ForegroundColor Red
    if (-not (Test-Admin)) {
        Launch-As-Admin
    }
    
    # Install Python
    $installationPerformed = $true
    Write-Host 'Attempting to install Python...' -ForegroundColor Yellow
    Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.4/python-3.11.4-amd64.exe' -OutFile 'python_installer.exe'
    Start-Process .\python_installer.exe -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1' -Wait
    Remove-Item .\python_installer.exe
    
    # Verify Python installation
    try {
        $pythonVersion = & python --version 2>&1
        Write-Host ('[OK] Python installed: {0}' -f $pythonVersion) -ForegroundColor Green
    } catch {
        Write-Host 'ERROR: Python installation failed!' -ForegroundColor Red
        Write-Host 'Please install Python manually.'
        Pause
        exit
    }
}

# Check for pip
Write-Host '2/3 Checking for pip installation...' -ForegroundColor Yellow
try {
    $pipVersion = & python -m pip --version 2>&1
    Write-Host ('[OK] Pip found: {0}' -f $pipVersion) -ForegroundColor Green
    Write-Host ''
} catch {
    Write-Host 'WARNING: Pip not found!' -ForegroundColor Red
    Write-Host ''

    if (-not (Test-Admin)) {
        Launch-As-Admin
    }
    
    # Install pip
    $installationPerformed = $true
    Write-Host 'Attempting to install pip...' -ForegroundColor Yellow
    & python -m ensurepip --upgrade
    try {
        $pipVersion = & python -m pip --version 2>&1
        Write-Host ('[OK] Pip installed: {0}' -f $pipVersion) -ForegroundColor Green
        Write-Host ''
    } catch {
        Write-Host 'ERROR: Pip installation failed!' -ForegroundColor Red
        Write-Host 'Please install pip manually.'
        Pause
        exit
    }
}

# Install mutagen
Write-Host '3/3 Checking for mutagen installation...' -ForegroundColor Yellow
try {
    $mutagenCheck = & python -m pip show mutagen 2>&1
    if ($mutagenCheck -match "Name: mutagen") {
        Write-Host '[OK] Mutagen is already installed' -ForegroundColor Green
        Write-Host ''
    } else {
        throw "Mutagen not found"
    }
} catch {
    Write-Host 'Mutagen not found. Installing...' -ForegroundColor Yellow
    if (-not (Test-Admin)) {
        Launch-As-Admin
    }
    
    # Install mutagen
    $installationPerformed = $true
    try {
        & python -m pip install mutagen
        Write-Host ''
        Write-Host '[OK] Mutagen installed successfully' -ForegroundColor Green
        Write-Host ''
    } catch {
        Write-Host 'ERROR: Installation failed!' -ForegroundColor Red
        Write-Host 'Please install dependencies manually.'
        Pause
        exit
    }
}

# Verify installation
try {
    if ($installationPerformed) {
        Write-Host '========================================' -ForegroundColor Green
        Write-Host '    Installation completed successfully!' -ForegroundColor Green
        Write-Host '========================================' -ForegroundColor Green
        Write-Host
        Write-Host 'You can now use Check-ID3.' -ForegroundColor Green
    } else {
        Write-Host '========================================' -ForegroundColor Blue
        Write-Host '    Check-ID3 is already installed' -ForegroundColor Blue
        Write-Host '========================================' -ForegroundColor Blue
        Write-Host
    }
    & python tag_verifier.py --help
} catch {
    Write-Host '========================================' -ForegroundColor Red
    Write-Host '    Installation failed!' -ForegroundColor Red
    Write-Host '========================================' -ForegroundColor Red
    Write-Host
    Write-Host 'Please check the error messages above.' -ForegroundColor Red
}

# After successful verification, create settings file
if (-not $?) {
    # Installation failed, don't create settings
    exit
}

# Create settings file
@"
installed=true
"@ | Out-File -FilePath $settingsFile -Encoding UTF8

Write-Host
Write-Host "You can now double-click this script again to run Check-ID3!" -ForegroundColor Cyan 