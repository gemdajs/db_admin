
# Django DB Sync Tool

This project is a Django-based tool for synchronizing data between a local SQLite database and an external PostgreSQL database.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

- Python 3.x
- pip
- virtualenv

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd dbsync_tool
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

This project uses a `.env` file for environment variables. Create a `.env` file in the project root and add the following variables:

```
SECRET_KEY=your-secret-key
DEBUG=True

# External PostgreSQL Database
DB_NAME=your_db_name
DB_USERNAME=your_db_username
DB_PASSWORD=your_db_password
DB_HOST=your_db_host
DB_PORT=your_db_port

# Redis Cache
REDIS_URL=redis://localhost:6379
REDIS_PREFIX=dbsync

# Allowed Hosts
EXEMPTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
WHITELISTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
```

## Setup

1. **Run initial setup with migration and admin account setup:**
   ```bash
   python manage.py run_setup -u adminusername -e youremail@yourdomain.tld -p admin_password -f AdminFirstName -l AdminLastName
   ```

## Running the Application

Start the development server with the following command:

```bash
python manage.py runserver
```

The application will be available at `http://localhost:8000`.

## Project Structure

- `account/`: Handles user authentication and custom user model.
- `core/`: Contains the core Django project settings, configurations, and backends.
- `dbsync/`: Manages the database synchronization logic.
- `utils/`: Contains utility functions used across the project.

## Key Features

- **Database Administration:** Administer data from an external PostgreSQL database.
- **Custom User Model:** Implements a custom user model for authentication.

## Customizing the Admin Site

The admin site for external models is dynamically configured based on the `DBSyncModelColumn` model. To customize the admin interface for a specific model, you can create or update entries in the `DBSyncModelColumn` table.

Here's how you can customize the admin site for a model:

1.  **Navigate to the `DBSyncModelColumn` admin page:**
    - Go to `http://localhost:8000/admin/account/dbsyncmodelcolumn/`

2.  **Edit a `DBSyncModelColumn` entry:**
    - **In List Display List:** Check this to display the field in the model's list view.
    - **In List Filter List:** Check this to add a filter for this field in the sidebar.
    - **In Searchable List:** Check this to include this field in the search functionality.
    - **In Autocomplete List:** Check this if it's a foreign key to enable an autocomplete widget.

### Important Note

When a change is made to any of the DBSyncModelColumn entries, our intent is to reload the admin models to pick up the changes automatically. This however has not been working for all cases especially for list_display, autocomplete and list_filter.

In light of this, you may have to restart your application to ensure changes reflect properly. Changes would be maintained so far the model definition has not changed in your database. Every new columns entries added will eventually get removed upon sync.

## Dependencies

- Django
- django-dotenv
- django-redis
- gunicorn
- psycopg2-binary
- redis
