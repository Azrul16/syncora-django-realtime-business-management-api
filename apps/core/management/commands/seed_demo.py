from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.branches.models import Branch
from apps.customers.models import Customer
from apps.expenses.models import Expense, ExpenseCategory
from apps.inventory.models import InventoryStock, StockMovement
from apps.notifications.models import ActivityLog, AuditLog, Notification
from apps.organizations.models import Organization, OrganizationMembership
from apps.products.models import Product, ProductCategory, ProductVariant
from apps.purchases.models import Purchase, PurchaseItem
from apps.sales.models import Payment, Sale, SaleItem
from apps.suppliers.models import Supplier


class Command(BaseCommand):
    help = 'Seed Syncora with portfolio-friendly demo business data.'

    def add_arguments(self, parser):
        parser.add_argument('--products', type=int, default=100)
        parser.add_argument('--customers', type=int, default=300)
        parser.add_argument('--suppliers', type=int, default=20)
        parser.add_argument('--sales', type=int, default=120)
        parser.add_argument('--purchases', type=int, default=40)
        parser.add_argument('--expenses', type=int, default=50)

    @transaction.atomic
    def handle(self, *args, **options):
        owner = self.ensure_user('owner@demo.syncora.local', 'Demo', 'Owner')
        organization, _ = Organization.objects.get_or_create(
            name='Demo Electronics Ltd.',
            defaults={
                'email': 'hello@demo.syncora.local',
                'phone': '01700000000',
                'address': 'Dhaka, Bangladesh',
            },
        )
        OrganizationMembership.objects.get_or_create(
            user=owner,
            organization=organization,
            defaults={'role': OrganizationMembership.Role.OWNER},
        )

        branches = self.ensure_branches(organization)
        self.ensure_team(organization, branches)
        categories = self.ensure_categories(organization)
        products, variants = self.ensure_products(organization, categories, owner, options['products'])
        suppliers = self.ensure_suppliers(organization, owner, options['suppliers'])
        customers = self.ensure_customers(organization, owner, options['customers'])
        expenses = self.ensure_expenses(organization, branches, owner, options['expenses'])
        self.ensure_inventory(organization, branches, products, variants, owner)
        purchases = self.ensure_purchases(organization, branches, suppliers, products, owner, options['purchases'])
        sales = self.ensure_sales(organization, branches, customers, products, owner, options['sales'])
        self.ensure_notifications(organization, owner, sales, purchases, expenses)

        self.stdout.write(self.style.SUCCESS('Demo data ready.'))
        self.stdout.write(f'Organization: {organization.name} (id={organization.id})')
        self.stdout.write('Demo login: owner@demo.syncora.local / demo-pass-1234')

    def ensure_user(self, email, first_name, last_name):
        user, created = get_user_model().objects.get_or_create(
            email=email,
            defaults={'first_name': first_name, 'last_name': last_name, 'is_staff': email.startswith('owner@')},
        )
        if created or not user.has_usable_password():
            user.set_password('demo-pass-1234')
            user.save(update_fields=['password'])
        return user

    def ensure_branches(self, organization):
        branch_specs = [
            ('Dhaka', 'DHK', 'Dhaka, Bangladesh'),
            ('Khulna', 'KHL', 'Khulna, Bangladesh'),
            ('Barishal', 'BAR', 'Barishal, Bangladesh'),
        ]
        return [
            Branch.objects.get_or_create(
                organization=organization,
                name=name,
                defaults={'code': code, 'address': address, 'phone': f'0170000000{index}'},
            )[0]
            for index, (name, code, address) in enumerate(branch_specs, start=1)
        ]

    def ensure_team(self, organization, branches):
        roles = [
            ('admin@demo.syncora.local', 'Admin', OrganizationMembership.Role.ADMIN, []),
            ('manager@demo.syncora.local', 'Manager', OrganizationMembership.Role.MANAGER, []),
            ('sales@demo.syncora.local', 'Sales', OrganizationMembership.Role.SALES, [branches[0]]),
            ('inventory@demo.syncora.local', 'Inventory', OrganizationMembership.Role.INVENTORY_MANAGER, branches[:2]),
            ('accountant@demo.syncora.local', 'Accountant', OrganizationMembership.Role.ACCOUNTANT, []),
            ('employee1@demo.syncora.local', 'Employee', OrganizationMembership.Role.EMPLOYEE, [branches[0]]),
            ('employee2@demo.syncora.local', 'Employee', OrganizationMembership.Role.EMPLOYEE, [branches[1]]),
            ('employee3@demo.syncora.local', 'Employee', OrganizationMembership.Role.EMPLOYEE, [branches[2]]),
        ]
        for email, first_name, role, assigned_branches in roles:
            user = self.ensure_user(email, first_name, 'Demo')
            membership, _ = OrganizationMembership.objects.get_or_create(
                user=user,
                organization=organization,
                defaults={'role': role},
            )
            membership.role = role
            membership.is_active = True
            membership.save(update_fields=['role', 'is_active'])
            if assigned_branches:
                membership.branches.set(assigned_branches)

    def ensure_categories(self, organization):
        names = ['Phones', 'Laptops', 'Accessories', 'Audio', 'Cameras', 'Networking', 'Storage', 'Displays', 'Gaming', 'Office']
        return [
            ProductCategory.objects.get_or_create(organization=organization, name=name)[0]
            for name in names
        ]

    def ensure_products(self, organization, categories, owner, count):
        products = []
        variants = []
        for index in range(1, count + 1):
            category = categories[index % len(categories)]
            product, _ = Product.objects.get_or_create(
                organization=organization,
                sku=f'DEMO-SKU-{index:04d}',
                defaults={
                    'category': category,
                    'name': f'Demo Product {index:04d}',
                    'brand': ['Nexa', 'Orbit', 'Pulse', 'Core'][index % 4],
                    'unit': 'pcs',
                    'cost_price': '4500.00',
                    'selling_price': '6500.00',
                    'created_by': owner,
                },
            )
            products.append(product)
            for variant_name in ['Standard', 'Premium']:
                variant, _ = ProductVariant.objects.get_or_create(
                    product=product,
                    sku=f'{product.sku}-{variant_name.upper()}',
                    defaults={
                        'name': variant_name,
                        'cost_price': product.cost_price,
                        'selling_price': product.selling_price,
                    },
                )
                variants.append(variant)
        return products, variants

    def ensure_suppliers(self, organization, owner, count):
        return [
            Supplier.objects.get_or_create(
                organization=organization,
                name=f'Demo Supplier {index:02d}',
                defaults={
                    'contact_person': f'Supplier Contact {index:02d}',
                    'email': f'supplier{index:02d}@demo.syncora.local',
                    'phone': f'0180000{index:04d}',
                    'created_by': owner,
                },
            )[0]
            for index in range(1, count + 1)
        ]

    def ensure_customers(self, organization, owner, count):
        return [
            Customer.objects.get_or_create(
                organization=organization,
                customer_code=f'DCUST-{index:04d}',
                defaults={
                    'name': f'Demo Customer {index:04d}',
                    'email': f'customer{index:04d}@demo.syncora.local',
                    'phone': f'0190000{index:04d}',
                    'created_by': owner,
                },
            )[0]
            for index in range(1, count + 1)
        ]

    def ensure_inventory(self, organization, branches, products, variants, owner):
        for index, product in enumerate(products):
            branch = branches[index % len(branches)]
            stock, _ = InventoryStock.objects.get_or_create(
                organization=organization,
                branch=branch,
                product=product,
                product_variant=None,
                defaults={'quantity': '75.00', 'reorder_level': '10.00', 'updated_by': owner},
            )
            StockMovement.objects.get_or_create(
                organization=organization,
                branch=branch,
                product=product,
                product_variant=None,
                movement_type=StockMovement.MovementType.OPENING_STOCK,
                reference=f'DEMO-OPEN-{product.sku}',
                defaults={
                    'quantity': stock.quantity,
                    'previous_quantity': '0.00',
                    'new_quantity': stock.quantity,
                    'note': 'Demo opening stock.',
                    'created_by': owner,
                },
            )
        for index, variant in enumerate(variants[: min(len(variants), 150)]):
            branch = branches[index % len(branches)]
            InventoryStock.objects.get_or_create(
                organization=organization,
                branch=branch,
                product=variant.product,
                product_variant=variant,
                defaults={'quantity': '25.00', 'reorder_level': '5.00', 'updated_by': owner},
            )

    def ensure_purchases(self, organization, branches, suppliers, products, owner, count):
        purchases = []
        for index in range(1, count + 1):
            purchase, _ = Purchase.objects.get_or_create(
                organization=organization,
                reference=f'DEMO-PO-{index:04d}',
                defaults={
                    'branch': branches[index % len(branches)],
                    'supplier': suppliers[index % len(suppliers)],
                    'status': Purchase.Status.RECEIVED,
                    'order_date': date(2026, 9, min((index % 28) + 1, 28)),
                    'created_by': owner,
                    'received_at': timezone.now(),
                },
            )
            PurchaseItem.objects.get_or_create(
                purchase=purchase,
                product=products[index % len(products)],
                defaults={'quantity': '10.00', 'unit_cost': '4500.00'},
            )
            purchase.recalculate_totals()
            purchases.append(purchase)
        return purchases

    def ensure_sales(self, organization, branches, customers, products, owner, count):
        sales = []
        for index in range(1, count + 1):
            sale, _ = Sale.objects.get_or_create(
                organization=organization,
                reference=f'DEMO-SO-{index:04d}',
                defaults={
                    'branch': branches[index % len(branches)],
                    'customer': customers[index % len(customers)],
                    'status': Sale.Status.COMPLETED,
                    'sale_date': date(2026, 9, min((index % 28) + 1, 28)),
                    'created_by': owner,
                    'completed_at': timezone.now(),
                },
            )
            SaleItem.objects.get_or_create(
                sale=sale,
                product=products[index % len(products)],
                defaults={'quantity': '2.00', 'unit_cost': '4500.00', 'unit_price': '6500.00'},
            )
            sale.recalculate_totals()
            Payment.objects.get_or_create(
                sale=sale,
                reference_number=f'DEMO-PAY-{index:04d}',
                defaults={'amount': sale.grand_total.quantize(Decimal('0.01')), 'received_by': owner},
            )
            sales.append(sale)
        return sales

    def ensure_expenses(self, organization, branches, owner, count):
        category, _ = ExpenseCategory.objects.get_or_create(organization=organization, name='Demo Operations')
        expenses = []
        for index in range(1, count + 1):
            expense, _ = Expense.objects.get_or_create(
                organization=organization,
                reference=f'DEMO-EXP-{index:04d}',
                defaults={
                    'branch': branches[index % len(branches)],
                    'category': category,
                    'title': f'Demo Expense {index:03d}',
                    'amount': '2500.00',
                    'expense_date': date(2026, 9, min((index % 28) + 1, 28)),
                    'status': Expense.Status.APPROVED,
                    'created_by': owner,
                    'approved_by': owner,
                },
            )
            expenses.append(expense)
        return expenses

    def ensure_notifications(self, organization, owner, sales, purchases, expenses):
        Notification.objects.get_or_create(
            organization=organization,
            recipient=owner,
            type='demo.ready',
            title='Demo data ready',
            defaults={'message': 'Syncora demo records are available for local testing.'},
        )
        ActivityLog.objects.get_or_create(
            organization=organization,
            actor=owner,
            action='demo.seeded',
            resource_type='Organization',
            resource_id=str(organization.id),
            defaults={'description': 'Demo data was seeded.', 'metadata': {'sales': len(sales), 'purchases': len(purchases), 'expenses': len(expenses)}},
        )
        AuditLog.objects.get_or_create(
            organization=organization,
            actor=owner,
            action='demo.seeded',
            target_type='Organization',
            target_id=str(organization.id),
            defaults={'metadata': {'source': 'seed_demo'}},
        )
