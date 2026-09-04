# Host Provisioning

Ansible owns the reproducible state of the ThinkPad coordinator and the iMac
endpoint. Application source and endpoint runtime helpers remain in their
module directories; the roles install those reviewed files onto each host.

## Controller setup

The root-level wrapper is the normal operator entry point:

```sh
./deploy all
```

It creates the pinned Ansible environment and ignored inventory when they do
not exist, checks SSH connectivity, and deploys the coordinator before the
iMac. It accepts the same useful Ansible options for focused or checked runs:

```sh
./deploy coordinator
./deploy imac --tags media
./deploy imac --tags raspotify
./deploy imac --check
```

Use `./deploy setup` when you only want to prepare the local Ansible
environment. The wrapper does not fill in private inventory values or bypass
the existing sudo and secret prompts.

From the repository root, create an isolated Ansible environment:

```sh
python3 -m venv .venv-ansible
. .venv-ansible/bin/activate
python -m pip install --disable-pip-version-check -r ops/requirements.txt
cp ops/inventory.example.yml ops/inventory.yml
```

The example uses the `homelab` and `imac` aliases from
`~/.ssh/config`, so it needs no private host values when those aliases already
work. Otherwise, edit only the ignored `ops/inventory.yml` to add the required
`ansible_host` and `ansible_user` values. Do not add passwords, private keys,
API keys, Wi-Fi credentials, or private addresses to the committed example.

Check unprivileged connectivity before provisioning:

```sh
cd ops
ansible all -m ping
```

Use `--ask-become-pass` when the remote administrative account requires a sudo
password. Ansible reads it only for the current invocation.

## Coordinator

Build the React client locally and converge the production coordinator:

```sh
cd ops
ansible-playbook playbooks/coordinator.yml --ask-become-pass
```

The first run prompts without echo for the OpenRouter key and creates
`/etc/cortex-home/agent.env`. Later runs validate and preserve that file.

Install or restore only the isolated speech qualification workbench:

```sh
cd ops
ansible-playbook playbooks/coordinator.yml --tags speech --ask-become-pass
```

## Endpoint

Converge the complete qualified iMac endpoint:

```sh
cd ops
ansible-playbook playbooks/endpoint.yml --ask-become-pass
```

The first run prompts for the coordinator's local HTTP origin and Wi-Fi values.
Later runs preserve the installed values. To deliberately replace them, keep a
mode-`0600` variables file outside the repository:

```yaml
endpoint_coordinator_url: http://coordinator.local:8080
endpoint_wifi_ssid: private-network
endpoint_wifi_password: private-password
```

Apply it once, then remove it:

```sh
cd ops
ansible-playbook playbooks/endpoint.yml \
  --extra-vars @/private/path/endpoint.yml \
  --ask-become-pass
```

An already provisioned endpoint can converge one concern without reading or
changing Wi-Fi configuration:

```sh
cd ops
ansible-playbook playbooks/endpoint.yml --tags media --ask-become-pass
ansible-playbook playbooks/endpoint.yml --tags raspotify --ask-become-pass
ansible-playbook playbooks/endpoint.yml --tags alarm --ask-become-pass
```

Full and focused runs validate Ubuntu 24.04, the `iMac8,1` product identity, and
the qualified Broadcom adapter before changing the endpoint.

## Static checks

Run both playbook syntax checks without contacting either example host:

```sh
cd ops
ansible-playbook -i inventory.example.yml --syntax-check playbooks/coordinator.yml
ansible-playbook -i inventory.example.yml --syntax-check playbooks/endpoint.yml
```
