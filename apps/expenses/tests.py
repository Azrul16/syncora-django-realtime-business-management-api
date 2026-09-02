from datetime import date

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.branches.models import Branch
from apps.organizations.models import Organization, OrganizationMembership

from .models import Expense, ExpenseCategory


class ExpenseAPITests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='expense-owner@example.com',
            password='test-pass-1234',
        )
        self.organization = Organization.objects.create(name='Expense Org')
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )
        self.branch = Branch.objects.create(organization=self.organization, name='Dhaka')
        self.category = ExpenseCategory.objects.create(organization=self.organization, name='Rent')

    def authenticate(self, user=None):
        self.client.force_authenticate(user=user or self.user)

    def create_user(self, email):
        return get_user_model().objects.create_user(email=email, password='test-pass-1234')

    def test_manager_can_create_expense(self):
        manager = self.create_user('expense-manager@example.com')
        OrganizationMembership.objects.create(
            user=manager,
            organization=self.organization,
            role=OrganizationMembership.Role.MANAGER,
        )
        self.authenticate(manager)

        response = self.client.post(
            '/api/v1/expenses/',
            {
                'organization': self.organization.id,
                'branch': self.branch.id,
                'category': self.category.id,
                'title': 'Office Rent',
                'amount': '15000.00',
                'expense_date': date.today().isoformat(),
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        expense = Expense.objects.get(title='Office Rent')
        self.assertRegex(expense.expense_number, r'^EXP-\d{6}$')
        self.assertEqual(expense.status, Expense.Status.DRAFT)
        self.assertEqual(expense.created_by, manager)

    def test_employee_can_read_and_create_draft_expense(self):
        employee = self.create_user('expense-employee@example.com')
        OrganizationMembership.objects.create(
            user=employee,
            organization=self.organization,
            role=OrganizationMembership.Role.EMPLOYEE,
        )
        Expense.objects.create(
            organization=self.organization,
            branch=self.branch,
            title='Visible Expense',
            amount='100.00',
            expense_date=date.today(),
        )
        self.authenticate(employee)

        list_response = self.client.get('/api/v1/expenses/')
        create_response = self.client.post(
            '/api/v1/expenses/',
            {
                'organization': self.organization.id,
                'category': self.category.id,
                'title': 'Blocked Expense',
                'amount': '100.00',
                'expense_date': date.today().isoformat(),
            },
            format='json',
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data['count'], 1)
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_response.data['status'], Expense.Status.DRAFT)

    def test_manager_can_approve_expense(self):
        manager = self.create_user('expense-approver@example.com')
        OrganizationMembership.objects.create(
            user=manager,
            organization=self.organization,
            role=OrganizationMembership.Role.MANAGER,
        )
        expense = Expense.objects.create(
            organization=self.organization,
            branch=self.branch,
            category=self.category,
            title='Approval Expense',
            amount='100.00',
            expense_date=date.today(),
            created_by=self.user,
        )
        self.authenticate(manager)

        response = self.client.post(f'/api/v1/expenses/{expense.id}/approve/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], Expense.Status.APPROVED)
        expense.refresh_from_db()
        self.assertEqual(expense.approved_by, manager)

    def test_employee_cannot_approve_expense(self):
        employee = self.create_user('expense-employee-approver@example.com')
        OrganizationMembership.objects.create(
            user=employee,
            organization=self.organization,
            role=OrganizationMembership.Role.EMPLOYEE,
        )
        expense = Expense.objects.create(
            organization=self.organization,
            branch=self.branch,
            category=self.category,
            title='Blocked Approval',
            amount='100.00',
            expense_date=date.today(),
            created_by=employee,
        )
        self.authenticate(employee)

        response = self.client.post(f'/api/v1/expenses/{expense.id}/approve/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
