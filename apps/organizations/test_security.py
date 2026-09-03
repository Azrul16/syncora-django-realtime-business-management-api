from datetime import date

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.branches.models import Branch
from apps.customers.models import Customer
from apps.expenses.models import Expense, ExpenseCategory
from apps.inventory.models import InventoryStock
from apps.notifications.models import AuditLog
from apps.products.models import Product
from apps.sales.models import Sale, SaleItem

from .models import Organization, OrganizationMembership


@override_settings(DISABLE_AUTH_FOR_LOCAL_DEV=False)
class SecurityPermissionTests(APITestCase):
    def setUp(self):
        self.password = 'test-pass-1234'
        self.owner = self.create_user('security-owner@example.com')
        self.manager = self.create_user('security-manager@example.com')
        self.sales_user = self.create_user('security-sales@example.com')
        self.employee = self.create_user('security-employee@example.com')
        self.accountant = self.create_user('security-accountant@example.com')
        self.outsider = self.create_user('security-outsider@example.com')

        self.organization = Organization.objects.create(name='Security Org')
        self.branch = Branch.objects.create(organization=self.organization, name='Dhaka')
        self.other_branch = Branch.objects.create(organization=self.organization, name='Khulna')
        self.customer = Customer.objects.create(organization=self.organization, name='Security Customer')
        self.category = ExpenseCategory.objects.create(organization=self.organization, name='Travel')
        self.product = Product.objects.create(
            organization=self.organization,
            name='Security Product',
            sku='SEC-PROD-1',
            cost_price='50.00',
            selling_price='100.00',
        )

        OrganizationMembership.objects.create(
            user=self.owner,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )
        OrganizationMembership.objects.create(
            user=self.manager,
            organization=self.organization,
            role=OrganizationMembership.Role.MANAGER,
        )
        OrganizationMembership.objects.create(
            user=self.sales_user,
            organization=self.organization,
            role=OrganizationMembership.Role.SALES,
        )
        OrganizationMembership.objects.create(
            user=self.employee,
            organization=self.organization,
            role=OrganizationMembership.Role.EMPLOYEE,
        )
        OrganizationMembership.objects.create(
            user=self.accountant,
            organization=self.organization,
            role=OrganizationMembership.Role.ACCOUNTANT,
        )

    def create_user(self, email):
        return get_user_model().objects.create_user(email=email, password=self.password)

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def sale_payload(self, branch=None):
        return {
            'branch': (branch or self.branch).id,
            'customer': self.customer.id,
            'items': [
                {
                    'product': self.product.id,
                    'quantity': '1.00',
                    'unit_price': '100.00',
                }
            ],
        }

    def test_unauthenticated_requests_are_rejected(self):
        response = self.client.get('/api/v1/organizations/')

        self.assertIn(response.status_code, {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN})
        self.assertIn('error', response.data)
        self.assertIn('code', response.data['error'])

    def test_role_permissions_allow_sales_but_block_expense_approval(self):
        expense = Expense.objects.create(
            organization=self.organization,
            branch=self.branch,
            category=self.category,
            title='Needs Approval',
            amount='500.00',
            expense_date=date(2026, 9, 3),
            created_by=self.employee,
        )
        self.authenticate(self.sales_user)

        sale_response = self.client.post('/api/v1/sales/', self.sale_payload(), format='json')
        approval_response = self.client.post(f'/api/v1/expenses/{expense.id}/approve/')

        self.assertEqual(sale_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(approval_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(approval_response.data['error']['code'], 'PERMISSION_DENIED')

    def test_accountant_can_view_finance_and_approve_expense(self):
        expense = Expense.objects.create(
            organization=self.organization,
            branch=self.branch,
            category=self.category,
            title='Approve Me',
            amount='250.00',
            expense_date=date(2026, 9, 3),
            created_by=self.employee,
        )
        self.authenticate(self.accountant)

        finance_response = self.client.get(f'/api/v1/finance/summary/?organization={self.organization.id}')
        approval_response = self.client.post(f'/api/v1/expenses/{expense.id}/approve/')

        self.assertEqual(finance_response.status_code, status.HTTP_200_OK)
        self.assertEqual(approval_response.status_code, status.HTTP_200_OK)

    def test_employee_cannot_view_dashboard_reports(self):
        self.authenticate(self.employee)

        response = self.client.get(f'/api/v1/dashboard/summary/?organization={self.organization.id}')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_branch_restricted_user_gets_only_assigned_branch_data(self):
        membership = OrganizationMembership.objects.get(user=self.manager, organization=self.organization)
        membership.branches.set([self.branch])
        self.create_completed_sale(self.branch, '100.00')
        self.create_completed_sale(self.other_branch, '900.00')
        self.authenticate(self.manager)

        list_response = self.client.get('/api/v1/sales/')
        dashboard_response = self.client.get(f'/api/v1/dashboard/summary/?organization={self.organization.id}')
        hidden_branch_response = self.client.get(
            f'/api/v1/dashboard/summary/?organization={self.organization.id}&branch={self.other_branch.id}'
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data['count'], 1)
        self.assertEqual(dashboard_response.data['today']['revenue'], '100.00')
        self.assertEqual(hidden_branch_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cross_tenant_detail_returns_not_found(self):
        other_org = Organization.objects.create(name='Other Security Org')
        other_branch = Branch.objects.create(organization=other_org, name='Other Branch')
        other_sale = Sale.objects.create(organization=other_org, branch=other_branch)
        self.authenticate(self.owner)

        response = self.client.get(f'/api/v1/sales/{other_sale.id}/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_request_validation_rejects_negative_stock_quantity(self):
        self.authenticate(self.owner)

        response = self.client.post(
            '/api/v1/inventory/',
            {
                'branch': self.branch.id,
                'product': self.product.id,
                'quantity': '-1.00',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error']['code'], 'VALIDATION_ERROR')

    def test_soft_deleted_branch_is_hidden_from_lists(self):
        self.authenticate(self.owner)

        delete_response = self.client.delete(f'/api/v1/branches/{self.other_branch.id}/')
        list_response = self.client.get('/api/v1/branches/')

        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.other_branch.refresh_from_db()
        self.assertTrue(self.other_branch.is_deleted)
        self.assertEqual(list_response.data['count'], 1)

    def test_member_role_change_creates_audit_log(self):
        membership = OrganizationMembership.objects.get(user=self.employee, organization=self.organization)
        self.authenticate(self.owner)

        response = self.client.patch(
            f'/api/v1/organizations/{self.organization.id}/members/{membership.id}/',
            {'role': OrganizationMembership.Role.MANAGER},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.organization,
                actor=self.owner,
                action='role.changed',
                target_id=str(self.employee.id),
            ).exists()
        )

    def test_request_id_is_returned_and_saved_on_audit_log(self):
        self.authenticate(self.owner)

        response = self.client.post(
            '/api/v1/auth/change-password/',
            {
                'current_password': self.password,
                'new_password': 'new-test-pass-1234',
            },
            format='json',
            HTTP_X_REQUEST_ID='req-security-test',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['X-Request-ID'], 'req-security-test')
        self.assertTrue(
            AuditLog.objects.filter(
                actor=self.owner,
                action='password.changed',
                request_id='req-security-test',
            ).exists()
        )

    def create_completed_sale(self, branch, amount):
        sale = Sale.objects.create(
            organization=self.organization,
            branch=branch,
            customer=self.customer,
            status=Sale.Status.COMPLETED,
            sale_date=date(2026, 9, 3),
            created_by=self.owner,
        )
        SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity='1.00',
            unit_price=amount,
            unit_cost='50.00',
        )
        sale.recalculate_totals()
        return sale
