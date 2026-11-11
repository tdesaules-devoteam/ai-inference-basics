locals {
  prefix     = "ai-inference-basics-${var.training_session_id}"
  expires_at = timeadd(var.session_started_at, "${var.ttl_hours}h")
  tags = concat(var.tags, [
    "owner=ai-inference-basics", "environment=${var.environment}",
    "session=${var.training_session_id}", "expires-at=${local.expires_at}",
    "release=${var.release_version}"
  ])
}

resource "scaleway_instance_security_group" "lab" {
  name                    = local.prefix
  inbound_default_policy  = "drop"
  outbound_default_policy = "accept"
  stateful                = true
  tags                    = local.tags
  dynamic "inbound_rule" {
    for_each = var.authorized_ssh_cidrs
    content {
      action   = "accept"
      protocol = "TCP"
      port     = 22
      ip_range = inbound_rule.value
    }
  }
  dynamic "inbound_rule" {
    for_each = var.enable_public_https ? var.authorized_https_cidrs : toset([])
    content {
      action   = "accept"
      protocol = "TCP"
      port     = 30443
      ip_range = inbound_rule.value
    }
  }
}

resource "scaleway_instance_ip" "lab" {
  count = var.instance_count
  tags  = local.tags
}

resource "scaleway_instance_server" "lab" {
  count             = var.instance_count
  name              = format("%s-%02d", local.prefix, count.index + 1)
  type              = var.instance_type
  image             = var.image_id
  ip_id             = scaleway_instance_ip.lab[count.index].id
  security_group_id = scaleway_instance_security_group.lab.id
  tags              = local.tags
  root_volume {
    name                  = format("%s-%02d-boot", local.prefix, count.index + 1)
    volume_type           = "sbs_volume"
    size_in_gb            = var.volume_size_gb
    sbs_iops              = var.volume_iops
    delete_on_termination = true
  }
  user_data = {
    cloud-init = templatefile("${path.module}/../cloud-init/base.yaml.tftpl", {
      ssh_public_key = var.ssh_public_key
      bootstrap      = indent(6, file("${path.module}/../cloud-init/bootstrap-k0s.sh"))
      k0s_config     = indent(6, file("${path.module}/../k0s/config.yaml"))
    })
  }
  lifecycle {
    precondition {
      condition     = var.instance_count == 1 || (var.environment == "training" && var.training_acknowledged && var.pilot_accepted)
      error_message = "Eight instances require explicit training acknowledgement and an accepted H100 pilot."
    }
    precondition {
      condition     = var.environment == "scaleway-cpu-pilot" || (var.pilot_accepted && var.volume_size_gb >= 125)
      error_message = "GPU provisioning requires prior pilot acceptance and at least 125 GB boot storage."
    }
    precondition {
      condition     = timecmp(var.session_started_at, timestamp()) <= 0
      error_message = "The allocation start must not be in the future."
    }
    precondition {
      condition     = timecmp(timestamp(), local.expires_at) < 0
      error_message = "The allocation has expired; create a new session instead of extending this one."
    }
  }
}
