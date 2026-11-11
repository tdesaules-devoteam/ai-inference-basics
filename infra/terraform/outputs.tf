output "environment_id" {
  value = local.prefix
}
output "expires_at" {
  value = local.expires_at
}
output "labs" {
  value = [for i, server in scaleway_instance_server.lab : {
    hostname = server.name
    ip       = scaleway_instance_ip.lab[i].address
    url      = format("https://lab-%02d.%s:30443", i + 1, var.base_domain)
  }]
}
