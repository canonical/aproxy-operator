# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

terraform {
  required_version = ">= 1.0"
  required_providers {
    juju = {
      version = "> 1.1.0"
      source  = "juju/juju"
    }
    external = {
      version = "> 2"
      source  = "hashicorp/external"
    }
  }
}

provider "juju" {}

variable "model_uuid" {
  type = string
}

resource "juju_application" "ubuntu" {
  model_uuid = var.model_uuid
  charm {
    name = "ubuntu"
  }
}

resource "juju_integration" "aproxy_ubuntu" {
  model_uuid = var.model_uuid

  application {
    name = juju_application.ubuntu.name
  }

  application {
    name = "aproxy"
  }
}

# tflint-ignore: terraform_unused_declarations
data "external" "aproxy_status" {
  program = ["bash", "${path.module}/wait-for-status.sh", var.model_uuid]

  depends_on = [
    juju_integration.aproxy_ubuntu
  ]
}
