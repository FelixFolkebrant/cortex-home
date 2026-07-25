# Coordinator

Install the coordinator from a machine that can reach the Ubuntu server over
SSH:

```sh
./coordinator/install <server-ssh-host>
```

The SSH destination is supplied at runtime so the server hostname or address
does not enter Git. The installer copies the fixed runtime files to
`/opt/cortex-home`, installs `cortex-home.service`, and starts the coordinator
on port 8080.

For local development:

```sh
python3 coordinator/cortex_home.py --host 127.0.0.1
```

Run the automated tests with:

```sh
python3 -m unittest discover -s coordinator/tests
```

With the endpoint connected, an outside caller can invoke the only allowed
action:

```sh
curl \
  --fail-with-body \
  --header 'Content-Type: application/json' \
  --data '{"requestId":"manual-1","action":"endpoint.identify"}' \
  http://<server-host>:8080/api/actions
```

The request remains open until the endpoint reports completion or failure. The
JSON response carries the same request ID. Use a new request ID for every
invocation while the coordinator process remains running.
