Param()

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Starting backend (Back) and frontend (Front) in separate PowerShell windows..."

Start-Process -NoNewWindow -FilePath "powershell" -ArgumentList @('-NoProfile','-NoExit','-Command',"Set-Location -Path '$root\\Back'; if (-Not (Test-Path venv)) { python -m venv venv }; .\\venv\\Scripts\\Activate.ps1; pip install -r requirements.txt; python -m uvicorn main:app --reload --port 8000")

Start-Process -NoNewWindow -FilePath "powershell" -ArgumentList @('-NoProfile','-NoExit','-Command',"Set-Location -Path '$root\\Front'; npm install; npm run dev")

Write-Host "Laissés en cours d'exécution dans de nouvelles fenêtres PowerShell. Fermez-les pour arrêter les serveurs."
