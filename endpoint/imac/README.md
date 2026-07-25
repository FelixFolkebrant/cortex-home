# iMac Endpoint

Run the provisioning entry point from the repository root while the qualified
iMac is reachable through the `imac` SSH host:

```sh
./endpoint/imac/provision
```

The command copies the fixed provisioning files to a temporary directory on
the iMac and asks for:

1. The existing `imac` account's sudo password.
2. The home Wi-Fi name.
3. The home Wi-Fi password.
4. The coordinator's local HTTP origin, without a path.

The Wi-Fi values are read by the remote installer without echoing the password.
They are written only to the root-readable Netplan configuration on the iMac.
The coordinator URL is written only to the endpoint's local configuration. The
temporary remote copy is removed when provisioning exits.

Provisioning installs the minimal graphical and wireless packages, creates the
locked `cortex-endpoint` account, configures its automatic full-screen session,
points Chromium at the network client, and persists the rear analog mixer route.
The command can be rerun to restore the committed configuration.

The endpoint advertises itself as `imac.local` on the home network. Press
`Control`+`Option`+`Return` on the iMac keyboard to open an unprivileged
recovery terminal above the kiosk. Run `su - imac` there when administrative
access is required, and close the terminal to return to the full-screen page.
