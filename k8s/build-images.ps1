# Run from the project root.
# Builds each image with Docker Desktop, then copies it into Minikube (works with the containerd runtime).
$ErrorActionPreference = "Stop"
$images = @(
  @("user-service",    "./services/user-service"),
  @("catalog-service", "./services/catalog-service"),
  @("booking-service", "./services/booking-service"),
  @("booking-worker",  "./worker"),
  @("frontend",        "./frontend")
)
foreach ($i in $images) {
  $tag = "ticketrush/$($i[0]):dev"
  Write-Host "=== Building $tag" -ForegroundColor Cyan
  docker build -t $tag $i[1]
  if ($LASTEXITCODE -ne 0) { throw "docker build failed for $tag" }
  Write-Host "=== Loading $tag into Minikube" -ForegroundColor Cyan
  minikube image load $tag
  if ($LASTEXITCODE -ne 0) { throw "minikube image load failed for $tag" }
}
Write-Host "Done. Images inside Minikube:" -ForegroundColor Green
minikube image ls | Select-String ticketrush
