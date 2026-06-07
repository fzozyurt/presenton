# OIDC Authentication & Multi-Workspace Guide

Presenton supports optional OIDC-based authentication for multi-user, multi-workspace deployments. When disabled, the app falls back to the default single-admin authentication.

## Architecture

```
OIDC_ENABLED=true
       │
       ▼
┌──────────────────────────────────────────────────────┐
│                  Presenton                            │
│                                                      │
│  ┌──────────┐   ┌──────────────┐   ┌─────────────┐  │
│  │ Identity │   │Access Control│   │  Workspaces  │  │
│  │  Module  │   │   (RBAC)     │   │  (Projects)  │  │
│  └────┬─────┘   └──────┬───────┘   └──────┬───────┘  │
│       │                │                  │          │
│  ┌────▼────────────────▼──────────────────▼───────┐  │
│  │              Database Layer                     │  │
│  │  users │ oauth_accounts │ roles │ workspaces   │  │
│  │            workspace_members                   │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  Existing tables (presentations, templates) gain:    │
│       workspace_id FK (nullable)                     │
│       created_by FK (nullable)                       │
└──────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│              OIDC Identity Provider                   │
│  (Keycloak, Authentik, Azure Entra ID, Okta, etc.)   │
└──────────────────────────────────────────────────────┘
```

## Environment Variables

Add these to your `docker-compose.yml` or `.env` file:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OIDC_ENABLED` | Yes | `false` | Set to `true` to enable OIDC authentication |
| `OIDC_ISSUER` | Yes | — | OIDC provider URL (e.g. `https://keycloak.example.com/realms/myrealm`) |
| `OIDC_CLIENT_ID` | Yes | — | Client ID registered with your IdP |
| `OIDC_CLIENT_SECRET` | No | — | Client secret (omit for public clients using PKCE only) |
| `OIDC_REDIRECT_URI` | Yes | — | Callback URL (e.g. `http://localhost:5000/api/v1/oidc/callback`) |
| `OIDC_SCOPES` | No | `openid profile email` | OIDC scopes to request |
| `WORKSPACE_MODE` | No | `single` | `single` (legacy) or `multi` (workspace support) |

## Quick Start

### 1. Register a client in your IdP

Create an OIDC client with:
- **Grant type**: Authorization Code + PKCE
- **Redirect URI**: `http://localhost:5000/api/v1/oidc/callback`
- **Scopes**: `openid profile email`

### 2. Configure environment

```yaml
# docker-compose.yml additions
environment:
  - OIDC_ENABLED=true
  - OIDC_ISSUER=https://your-idp.example.com
  - OIDC_CLIENT_ID=presenton
  - OIDC_CLIENT_SECRET=XXXX
  - OIDC_REDIRECT_URI=http://localhost:5000/api/v1/oidc/callback
  - WORKSPACE_MODE=multi
```

### 3. Start the app

```bash
docker compose up --build
```

Users will see "Sign in with OIDC" instead of the username/password form.

## OIDC Flow

```
Browser                  Presenton BE              Identity Provider
  │                           │                           │
  │ GET /                     │                           │
  │──────────────────────────>│                           │
  │                           │                           │
  │ GET /api/v1/auth/status   │                           │
  │──────────────────────────>│                           │
  │ {provider:"oidc", auth:false}                          │
  │<──────────────────────────│                           │
  │                           │                           │
  │ Redirect to /api/v1/oidc/login                         │
  │──────────────────────────>│                           │
  │                           │ GET /.well-known/oidc      │
  │                           │──────────────────────────>│
  │                           │ Generate PKCE challenge    │
  │                           │                           │
  │ Redirect to IdP auth URL  │                           │
  │<──────────────────────────│                           │
  │                           │                           │
  │ Authenticate with IdP     │                           │
  │───────────────────────────────────────────────────────>│
  │                           │                           │
  │ Redirect to /callback     │                           │
  │<──────────────────────────────────────────────────────│
  │                           │                           │
  │ GET /api/v1/oidc/callback │                           │
  │──────────────────────────>│                           │
  │                           │ POST /token (PKCE)        │
  │                           │──────────────────────────>│
  │                           │ GET /userinfo             │
  │                           │──────────────────────────>│
  │                           │ Create/find user in DB    │
  │                           │ Generate session cookie   │
  │                           │                           │
  │ Set-Cookie: presenton_oidc_session                    │
  │ Redirect to /upload       │                           │
  │<──────────────────────────│                           │
```

## Roles & Permissions

| Role | Permissions |
|------|-------------|
| **Owner** | All permissions including workspace deletion and role management |
| **Admin** | All CRUD except workspace deletion |
| **Editor** | Read/write presentations & templates, read integrations |
| **Viewer** | Read-only access to presentations and templates |

### Full Permission List

```
presentation:read, presentation:write, presentation:delete, presentation:export
template:read, template:write, template:delete
integration:read, integration:write, integration:manage
webhook:read, webhook:write, webhook:manage
workspace:read, workspace:write, workspace:delete
member:read, member:write, member:manage
```

## API Reference

### OIDC Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/oidc/status` | Current OIDC session status |
| `GET` | `/api/v1/oidc/login` | Start OIDC flow (redirects to IdP) |
| `GET` | `/api/v1/oidc/callback` | OIDC callback handler |
| `POST` | `/api/v1/oidc/logout` | End session + clear cookie |

### Workspace Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/projects` | List user's workspaces |
| `POST` | `/api/v1/projects` | Create workspace |
| `GET` | `/api/v1/projects/{id}` | Get workspace details |
| `PUT` | `/api/v1/projects/{id}` | Update workspace (owner/admin) |
| `DELETE` | `/api/v1/projects/{id}` | Delete workspace (owner only) |
| `GET` | `/api/v1/projects/{id}/members` | List workspace members |
| `POST` | `/api/v1/projects/{id}/members` | Add member (owner/admin) |
| `PUT` | `/api/v1/projects/{id}/members/{userId}` | Change member role |
| `DELETE` | `/api/v1/projects/{id}/members/{userId}` | Remove member |

## Database Migration

The Alembic migration (`5056b9c6c9cf`) is idempotent and runs automatically when `MIGRATE_DATABASE_ON_STARTUP=true` (default in Docker).

New tables:
- `users` — user accounts
- `oauth_accounts` — linked OIDC identities
- `roles` — role definitions (seeded with owner/admin/editor/viewer)
- `workspaces` — workspace/project records
- `workspace_members` — workspace membership with role

Modified existing tables:
- `presentations` + `workspace_id` (FK, nullable) + `created_by` (FK, nullable)
- `templates` + `workspace_id` (FK, nullable) + `created_by` (FK, nullable)

## Disabling OIDC

Set `OIDC_ENABLED=false` or remove the variable entirely. Presenton falls back to single-admin password authentication. All new tables remain in the database but are unused.

## Upstream Compatibility

All OIDC/workspace code lives in separate modules (`identity/`, `access_control/`, `workspaces/`). Core files have minimal changes (~30 lines total, all environment-gated). Merging upstream updates should be conflict-free in 90%+ of cases.

The files with merge risk:
- `api/main.py` (~4 lines added)
- `api/v1/auth/router.py` (~8 lines added)
- `api/middlewares.py` (0 lines changed — new middleware in separate file)
- `components/Auth/AuthGate.tsx` (~8 lines added)
- `proxy.ts` (~1 line added)
- `store/store.ts` (~2 lines added)

## Provider-Specific Notes

### Keycloak
```
OIDC_ISSUER=https://keycloak.example.com/realms/myrealm
```
Ensure the client has "Standard Flow" enabled and "Access Type" set to `public` (if no client secret) or `confidential`.

### Authentik
```
OIDC_ISSUER=https://authentik.example.com/application/o/presenton/
```
Create an OAuth2 provider with `authorization_code` grant type and PKCE enabled.

### Azure Entra ID
```
OIDC_ISSUER=https://login.microsoftonline.com/{tenant-id}/v2.0
```
Register as "Web" platform with the callback redirect URI.

### Authelia
```
OIDC_ISSUER=https://auth.example.com
```
Ensure `authorization_policy: two_factor` or adjusted as needed.
