from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Organization(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class OrganizationMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = 'OWNER', 'Owner'
        ADMIN = 'ADMIN', 'Admin'
        MANAGER = 'MANAGER', 'Manager'
        SALES = 'SALES', 'Sales'
        INVENTORY_MANAGER = 'INVENTORY_MANAGER', 'Inventory manager'
        ACCOUNTANT = 'ACCOUNTANT', 'Accountant'
        EMPLOYEE = 'EMPLOYEE', 'Employee'

    class Permission:
        USERS_MANAGE = 'users.manage'
        BRANCHES_MANAGE = 'branches.manage'
        PRODUCTS_VIEW = 'products.view'
        PRODUCTS_MANAGE = 'products.manage'
        INVENTORY_VIEW = 'inventory.view'
        INVENTORY_ADJUST = 'inventory.adjust'
        PURCHASES_CREATE = 'purchases.create'
        PURCHASES_RECEIVE = 'purchases.receive'
        SALES_CREATE = 'sales.create'
        SALES_COMPLETE = 'sales.complete'
        PAYMENTS_CREATE = 'payments.create'
        EXPENSES_CREATE = 'expenses.create'
        EXPENSES_APPROVE = 'expenses.approve'
        REPORTS_VIEW = 'reports.view'
        FINANCE_VIEW = 'finance.view'

    ROLE_PERMISSIONS = {
        Role.OWNER: {
            Permission.USERS_MANAGE,
            Permission.BRANCHES_MANAGE,
            Permission.PRODUCTS_VIEW,
            Permission.PRODUCTS_MANAGE,
            Permission.INVENTORY_VIEW,
            Permission.INVENTORY_ADJUST,
            Permission.PURCHASES_CREATE,
            Permission.PURCHASES_RECEIVE,
            Permission.SALES_CREATE,
            Permission.SALES_COMPLETE,
            Permission.PAYMENTS_CREATE,
            Permission.EXPENSES_CREATE,
            Permission.EXPENSES_APPROVE,
            Permission.REPORTS_VIEW,
            Permission.FINANCE_VIEW,
        },
        Role.ADMIN: {
            Permission.USERS_MANAGE,
            Permission.BRANCHES_MANAGE,
            Permission.PRODUCTS_VIEW,
            Permission.PRODUCTS_MANAGE,
            Permission.INVENTORY_VIEW,
            Permission.INVENTORY_ADJUST,
            Permission.PURCHASES_CREATE,
            Permission.PURCHASES_RECEIVE,
            Permission.SALES_CREATE,
            Permission.SALES_COMPLETE,
            Permission.PAYMENTS_CREATE,
            Permission.EXPENSES_CREATE,
            Permission.EXPENSES_APPROVE,
            Permission.REPORTS_VIEW,
            Permission.FINANCE_VIEW,
        },
        Role.MANAGER: {
            Permission.PRODUCTS_VIEW,
            Permission.PRODUCTS_MANAGE,
            Permission.INVENTORY_VIEW,
            Permission.INVENTORY_ADJUST,
            Permission.PURCHASES_CREATE,
            Permission.PURCHASES_RECEIVE,
            Permission.SALES_CREATE,
            Permission.SALES_COMPLETE,
            Permission.PAYMENTS_CREATE,
            Permission.EXPENSES_CREATE,
            Permission.EXPENSES_APPROVE,
            Permission.REPORTS_VIEW,
            Permission.FINANCE_VIEW,
        },
        Role.SALES: {
            Permission.PRODUCTS_VIEW,
            Permission.INVENTORY_VIEW,
            Permission.SALES_CREATE,
            Permission.SALES_COMPLETE,
            Permission.PAYMENTS_CREATE,
        },
        Role.INVENTORY_MANAGER: {
            Permission.PRODUCTS_VIEW,
            Permission.PRODUCTS_MANAGE,
            Permission.INVENTORY_VIEW,
            Permission.INVENTORY_ADJUST,
            Permission.PURCHASES_CREATE,
            Permission.PURCHASES_RECEIVE,
        },
        Role.ACCOUNTANT: {
            Permission.PRODUCTS_VIEW,
            Permission.EXPENSES_CREATE,
            Permission.EXPENSES_APPROVE,
            Permission.REPORTS_VIEW,
            Permission.FINANCE_VIEW,
        },
        Role.EMPLOYEE: {
            Permission.PRODUCTS_VIEW,
            Permission.INVENTORY_VIEW,
            Permission.EXPENSES_CREATE,
        },
    }

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='organization_memberships',
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    branches = models.ManyToManyField(
        'branches.Branch',
        related_name='memberships',
        blank=True,
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['organization', 'user']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'organization'],
                name='unique_user_organization_membership',
            ),
        ]

    @property
    def is_owner(self):
        return self.role == self.Role.OWNER

    @property
    def is_admin(self):
        return self.role in {self.Role.OWNER, self.Role.ADMIN}

    @property
    def is_manager(self):
        return self.role in {self.Role.OWNER, self.Role.ADMIN, self.Role.MANAGER}

    def has_permission(self, permission):
        return permission in self.ROLE_PERMISSIONS.get(self.role, set())

    @property
    def permissions(self):
        return sorted(self.ROLE_PERMISSIONS.get(self.role, set()))

    @property
    def has_all_branch_access(self):
        return self.is_admin or not self.branches.exists()

    def __str__(self):
        return f'{self.user} - {self.organization} ({self.role})'
