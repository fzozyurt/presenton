from enum import Enum


class Permission(str, Enum):
    PRESENTATION_READ = "presentation:read"
    PRESENTATION_WRITE = "presentation:write"
    PRESENTATION_DELETE = "presentation:delete"
    PRESENTATION_EXPORT = "presentation:export"

    TEMPLATE_READ = "template:read"
    TEMPLATE_WRITE = "template:write"
    TEMPLATE_DELETE = "template:delete"

    INTEGRATION_READ = "integration:read"
    INTEGRATION_WRITE = "integration:write"
    INTEGRATION_MANAGE = "integration:manage"

    WEBHOOK_READ = "webhook:read"
    WEBHOOK_WRITE = "webhook:write"
    WEBHOOK_MANAGE = "webhook:manage"

    WORKSPACE_READ = "workspace:read"
    WORKSPACE_WRITE = "workspace:write"
    WORKSPACE_DELETE = "workspace:delete"

    MEMBER_READ = "member:read"
    MEMBER_WRITE = "member:write"
    MEMBER_MANAGE = "member:manage"


ROLE_PERMISSIONS: dict[str, list[Permission]] = {
    "owner": [
        Permission.PRESENTATION_READ,
        Permission.PRESENTATION_WRITE,
        Permission.PRESENTATION_DELETE,
        Permission.PRESENTATION_EXPORT,
        Permission.TEMPLATE_READ,
        Permission.TEMPLATE_WRITE,
        Permission.TEMPLATE_DELETE,
        Permission.INTEGRATION_READ,
        Permission.INTEGRATION_WRITE,
        Permission.INTEGRATION_MANAGE,
        Permission.WEBHOOK_READ,
        Permission.WEBHOOK_WRITE,
        Permission.WEBHOOK_MANAGE,
        Permission.WORKSPACE_READ,
        Permission.WORKSPACE_WRITE,
        Permission.WORKSPACE_DELETE,
        Permission.MEMBER_READ,
        Permission.MEMBER_WRITE,
        Permission.MEMBER_MANAGE,
    ],
    "admin": [
        Permission.PRESENTATION_READ,
        Permission.PRESENTATION_WRITE,
        Permission.PRESENTATION_DELETE,
        Permission.PRESENTATION_EXPORT,
        Permission.TEMPLATE_READ,
        Permission.TEMPLATE_WRITE,
        Permission.TEMPLATE_DELETE,
        Permission.INTEGRATION_READ,
        Permission.INTEGRATION_WRITE,
        Permission.WEBHOOK_READ,
        Permission.WEBHOOK_WRITE,
        Permission.WORKSPACE_READ,
        Permission.WORKSPACE_WRITE,
        Permission.MEMBER_READ,
        Permission.MEMBER_WRITE,
    ],
    "editor": [
        Permission.PRESENTATION_READ,
        Permission.PRESENTATION_WRITE,
        Permission.PRESENTATION_EXPORT,
        Permission.TEMPLATE_READ,
        Permission.TEMPLATE_WRITE,
        Permission.INTEGRATION_READ,
        Permission.WEBHOOK_READ,
        Permission.WORKSPACE_READ,
        Permission.MEMBER_READ,
    ],
    "viewer": [
        Permission.PRESENTATION_READ,
        Permission.TEMPLATE_READ,
        Permission.WORKSPACE_READ,
        Permission.MEMBER_READ,
    ],
}


def has_permission(role: str, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    perms = ROLE_PERMISSIONS.get(role, [])
    return permission in perms


def get_role_permissions(role: str) -> list[Permission]:
    """Get all permissions for a given role."""
    return ROLE_PERMISSIONS.get(role, [])
