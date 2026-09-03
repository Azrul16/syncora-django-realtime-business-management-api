# System Architecture

Syncora is organized around a tenant-isolated Django backend with REST APIs, WebSocket updates, transactional service logic, and PostgreSQL persistence.

## Backend Flow

```mermaid
flowchart TD
    Client[Client Applications] --> REST[REST API]
    Client --> WS[WebSocket Clients]

    REST --> DRF[Django REST Framework]
    WS --> Channels[Django Channels]

    DRF --> Auth[Authentication]
    Auth --> Throttle[Throttling]
    Throttle --> Permissions[RBAC and Object Permissions]
    Permissions --> Validation[Serializer Validation]

    Validation --> Services[Service Layer]
    Channels --> SocketAuth[JWT WebSocket Auth]
    SocketAuth --> Groups[Organization and Branch Groups]

    Services --> Transactions[Atomic Transactions and Row Locks]
    Transactions --> Database[(PostgreSQL)]

    Services --> EventDispatcher[Event Dispatcher]
    EventDispatcher --> Activity[Activity Logs]
    EventDispatcher --> Notifications[Notifications]
    EventDispatcher --> Broadcasts[WebSocket Broadcasts]
    EventDispatcher --> Dashboard[Dashboard Refresh Events]

    Activity --> Database
    Notifications --> Database
    Broadcasts --> Groups
    Dashboard --> Groups
```

## Business Modules

```mermaid
flowchart LR
    Org[Organization] --> Branches[Branches]
    Org --> RBAC[Memberships and Roles]
    Org --> Products[Products and Variants]
    Org --> Suppliers[Suppliers]
    Org --> Customers[Customers]
    Org --> Inventory[Inventory]
    Org --> Purchases[Purchases]
    Org --> Sales[Sales]
    Org --> Expenses[Expenses]
    Org --> Finance[Finance Analytics]
    Org --> Notifications[Notifications and Activity]

    Purchases --> InventoryIncrease[Stock Increase]
    Sales --> InventoryDecrease[Stock Deduction]
    Sales --> Payments[Payments]
    Expenses --> Approvals[Approval Workflow]

    InventoryIncrease --> Finance
    InventoryDecrease --> Finance
    Payments --> Finance
    Approvals --> Finance
```

## Multi-Tenant Isolation

```mermaid
flowchart TD
    Syncora[Syncora Backend] --> CompanyA[Company A]
    Syncora --> CompanyB[Company B]
    Syncora --> CompanyC[Company C]

    CompanyA --> DataA[Isolated Organization Data]
    CompanyB --> DataB[Isolated Organization Data]
    CompanyC --> DataC[Isolated Organization Data]

    DataA --> BranchA[Branch-Scoped Access]
    DataB --> BranchB[Branch-Scoped Access]
    DataC --> BranchC[Branch-Scoped Access]

    BranchA --> RolesA[Role Permissions]
    BranchB --> RolesB[Role Permissions]
    BranchC --> RolesC[Role Permissions]
```

## Production Shape

```mermaid
flowchart TD
    Internet[Internet] --> Proxy[Nginx or Platform Router]
    Proxy --> ASGI[Daphne ASGI Server]
    ASGI --> Django[Django Application]
    Django --> REST[REST API]
    Django --> WebSockets[WebSockets]
    Django --> Postgres[(PostgreSQL)]
    Django --> Static[Static Files]

    WebSockets -. future scale .-> Redis[(Redis Channel Layer)]
```
