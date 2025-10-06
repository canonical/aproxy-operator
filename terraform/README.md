# Aproxy terraform module

This folder contains a base [Terraform][Terraform] module for the aproxy charm.

The module uses the [Terraform Juju provider][Terraform Juju provider] to model the charm
deployment onto any Kubernetes environment managed by [Juju][Juju].

## Module structure

- **main.tf** - Defines the Juju application to be deployed.
- **variables.tf** - Allows customization of the deployment. Also models the charm configuration, 
  except for exposing the deployment options (Juju model name, channel or application name).
- **output.tf** - Integrates the module with other Terraform modules, primarily
  by defining potential integration endpoints (charm integrations), but also by exposing
  the Juju application name.
- **versions.tf** - Defines the Terraform provider version.

## Using aproxy base module in higher level modules

If you want to use `aproxy` base module as part of your Terraform module, import it
like shown below:

```text
data "juju_model" "my_model" {
  name = var.model
}

module "aproxy" {
  source = "git::https://github.com/canonical/aproxy-operator//terraform"
  
  model = juju_model.my_model.name
  # (Customize configuration variables here if needed)
}
```

Create integrations, for instance:

```text
resource "juju_integration" "aproxy_to_principal" {
  model = juju_model.my_model.name
  application {
    name     = module.aproxy.app_name
    endpoint = module.aproxy.endpoints.juju_info
  }
  application {
    name     = "principal-app"
    endpoint = "juju-info"
  }
}
```

The complete list of available integrations can be found [in the Integrations tab][aproxy-integrations].

[Terraform]: https://www.terraform.io/
[Terraform Juju provider]: https://registry.terraform.io/providers/juju/juju/latest
[Juju]: https://juju.is
[aproxy-integrations]: https://charmhub.io/aproxy/integrations
