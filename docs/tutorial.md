# Deploy the aproxy subordinate charm

## Introduction

The aproxy subordinate charm provides proxy functionality that can be attached to a principal charm. As a subordinate charm, it enhances existing applications by adding proxy configuration management and integration without being deployed as a standalone service.

In this tutorial, you will deploy the aproxy subordinate charm in a Juju model, relate it to a principal charm, and verify that it is correctly integrated and running.

## What you will do

In this tutorial, you will:

1. Set up a Juju model for testing.
2. Deploy a principal charm that aproxy can relate to.
3. Deploy the aproxy subordinate charm and relate it to the principal charm.
4. Verify that the deployment was successful.
5. Perform a simple configuration test.
6. Tear down your environment.

## Requirements

Before starting, ensure you have the following:

- A working station (e.g., a laptop) with amd64 architecture.
- Juju 3 installed and bootstrapped to a LXD controller. You can accomplish this process by using a Multipass VM as outlined in this guide: [Set up / Tear down your test environment](https://documentation.ubuntu.com/juju/latest/howto/manage-your-juju-deployment/set-up-your-juju-deployment-local-testing-and-development/index.html).

## Set up the tutorial model

First, create a new Juju model named `aproxy-tutorial`. This model will isolate the tutorial environment from your other deployments.

```bash
juju add-model aproxy-tutorial
```

You can confirm that the model has been created by running:

```bash
juju models
```

## Deploy the principal charm

Since aproxy is a subordinate charm, it must be related to a principal charm. In this example, we will use the **Ubuntu** charm as the primary application to demonstrate how aproxy integrates with another service.

Deploy the ubuntu charm:

```bash
juju deploy ubuntu
```

Wait until the deployment is complete:

```bash
juju status --watch 1s
```

When the application is active and ready, the output should look similar to:

```
App     Version  Status  Scale  Charm   Channel        Rev  Exposed  Message
ubuntu  24.04    active      1  ubuntu  latest/stable   26  no
```

## Deploy the aproxy subordinate charm

Now deploy the aproxy charm with the target proxy address and proxy port. In this example, we will use `127.0.0.1:80`.

```bash
juju deploy aproxy --config proxy-address="127.0.0.1:80"
```

Because it is a subordinate charm, it will not create its own unit until it is related to a principal charm.

## Integrate aproxy to the principal charm

Next, integrate the aproxy subordinate charm to the Ubuntu application. This establishes the connection that allows aproxy to intercept outbound TCP traffic from the Ubuntu charm.

```bash
juju integrate ubuntu aproxy
```

Once the relation is established, Juju will automatically attach aproxy to the Ubuntu unit.

## Check the deployment was successful

Verify that both charms are deployed and related correctly:

```bash
juju status
```

The output should be similar to the following:

```
Model           Controller  Cloud/Region   Version
aproxy-tutorial lxd         localhost      3.4.1

App     Version  Status  Scale  Charm   Channel        Rev  Exposed  Message
aproxy           active      1  aproxy  latest/stable    1  no       Service ready on target proxy 127.0.0.1:80
ubuntu  24.04    active      1  ubuntu  latest/stable   26  no

Unit         Workload  Agent  Machine  Public address  Ports  Message
ubuntu/0*    active    idle   0        10.152.184.228
  aproxy/0*  active    idle            10.152.184.228         Service ready on target proxy 127.0.0.1:80
```

You should see both applications in an **active** state, with aproxy listed as a subordinate unit to the Ubuntu charm.

## Run a configuration test

To confirm that the charm is functioning properly, run configuration change on aproxy.

Let's set the `intercept-ports` to be `80`:

```bash
juju config aproxy intercept-ports=80
```

Then verify that the configuration has been applied:

```bash
juju config aproxy
```

The output should be similar to the following:

```
application: aproxy
application-config:
  trust:
    default: false
    description: Does this application have access to trusted credentials
    source: default
    type: bool
    value: false
charm: aproxy
settings:
  exclude-addresses-from-proxy:
    default: 127.0.0.1
    description: Comma-separated list of IP or hostname addresses that should bypass
      the proxy.
    source: default
    type: string
    value: 127.0.0.1
  intercept-ports:
    default: 80,443
    description: |
      Comma-separated list of ports to intercept and forward through the proxy.
      Support:
      - Single port e.g., 80
      - List of comma-separated ports e.g., 80,443
      - Range (both sides included) e.g., 1024-2048
      - List of ranges e.g. 80-90,1024-2048
      - Keyword "ALL" which corresponds to the range 1-65536
    source: default
    type: string
    value: 80
  proxy-address:
    description: |
      Configures the target proxy IP address and port for traffic forwarding.
      For example: "1.2.3.4:8888" or "1.2.3.4".
      If no proxy is specified, the default proxy is the principal charm's juju-https-proxy or juju-http-proxy relation data.
      If no port is specified, the default port value of 80 will be used.
    source: user
    type: string
    value: 127.0.0.1:80

```

## Run a connection test

To confirm that aproxy is forwarding properly, make an outbound TCP connection on the principal charm.

For example, let's curl `cloud-images.ubuntu.com` from inside `ubuntu/0` unit:

```bash
juju ssh ubuntu/0
curl -v cloud-images.ubuntu.com
```

If successful, the output should be similar to the following:

```
* Host cloud-images.ubuntu.com:80 was resolved.
* IPv6: 2620:2d:4000:1::17, 2620:2d:4000:1::1a
* IPv4: 185.125.190.40, 185.125.190.37
*   Trying 185.125.190.40:80...
* Connected to cloud-images.ubuntu.com (185.125.190.40) port 80
> GET / HTTP/1.1
> Host: cloud-images.ubuntu.com
> User-Agent: curl/8.5.0
> Accept: */*
>
< HTTP/1.1 200 OK
< Transfer-Encoding: chunked
< Connection: close
< Content-Type: text/html;charset=UTF-8
< Date: Tue, 14 Oct 2025 08:43:00 GMT
< Server: Apache/2.4.29 (Ubuntu)
< Vary: Accept-Encoding
< Via: 1.1 juju-9d5023-prod-ps6-internal-proxy-13 (squid/5.9)
< X-Cache: MISS from juju-9d5023-prod-ps6-internal-proxy-13
< X-Cache-Lookup: MISS from juju-9d5023-prod-ps6-internal-proxy-13:3128
```

Then verify that aproxy is intercepting and forwarding the traffic to target proxy:

```bash
sudo snap logs aproxy.aproxy -f
```

Expected output:

```
2025-10-13T14:18:16Z aproxy.aproxy[16156]: 2025/10/13 14:18:16 INFO start listening on :8443
2025-10-13T14:18:16Z aproxy.aproxy[16156]: 2025/10/13 14:18:16 INFO start forwarding to proxy 127.0.0.1:80
2025-10-14T08:43:00Z aproxy.aproxy[16156]: 2025/10/14 08:43:00 INFO relay HTTP connection to proxy src=10.142.134.228:41826 original_dst=185.125.190.40:80 host=cloud-images.ubuntu.com:80
```

## Tear down the environment

Congratulations! 🎉

You have successfully deployed the aproxy subordinate charm, related it to a primary application, and verified that it works as expected.

When you’re done with the tutorial, clean up your environment to free resources:

```bash
juju destroy-model aproxy-tutorial --destroy-storage --force --no-prompt
```

If you used a Multipass VM for this tutorial and no longer need it, you can remove it with:

```bash
multipass delete --purge my-juju-vm
```

## Next steps

Visit the [aproxy charm documentation](https://charmhub.io/aproxy/docs) for advanced usage and configuration options.
