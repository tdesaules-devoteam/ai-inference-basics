terraform {
  required_version = "= 1.17.2"
  required_providers {
    scaleway = {
      source  = "scaleway/scaleway"
      version = "2.91.0"
    }
  }
  backend "local" {}
}

provider "scaleway" {
  project_id = var.project_id
  region     = var.region
  zone       = var.zone
}
