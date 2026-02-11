# Build Nexys4 DDR Bitstream on Windows
# PowerShell script to run Vivado synthesis from a copied gateware folder
# Usage: .\windows_build_bitstream.ps1 -BuildFolder "Z:\nexys4ddr_build"

param(
    [Parameter(Mandatory=$true, HelpMessage="Path to the gateware build folder")]
    [string]$BuildFolder
)

# Validate input
if (-not (Test-Path $BuildFolder)) {
    Write-Error "Build folder not found: $BuildFolder"
    exit 1
}

# Find the TCL file
$tclFile = Get-ChildItem -Path $BuildFolder -Filter "*.tcl" -File | Select-Object -First 1

if ($null -eq $tclFile) {
    Write-Error "No TCL file found in $BuildFolder"
    exit 1
}

Write-Host "Found TCL file: $($tclFile.Name)" -ForegroundColor Green
Write-Host "Build folder: $BuildFolder" -ForegroundColor Green
Write-Host ""

# Check if Vivado is available
$vivadoPath = Get-Command vivado -ErrorAction SilentlyContinue
if ($null -eq $vivadoPath) {
    Write-Error "Vivado not found in PATH. Please add Vivado to your PATH and try again."
    Write-Host "Typical path: C:\Xilinx\Vivado\<version>\bin"
    exit 1
}

Write-Host "Using Vivado: $($vivadoPath.Source)" -ForegroundColor Green
Write-Host ""

# Change to the build directory and run Vivado
Push-Location $BuildFolder
try {
    Write-Host "Running Vivado synthesis..." -ForegroundColor Cyan
    Write-Host "Command: vivado -mode batch -source $($tclFile.Name)" -ForegroundColor Cyan
    Write-Host ""
    
    & vivado -mode batch -source $tclFile.Name
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "=== Vivado synthesis completed successfully ===" -ForegroundColor Green
        Write-Host ""
        
        # Find the generated bitstream
        $bitFile = Get-ChildItem -Path $BuildFolder -Filter "*.bit" -File | Select-Object -First 1
        
        if ($null -ne $bitFile) {
            Write-Host "Bitstream generated:" -ForegroundColor Green
            Write-Host "  Name: $($bitFile.Name)" -ForegroundColor Green
            Write-Host "  Size: $([math]::Round($bitFile.Length / 1MB, 2)) MB" -ForegroundColor Green
            Write-Host "  Path: $($bitFile.FullName)" -ForegroundColor Green
            Write-Host ""
            Write-Host "Ready to program the Nexys4 DDR board!" -ForegroundColor Green
        } else {
            Write-Host "Warning: No .bit file found in $BuildFolder" -ForegroundColor Yellow
            Write-Host "Check vivado.log for details."
        }
    } else {
        Write-Host ""
        Write-Host "=== Vivado synthesis failed ===" -ForegroundColor Red
        Write-Host "Exit code: $LASTEXITCODE" -ForegroundColor Red
        Write-Host "Check vivado.log for details." -ForegroundColor Red
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
