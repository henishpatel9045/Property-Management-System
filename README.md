# PropertyMaps Rent Management System (RMS)

A robust, enterprise-grade Property Management System built with **Django**, **Bootstrap 5**, and **HTMX**. This application streamlines property operations for landlords and property managers, focusing on financial precision, automated tenant communication, and seamless document management.

## 🚀 Key Features

### 💎 Property & Tenant Management
- **Centralized Dashboard**: At-a-glance view of property health, lease statuses, and financial metrics.
- **Unified Tracking**: Manage multiple properties and tenants with ease, keeping all records in one place.

### 💰 Financial Intelligence
- **Automated Rent Ledger**: Precision tracking of rent obligations vs. actual payments.
- **"Waterfall" Payment Allocation**: Intelligent algorithm that automatically allocates payments to the oldest outstanding debts first, handling partial payments and overages seamlessly.
- **Bond & Settlement Management**: Automated calculation of bond deductions and final settlement reports at the end of a lease.

### 📂 Document Management (Google Drive Integration)
- **Nested Folder Hierarchy**: Automatic organization of documents in a `PropertyMaps > Property > Tenant` structure on Google Drive.
- **Bulk Uploads**: Support for multi-file uploads with real-time status updates using HTMX.
- **Synchronized State**: Deleting records in the app safely cleans up corresponding cloud storage folders.

### 📧 Automated Communications
- **Smart Reminders**: Cron-based background jobs that trigger personalized rent reminders based on grace periods and arrears status.
- **Professional Templates**: Clean, responsive email designs for all tenant interactions.

## 🛠️ Tech Stack

- **Backend**: Python / Django
- **Frontend**: Vanilla CSS, Bootstrap 5, HTMX (for interactive, SPA-like features)
- **Database**: SQLite (Development) / PostgreSQL (Production ready)
- **Cloud Integration**: Google Drive API v3
- **Task Scheduling**: Django Management Commands (compatible with system-level crontabs)

## 🏗️ Quick Start

### Prerequisites
- Python 3.10+
- Google Cloud Platform project with Drive API enabled and OAuth2 credentials.

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/henishpatel9045/Property-Management-System.git
   cd Property-Management-System
   ```

2. **Set up virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Environment Setup:**
   Create a `.env` file in the root directory (refer to `env.example`):
   ```env
   SECRET_KEY=your_secret_key
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   # Google OAuth Credentials
   GOOGLE_DRIVE_CLIENT_ID=your_id
   GOOGLE_DRIVE_CLIENT_SECRET=your_secret
   ```

4. **Initialize Database:**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

5. **Run the server:**
   ```bash
   python manage.py runserver
   ```

6. **Seed Data (Optional):**
   ```bash
   python seed_data.py
   ```

## 🛡️ Security

- **Environment Isolation**: All sensitive API keys and secrets are managed via `python-dotenv`.
- **OAuth 2.0**: Secure authentication for Google Drive integration.
- **Atomic Transactions**: Financial operations are wrapped in `transaction.atomic` to ensure data integrity.

---
*Created by [Henish Patel](https://www.instagram.com/henishpatel9045/)*
