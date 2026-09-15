# Authentication Boundary

The local workstation deliberately has no browser-side password database

`frontend/src/lib/useAuth.ts` only exposes a fixed local-session compatibility object so inherited components can render without storing credentials

Do not treat that object as authentication and do not expose the workstation directly to the public internet

For remote access:

1. Keep Next.js, FastAPI, and ComfyUI bound to the loopback interface
2. Connect the local Next.js port to the VPS through the reverse SSH tunnel
3. Require the VPS identity gateway or an Authentik proxy provider before every application route
4. Forward verified identity headers only from the trusted reverse proxy
5. Keep administrative mutation routes disabled with `AIALRA_LOCKED_MODE=1`

See `docs/REMOTE_DEPLOYMENT.md` for the complete boundary and verification checklist
