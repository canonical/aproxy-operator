# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variable "app_name" {
  description = "Application name for aproxy."
  type        = string
  default     = "aproxy"
}

variable "charm_name" {
  description = "Charmhub charm name for aproxy."
  type        = string
  default     = "aproxy"
}

variable "base" {
  description = "The operating system on which to deploy"
  type        = string
  default     = "ubuntu@24.04"
}

variable "channel" {
  description = "The channel to use when deploying a charm."
  type        = string
  default     = "latest/stable"
}

variable "config" {
  description = "Application config. Details about available options can be found at https://charmhub.io/aproxy/configurations."
  type        = map(string)
  default     = {}
}

variable "model" {
  description = "Reference to a `juju_model`."
  type        = string
}

variable "revision" {
  description = "Revision number of the charm"
  type        = number
  default     = null
}