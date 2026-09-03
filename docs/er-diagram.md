# Database ER Diagram

This is the high-level entity relationship model for Syncora's tenant-isolated business data.

```mermaid
erDiagram
    User ||--o{ OrganizationMembership : has
    Organization ||--o{ OrganizationMembership : includes
    Organization ||--o{ Branch : owns
    Organization ||--o{ Customer : owns
    Organization ||--o{ Supplier : owns
    Organization ||--o{ ProductCategory : owns
    Organization ||--o{ Product : owns
    Organization ||--o{ InventoryStock : tracks
    Organization ||--o{ StockMovement : records
    Organization ||--o{ Purchase : owns
    Organization ||--o{ Sale : owns
    Organization ||--o{ Expense : owns
    Organization ||--o{ Notification : sends
    Organization ||--o{ ActivityLog : records
    Organization ||--o{ AuditLog : audits

    ProductCategory ||--o{ Product : categorizes
    Product ||--o{ ProductVariant : has
    Product ||--o{ InventoryStock : stocked_as
    ProductVariant ||--o{ InventoryStock : stocked_as

    Branch ||--o{ InventoryStock : holds
    Branch ||--o{ StockMovement : records
    Branch ||--o{ Purchase : receives
    Branch ||--o{ Sale : sells
    Branch ||--o{ Expense : spends

    Supplier ||--o{ Purchase : receives_orders
    Purchase ||--o{ PurchaseItem : contains
    Product ||--o{ PurchaseItem : purchased
    ProductVariant ||--o{ PurchaseItem : purchased

    Customer ||--o{ Sale : places
    Sale ||--o{ SaleItem : contains
    Sale ||--o{ Payment : receives
    Product ||--o{ SaleItem : sold
    ProductVariant ||--o{ SaleItem : sold

    ExpenseCategory ||--o{ Expense : categorizes
    User ||--o{ Sale : creates
    User ||--o{ Purchase : creates
    User ||--o{ Expense : creates
    User ||--o{ Payment : receives
    User ||--o{ Notification : receives
    User ||--o{ ActivityLog : performs
    User ||--o{ AuditLog : performs
```

## Relationship Notes

- `Organization` is the tenant boundary for all core business data.
- `OrganizationMembership` connects users to tenants and stores role/permission context.
- `Branch` scopes operational records such as inventory, purchases, sales, expenses, activities, and dashboards.
- `Product` is organization-level; `ProductVariant` supports SKU-level inventory, purchasing, and sales.
- `InventoryStock` stores current quantity while `StockMovement` records immutable quantity history.
- `Purchase` receiving creates stock increases and stock movement rows.
- `Sale` completion creates stock deductions, payment tracking, finance updates, activity logs, and realtime events.
- `AuditLog` is append-only and records sensitive security actions.
