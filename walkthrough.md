# Technical Walkthrough: PropertyMaps RMS Architecture

This document provides a deep dive into the engineering decisions, aggregation strategies, and feature implementations that power **PropertyMaps RMS**.

---

## 1. Rent Aggregation & Expectations Engine
The core of any property management system is the ability to predict future financial flow. 

### `RentObligation` Generation
Located in `finance/services.py`, the `generate_rent_obligations_for_lease` function acts as the "engine":
- **Frequency-Aware**: Supports `weekly`, `fortnightly`, and `monthly` cycles using `dateutil.relativedelta`.
- **Projection Horizon**: Generates expectations ahead of time (default 12 months) based on the lease `start_date`, ensuring the ledger is always ready for incoming payments.
- **Deduplication**: Checks for existing obligations before creation, allowing it to be run safely multiple times as a lease is updated.

---

## 2. The "Waterfall" Payment Allocation
Handling complex financial scenarios like partial payments, overpayments, and arrears requires a robust allocation strategy.

### `allocate_payment` Logic
When a payment is recorded, the system uses a **Waterfall Allocation** strategy:
1.  **Target Allocation**: If a user specifies a specific rent month, the payment is applied there first.
2.  **Chronological Overflow**: Any remaining balance is automatically "flowed" into the oldest outstanding `unpaid` or `partial` `RentObligation` records for that lease.
3.  **Real-Time Status Updates**: As allocations are created, the parent `RentObligation` status is dynamically updated (`unpaid` -> `partial` -> `paid`). 
4.  **Balance Tracking**: Any excess payment is saved as an `unallocated_balance`, which can be applied to future debts.

> [!NOTE]
> This strategy ensures that arrears are always cleared first, maintaining a clean ledger without manual intervention.

---

## 3. Managed Cloud Hierarchy (Google Drive API)
Rather than a flat file storage, PropertyMaps RMS enforces a strict organizational structure in the cloud.

### Folder Synchronization
The `gdrive_service.py` module manages the `PropertyMaps` root:
- **Nested Pathing**: `PropertyMaps > [Property Name] > [Tenant Name]`.
- **Lazy Folder Creation**: Folders are only created when needed (`_get_or_create_nested_folder`), ensuring a clean Drive environment.
- **Atomic Operations**: Deleting a lease or property in the app triggers a clean-up of the corresponding Google Drive folder using the `drive_file_id`.

### Feature Highlight: Bulk Uploads
Using **HTMX**, the file upload experience is seamless. Users can upload multiple files, and the app processes each sequentially, updating the UI without a full page reload.

---

## 4. Automated Workflow: Rent Reminders
The system bridges the gap between financial tracking and tenant communication.

### Cron-Based Triggering
A Django management command (`cron_generate_reminders.py`) runs as a scheduled task:
1.  **Arrears Discovery**: Scans `RentObligation` for records that are `unpaid` or `partial` and past their `due_date` (accounting for the `grace_period`).
2.  **Dynamic Emailing**: Generates personalized emails using `communications/email_service.py`, detailing the exact outstanding amount and property details.
3.  **Notification History**: Every email sent is logged in the database to prevent duplicate notifications and maintain a history of communication.

---

## 5. UI/UX: The "Interactivity" Layer
Despite being a server-side Django app, the interface feels modern and reactive.

### HTMX Implementation
HTMX is used to:
- **Refresh Dashboard Components**: Update financial graphs and tables without reloading.
- **Form Interactivity**: Dynamically calculate totals as users type in expense records.
- **Modals & Overlays**: Provide a smooth "SPA-like" experience for complex operations like "Finalize Settlement."

---

## 6. Bond & Settlement Lifecycle
At the end of a lease, the system automates the most complex part of property management: closing the books.

- **Bond Accounts**: Tracks security deposits separately.
- **Categorized Deductions**: Link outgoing expenses (like cleaning or maintenance) directly to the bond.
- **Final Reports**: Generates a reconciliation statement showing `Initial Bond - Deductions = Return Amount`.

---
*For more information on setting up the environment, see the [README.md](file:///d:/WORK/Rent%20Management%20System/README.md).*
