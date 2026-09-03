# Platform Roadmap

## Current

- [PLT-001](issues/PLT-001.md) records the qualified iMac hardware and Ubuntu
  baseline.
- [PLT-002](issues/PLT-002.md) makes the kiosk endpoint reproducible.
- [PLT-003](issues/PLT-003.md) establishes the coordinator, React client,
  correlated action lifecycle, service installation, and physical Sonos path.
- [PLT-005](issues/PLT-005.md) consolidates coordinator and endpoint desired
  state in two Ansible playbooks with focused speech, Music, media, and alarm
  tags.
- [Chromium performance findings](CHROMIUM_PERFORMANCE.md) record why channel
  replacement remains immediate on the low-end endpoint.

## Next

- [PLT-004](wip/PLT-004.md) will make the normal development loop an IdeaPad
  browser client plus a loopback-only simulated coordinator. It will reuse the
  production HTTP and SSE boundary, but will never contact room hardware or be
  included in the production installer.
- Keep production deployment checks aligned with every runtime module so a new
  source file cannot be omitted from the installed service.

## Later

- Reconsider the endpoint hardware when maintenance or performance costs exceed
  the value of the existing iMac panel.
- Add TLS, authentication, or remote access only for a concrete off-LAN flow.
- Split a service into another repository only after it has an independently
  useful deployment and release lifecycle.

## Open Decisions

- Whether future endpoint hardware still benefits from native helper processes
  beside the browser shell.
- Whether additional device families justify a general automation service.

## Accepted Decisions

- Keep one integration repository and one coordinator service for the current
  room.
- Keep compute and durable authority on the ThinkPad; treat the iMac as a
  replaceable local display and media endpoint.
- Use Ubuntu, a minimal Xorg/Openbox kiosk, and repository-owned provisioning.
- Use Ansible for privileged host desired state while keeping interactive
  product operations and installed endpoint helpers as narrow executables.
- Use React with Vite, Tailwind CSS, pnpm, `clsx`, CVA, `tailwind-merge`, and
  Biome without a router or application framework.
- Keep the Sonos attached to the iMac and pin room output explicitly so attached
  USB devices cannot silently become the speaker.
