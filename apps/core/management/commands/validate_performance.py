from datetime import date
from time import perf_counter

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils.text import slugify
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.branches.models import Branch
from apps.customers.models import Customer
from apps.inventory.models import InventoryStock
from apps.organizations.models import Organization, OrganizationMembership
from apps.products.models import Product
from apps.sales.models import Sale, SaleItem


class Command(BaseCommand):
    help = 'Seed a benchmark tenant and measure representative API endpoints.'

    def add_arguments(self, parser):
        parser.add_argument('--products', type=int, default=100)
        parser.add_argument('--customers', type=int, default=100)
        parser.add_argument('--sales', type=int, default=200)
        parser.add_argument('--page-size', type=int, default=20)

    def handle(self, *args, **options):
        user = self.get_user()
        organization = self.get_organization(user)
        branches = self.ensure_branches(organization)
        products = self.ensure_products(organization, options['products'])
        customers = self.ensure_customers(organization, options['customers'])
        self.ensure_inventory(organization, branches, products)
        self.ensure_sales(organization, branches, products, customers, options['sales'], user)

        client = APIClient()
        client.force_authenticate(user)
        endpoints = [
            ('products', f'/api/v1/products/?page_size={options["page_size"]}'),
            ('inventory', f'/api/v1/inventory/?page_size={options["page_size"]}'),
            ('sales', f'/api/v1/sales/?page_size={options["page_size"]}'),
            ('dashboard_summary', f'/api/v1/dashboard/summary/?organization={organization.id}'),
            ('dashboard_top_products', f'/api/v1/dashboard/top-products/?organization={organization.id}'),
        ]

        self.stdout.write('endpoint,status,queries,duration_ms,response_bytes')
        for name, path in endpoints:
            with CaptureQueriesContext(connection) as queries:
                started = perf_counter()
                response = client.get(path, HTTP_HOST='127.0.0.1')
                duration_ms = round((perf_counter() - started) * 1000, 2)
            response_bytes = len(getattr(response, 'rendered_content', response.content))
            self.stdout.write(
                f'{name},{response.status_code},{len(queries)},{duration_ms},{response_bytes}'
            )

    def get_user(self):
        user, _ = get_user_model().objects.get_or_create(
            email='performance@syncora.local',
            defaults={'first_name': 'Performance', 'last_name': 'Runner'},
        )
        if not user.has_usable_password():
            user.set_password('performance-pass-1234')
            user.save(update_fields=['password'])
        return user

    def get_organization(self, user):
        organization, _ = Organization.objects.get_or_create(name='Performance Validation Org')
        OrganizationMembership.objects.get_or_create(
            user=user,
            organization=organization,
            defaults={'role': OrganizationMembership.Role.OWNER},
        )
        return organization

    def ensure_branches(self, organization):
        return [
            Branch.objects.get_or_create(
                organization=organization,
                name=f'Performance Branch {index}',
                defaults={'code': f'P{index}'},
            )[0]
            for index in range(1, 6)
        ]

    def ensure_products(self, organization, count):
        existing = Product.objects.filter(organization=organization).count()
        if existing < count:
            Product.objects.bulk_create(
                Product(
                    organization=organization,
                    name=f'Performance Product {index}',
                    slug=slugify(f'Performance Product {index}'),
                    sku=f'PERF-{index}',
                    cost_price='40.00',
                    selling_price='100.00',
                )
                for index in range(existing + 1, count + 1)
            )
        return list(Product.objects.filter(organization=organization).order_by('id')[:count])

    def ensure_customers(self, organization, count):
        existing = Customer.objects.filter(organization=organization).count()
        if existing < count:
            Customer.objects.bulk_create(
                Customer(
                    organization=organization,
                    name=f'Performance Customer {index}',
                    customer_code=f'PCUST-{index}',
                )
                for index in range(existing + 1, count + 1)
            )
        return list(Customer.objects.filter(organization=organization).order_by('id')[:count])

    def ensure_inventory(self, organization, branches, products):
        existing_keys = set(
            InventoryStock.objects.filter(
                organization=organization,
                product__in=products,
            ).values_list('branch_id', 'product_id')
        )
        InventoryStock.objects.bulk_create(
            InventoryStock(
                organization=organization,
                branch=branch,
                product=product,
                quantity='100.00',
                reorder_level='10.00',
            )
            for index, product in enumerate(products)
            for branch in [branches[index % len(branches)]]
            if (branch.id, product.id) not in existing_keys
        )

    def ensure_sales(self, organization, branches, products, customers, count, user):
        existing = Sale.objects.filter(organization=organization).count()
        if existing >= count:
            return
        sales = Sale.objects.bulk_create(
            Sale(
                organization=organization,
                branch=branches[index % len(branches)],
                customer=customers[index % len(customers)],
                status=Sale.Status.COMPLETED,
                sale_date=date(2026, 9, 3),
                created_by=user,
                subtotal='100.00',
                grand_total='100.00',
            )
            for index in range(existing, count)
        )
        SaleItem.objects.bulk_create(
            SaleItem(
                sale=sale,
                product=products[index % len(products)],
                quantity='1.00',
                unit_price='100.00',
                unit_cost='40.00',
            )
            for index, sale in enumerate(sales, start=existing)
        )
