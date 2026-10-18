# Rebuild only some services (default: the two changed in Part 4), load them into Minikube, restart them.
# Example for others: powershell -ExecutionPolicy Bypass -File k8s\rebuild-images.ps1 -Services user-service,booking-worker
param([string[]]$Services = @("booking-service", "frontend"))
$paths = @{ "user-service"="./services/user-service"; "catalog-service"="./services/catalog-service"; "booking-service"="./services/booking-service"; "booking-worker"="./worker"; "frontend"="./frontend" }
foreach ($s in $Services) {
  $tag = "ticketrush/${s}:dev"
  Write-Host "=== Building $tag" -ForegroundColor Cyan
  docker build -t $tag $paths[$s]
  if ($LASTEXITCODE -ne 0) { throw "docker build failed for $tag" }
  minikube image rm $tag 2>$null | Out-Null     # remove the old copy so the new one really replaces it
  minikube image load $tag
  if ($LASTEXITCODE -ne 0) { throw "minikube image load failed for $tag" }
  kubectl rollout restart deployment/$s -n ticketrush
}
Write-Host "Done." -ForegroundColor Green
