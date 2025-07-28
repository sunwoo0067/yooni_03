"""
Initialize RBAC system with default permissions and roles
Run this script after creating the database tables
"""
import asyncio
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.rbac import (
    Permission, Role, PermissionCategory, PermissionAction, ResourceScope,
    DROPSHIPPING_PERMISSIONS, DROPSHIPPING_ROLES
)
from app.models.user import User, UserRole
from app.core.security import SecurityManager


def create_default_permissions(db: Session) -> dict:
    """Create default permissions for dropshipping platform"""
    print("Creating default permissions...")
    
    created_permissions = {}
    permission_count = 0
    
    for perm_data in DROPSHIPPING_PERMISSIONS:
        name, display_name, category, action, resource_type, scope = perm_data
        
        # Check if permission already exists
        existing = db.query(Permission).filter(Permission.name == name).first()
        if existing:
            print(f"Permission '{name}' already exists, skipping...")
            created_permissions[name] = existing
            continue
        
        # Create new permission
        permission = Permission(
            name=name,
            display_name=display_name,
            category=category,
            action=action,
            resource_type=resource_type,
            scope=scope,
            is_system_permission=True,
            is_active=True,
            priority=0
        )
        
        db.add(permission)
        created_permissions[name] = permission
        permission_count += 1
        print(f"Created permission: {name}")
    
    db.flush()  # Ensure permissions are created before roles
    print(f"Created {permission_count} new permissions")
    return created_permissions


def create_default_roles(db: Session, permissions: dict) -> dict:
    """Create default roles with permissions"""
    print("\nCreating default roles...")
    
    created_roles = {}
    role_count = 0
    
    for role_name, role_config in DROPSHIPPING_ROLES.items():
        # Check if role already exists
        existing = db.query(Role).filter(Role.name == role_name).first()
        if existing:
            print(f"Role '{role_name}' already exists, skipping...")
            created_roles[role_name] = existing
            continue
        
        # Create new role
        role = Role(
            name=role_name,
            display_name=role_config["display_name"],
            description=role_config["description"],
            level=role_config["level"],
            is_system_role=True,
            is_active=True
        )
        
        # Add permissions to role
        role_permissions = []
        if role_config["permissions"] == ["*"]:
            # Super admin gets all permissions
            role_permissions = list(permissions.values())
            print(f"Granting ALL permissions to role '{role_name}'")
        else:
            # Add specific permissions
            for perm_name in role_config["permissions"]:
                if perm_name in permissions:
                    role_permissions.append(permissions[perm_name])
                else:
                    print(f"Warning: Permission '{perm_name}' not found for role '{role_name}'")
        
        role.permissions = role_permissions
        db.add(role)
        created_roles[role_name] = role
        role_count += 1
        print(f"Created role: {role_name} with {len(role_permissions)} permissions")
    
    print(f"Created {role_count} new roles")
    return created_roles


def create_default_admin_user(db: Session) -> User:
    """Create default admin user if none exists"""
    print("\nChecking for admin users...")
    
    # Check if any super admin users exist
    admin_exists = db.query(User).filter(User.role == UserRole.SUPER_ADMIN).first()
    if admin_exists:
        print(f"Admin user already exists: {admin_exists.username}")
        return admin_exists
    
    # Create default admin user
    default_password = "admin123!@#"  # Change this in production!
    
    admin_user = User(
        username="admin",
        email="admin@dropship.local",
        full_name="System Administrator",
        hashed_password=SecurityManager.get_password_hash(default_password),
        role=UserRole.SUPER_ADMIN,
        is_active=True,
        is_verified=True,
        department="Administration"
    )
    
    db.add(admin_user)
    print(f"Created default admin user: {admin_user.username}")
    print(f"Default password: {default_password}")
    print("⚠️  IMPORTANT: Change the default password after first login!")
    
    return admin_user


def verify_rbac_setup(db: Session):
    """Verify that RBAC system is properly set up"""
    print("\n" + "="*50)
    print("RBAC SYSTEM VERIFICATION")
    print("="*50)
    
    # Count permissions
    total_permissions = db.query(Permission).count()
    active_permissions = db.query(Permission).filter(Permission.is_active == True).count()
    system_permissions = db.query(Permission).filter(Permission.is_system_permission == True).count()
    
    print(f"Total Permissions: {total_permissions}")
    print(f"Active Permissions: {active_permissions}")
    print(f"System Permissions: {system_permissions}")
    
    # Count roles
    total_roles = db.query(Role).count()
    active_roles = db.query(Role).filter(Role.is_active == True).count()
    system_roles = db.query(Role).filter(Role.is_system_role == True).count()
    
    print(f"Total Roles: {total_roles}")
    print(f"Active Roles: {active_roles}")
    print(f"System Roles: {system_roles}")
    
    # Count users by role
    print("\nUsers by Role:")
    for role in UserRole:
        count = db.query(User).filter(User.role == role).count()
        print(f"  {role.value}: {count}")
    
    # Show permission categories
    print("\nPermission Categories:")
    for category in PermissionCategory:
        count = db.query(Permission).filter(Permission.category == category).count()
        print(f"  {category.value}: {count}")
    
    print("\n✅ RBAC System initialized successfully!")


def main():
    """Main initialization function"""
    print("="*60)
    print("DROPSHIPPING PLATFORM RBAC INITIALIZATION")
    print("="*60)
    
    try:
        # Create database session
        db = SessionLocal()
        
        # Create default permissions
        permissions = create_default_permissions(db)
        
        # Create default roles
        roles = create_default_roles(db, permissions)
        
        # Create default admin user
        admin_user = create_default_admin_user(db)
        
        # Commit all changes
        db.commit()
        print("\n✅ All changes committed to database")
        
        # Verify setup
        verify_rbac_setup(db)
        
        # Show important security notes
        print("\n" + "⚠️ "*10)
        print("SECURITY REMINDERS:")
        print("⚠️ "*10)
        print("1. Change the default admin password immediately")
        print("2. Review and customize permissions as needed")
        print("3. Create additional users with appropriate roles")
        print("4. Enable audit logging in production")
        print("5. Regularly review user permissions and access logs")
        print("⚠️ "*10)
        
    except Exception as e:
        print(f"❌ Error during RBAC initialization: {str(e)}")
        if db:
            db.rollback()
        raise
    finally:
        if db:
            db.close()


if __name__ == "__main__":
    main()