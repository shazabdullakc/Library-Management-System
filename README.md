# Library Management System

A comprehensive desktop application for managing library operations, built with Python and Tkinter.

## Features

- **Book Management**

  - Add, edit, and remove books
  - Track multiple copies of books
  - Categorize books by genre
  - Search books by title, author, or ISBN
  - Track book availability status

- **Member Management**

  - Register new members
  - Update member information
  - Track membership status
  - Search members by name, email, or phone

- **Circulation Management**

  - Issue books to members
  - Process book returns
  - Calculate and collect fines for overdue books
  - Track due dates and overdue status

- **User Management**

  - Role-based access control (Admin, Librarian, Staff)
  - Secure login system
  - User activity tracking

- **Reporting**
  - Generate various reports:
    - Books inventory
    - Member statistics
    - Circulation history
    - Overdue books
    - Fine collection

## Requirements

```
ttkthemes>=3.2.2
Pillow>=10.0.0
```

## Database Structure

### Tables

1. **Categories**

   - category_id (INTEGER PRIMARY KEY)
   - category_name (TEXT UNIQUE)
   - description (TEXT)

2. **Books**

   - book_id (INTEGER PRIMARY KEY)
   - title (TEXT)
   - author (TEXT)
   - isbn (TEXT UNIQUE)
   - publisher (TEXT)
   - publication_year (INTEGER)
   - category_id (INTEGER FOREIGN KEY)
   - total_copies (INTEGER)
   - available_copies (INTEGER)
   - description (TEXT)
   - added_date (TIMESTAMP)
   - cover_image (TEXT)

3. **Members**

   - member_id (INTEGER PRIMARY KEY)
   - first_name (TEXT)
   - last_name (TEXT)
   - email (TEXT UNIQUE)
   - phone (TEXT)
   - address (TEXT)
   - join_date (TIMESTAMP)
   - membership_status (TEXT) - ['active', 'inactive', 'suspended']
   - profile_image (TEXT)

4. **Users**

   - user_id (INTEGER PRIMARY KEY)
   - username (TEXT UNIQUE)
   - password_hash (TEXT)
   - email (TEXT UNIQUE)
   - full_name (TEXT)
   - role (TEXT) - ['admin', 'librarian', 'staff']
   - created_date (TIMESTAMP)
   - last_login (TIMESTAMP)

5. **Book Issues**

   - issue_id (INTEGER PRIMARY KEY)
   - book_id (INTEGER FOREIGN KEY)
   - member_id (INTEGER FOREIGN KEY)
   - issue_date (TIMESTAMP)
   - due_date (TIMESTAMP)
   - return_date (TIMESTAMP)
   - fine_amount (DECIMAL)
   - status (TEXT) - ['issued', 'returned', 'overdue']
   - issued_by (INTEGER FOREIGN KEY)

6. **Fines**
   - fine_id (INTEGER PRIMARY KEY)
   - issue_id (INTEGER FOREIGN KEY)
   - amount (DECIMAL)
   - fine_date (TIMESTAMP)
   - payment_date (TIMESTAMP)
   - payment_status (TEXT) - ['paid', 'unpaid']

## Default Settings

- Default admin credentials:

  - Username: admin
  - Password: admin123

- Default book categories:
  - Fiction
  - Non-Fiction
  - Science
  - Technology
  - History
  - Philosophy
  - Arts
  - Self-Help

## Getting Started

1. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:

   ```bash
   python app.py
   ```

3. Log in using the default admin credentials

## Security Features

- Password hashing using SHA-256
- Role-based access control
- Session management
- Input validation and sanitization

## Features by User Role

### Admin

- Full system access
- User management
- System configuration
- All reports access

### Librarian

- Book management
- Member management
- Circulation management
- Basic reports access

### Staff

- Basic book operations
- Basic member operations
- Circulation desk operations
