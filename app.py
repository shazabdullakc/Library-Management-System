import tkinter as tk
from tkinter import ttk, messagebox, filedialog, Tk
import sqlite3
from datetime import datetime, timedelta
from ttkthemes import ThemedTk
from PIL import Image, ImageTk
import os
import re
import hashlib
import random
import csv
from config import config

class LibraryManagementSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("Library Management System")
        self.root.geometry("1200x700")
        self.root.minsize(1200, 700)
        
        # Initialize connection
        self.conn = None
        
        # Database Connection
        if not self.db_connection():
            messagebox.showerror("Error", "Could not connect to database. Please check your database configuration in database.ini")
            self.root.destroy()
            return
            
        # Variables
        self.selected_book_id = None
        self.selected_member_id = None
        self.selected_issue_id = None
        self.selected_category_id = None
        self.current_user = None
        self.is_admin = False
        
        # Load Colors and Styles
        self.primary_color = "#2c3e50"
        self.secondary_color = "#3498db"
        self.accent_color = "#e74c3c"
        self.bg_color = "#ecf0f1"
        self.text_color = "#2c3e50"
        
        # Configure Styles
        style = ttk.Style()
        style.configure("TFrame", background=self.bg_color)
        style.configure("TLabel", background=self.bg_color, foreground=self.text_color, font=("Helvetica", 11))
        style.configure("TButton", 
            background=self.secondary_color, 
            foreground="black",  # Changed to black for better visibility
            font=("Helvetica", 11, "bold"),  # Made font bold
            relief="raised",  # Added relief
            padding=(10, 5))  # Added padding
        style.configure("Header.TLabel", font=("Helvetica", 16, "bold"), background=self.bg_color, foreground=self.primary_color)
        style.configure("Title.TLabel", font=("Helvetica", 24, "bold"), background=self.primary_color, foreground="white")
        style.configure("Sidebar.TFrame", background=self.primary_color)
        style.configure("Sidebar.TButton", font=("Helvetica", 12), background=self.primary_color, foreground="white")
        style.configure("Accent.TButton", background=self.accent_color)
        
        # Update button mappings for better interaction feedback
        style.map("TButton",
            foreground=[('active', 'black'), ('pressed', 'black')],
            background=[('active', '#4ea5e0'), ('pressed', '#2980b9')])
        style.map("Accent.TButton",
            foreground=[('active', 'black'), ('pressed', 'black')],
            background=[('active', '#e74c3c'), ('pressed', '#c0392b')])
            
        # Display Login Frame
        self.show_login_frame()
    
    def db_connection(self):
        try:
            # Get database configuration
            params = config()
            
            # Connect to SQLite database (it will be created if it doesn't exist)
            self.conn = sqlite3.connect(params['database'])
            self.conn.row_factory = sqlite3.Row  # This allows accessing columns by name
            
            # Create tables
            self.create_tables()
            return True
            
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Could not connect to database: {e}")
            return False
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
            return False
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Create Categories Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT NOT NULL UNIQUE,
            description TEXT
        )
        """)
        
        # Create Books Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            book_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            isbn TEXT UNIQUE,
            publisher TEXT,
            publication_year INTEGER,
            category_id INTEGER,
            total_copies INTEGER DEFAULT 1,
            available_copies INTEGER DEFAULT 1,
            description TEXT,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cover_image TEXT,
            FOREIGN KEY (category_id) REFERENCES categories(category_id)
        )
        """)
        
        # Create Members Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS members (
            member_id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            address TEXT,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            membership_status TEXT CHECK(membership_status IN ('active', 'inactive', 'suspended')) DEFAULT 'active',
            profile_image TEXT
        )
        """)
        
        # Create Users Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT CHECK(role IN ('admin', 'librarian', 'staff')) NOT NULL,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
        """)
        
        # Create Book Issues Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS book_issues (
            issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            issue_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            due_date TIMESTAMP NOT NULL,
            return_date TIMESTAMP,
            fine_amount DECIMAL(10,2) DEFAULT 0.00,
            status TEXT CHECK(status IN ('issued', 'returned', 'overdue')) DEFAULT 'issued',
            issued_by INTEGER,
            FOREIGN KEY (book_id) REFERENCES books(book_id),
            FOREIGN KEY (member_id) REFERENCES members(member_id),
            FOREIGN KEY (issued_by) REFERENCES users(user_id)
        )
        """)
        
        # Create Fines Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS fines (
            fine_id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_id INTEGER NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            fine_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            payment_date TIMESTAMP,
            payment_status TEXT CHECK(payment_status IN ('paid', 'unpaid')) DEFAULT 'unpaid',
            FOREIGN KEY (issue_id) REFERENCES book_issues(issue_id)
        )
        """)
        
        # Create default admin user if none exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = cursor.fetchone()[0]
        
        if admin_count == 0:
            # Hash the password 'admin123'
            password_hash = hashlib.sha256('admin123'.encode()).hexdigest()
            
            cursor.execute("""
            INSERT INTO users (username, password_hash, email, full_name, role)
            VALUES (?, ?, ?, ?, ?)
            """, ('admin', password_hash, 'admin@library.com', 'System Administrator', 'admin'))
        
        # Create some default categories if none exist
        cursor.execute("SELECT COUNT(*) FROM categories")
        category_count = cursor.fetchone()[0]
        
        if category_count == 0:
            default_categories = [
                ("Fiction", "Novels, short stories, and other fictional works"),
                ("Non-Fiction", "Factual books on various subjects"),
                ("Science", "Books related to scientific fields"),
                ("Technology", "Books about technology and computers"),
                ("History", "Historical books and biographies"),
                ("Philosophy", "Books on philosophical thoughts and ideas"),
                ("Arts", "Books related to various forms of art"),
                ("Self-Help", "Books focused on personal development")
            ]
            
            cursor.executemany("""
            INSERT INTO categories (category_name, description)
            VALUES (?, ?)
            """, default_categories)
        
        self.conn.commit()
        cursor.close()

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not username or not password:
            messagebox.showerror("Login Error", "Please enter both username and password")
            return
        
        # Hash the password for comparison
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
            SELECT * FROM users 
            WHERE username = ? AND password_hash = ?
            """, (username, password_hash))
            
            user = cursor.fetchone()
            cursor.close()
            
            if user:
                self.current_user = dict(user)  # Convert Row to dict for SQLite
                self.is_admin = (user['role'] == 'admin')
                
                # Update last login time
                cursor = self.conn.cursor()
                cursor.execute("""
                UPDATE users SET last_login = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """, (user['user_id'],))
                self.conn.commit()
                cursor.close()
                
                # Show main dashboard
                self.show_dashboard()
            else:
                messagebox.showerror("Login Error", "Invalid username or password")
        except sqlite3.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")

    def save_member(self, first_name, last_name, email, phone, address, status, window):
        if not first_name or not last_name or not email:
            messagebox.showerror("Input Error", "First Name, Last Name and Email are required fields")
            return
        
        # Validate email format
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            messagebox.showerror("Input Error", "Please enter a valid email address")
            return
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
            INSERT INTO members (first_name, last_name, email, phone, address, membership_status)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (first_name, last_name, email, phone, address.strip(), status))
            self.conn.commit()
            cursor.close()
            
            # Refresh the members table
            self.load_members()
            
            # Close the window
            window.destroy()
            
            messagebox.showinfo("Success", "Member added successfully!")
        except sqlite3.IntegrityError:
            messagebox.showerror("Database Error", "A member with this email already exists")
        except sqlite3.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")

    def load_books(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
            SELECT b.book_id, b.title, b.author, b.isbn, c.category_name, 
                   b.total_copies, b.available_copies, b.publication_year
            FROM books b
            LEFT JOIN categories c ON b.category_id = c.category_id
            ORDER BY b.title
            """)
            
            books = cursor.fetchall()
            cursor.close()
            
            # Clear existing data
            for item in self.books_table.get_children():
                self.books_table.delete(item)
            
            # Insert new data
            for book in books:
                self.books_table.insert("", tk.END, values=(
                    book['book_id'],
                    book['title'],
                    book['author'],
                    book['isbn'] if book['isbn'] else "",
                    book['category_name'] if book['category_name'] else "",
                    book['total_copies'],
                    book['available_copies'],
                    book['publication_year'] if book['publication_year'] else ""
                ))
        except sqlite3.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")

    def search_books(self):
        search_term = self.book_search_entry.get().strip()
        
        if not search_term:
            self.load_books()  # If search is empty, load all books
            return
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
            SELECT b.book_id, b.title, b.author, b.isbn, c.category_name, 
                   b.total_copies, b.available_copies, b.publication_year
            FROM books b
            LEFT JOIN categories c ON b.category_id = c.category_id
            WHERE b.title LIKE ? OR b.author LIKE ? OR b.isbn LIKE ?
            ORDER BY b.title
            """, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
            
            books = cursor.fetchall()
            cursor.close()
            
            # Clear existing data
            for item in self.books_table.get_children():
                self.books_table.delete(item)
            
            # Insert new data
            for book in books:
                self.books_table.insert("", tk.END, values=(
                    book['book_id'],
                    book['title'],
                    book['author'],
                    book['isbn'] if book['isbn'] else "",
                    book['category_name'] if book['category_name'] else "",
                    book['total_copies'],
                    book['available_copies'],
                    book['publication_year'] if book['publication_year'] else ""
                ))
        except sqlite3.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")

    def load_members(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
            SELECT member_id, first_name, last_name, email, phone, membership_status, join_date
            FROM members
            ORDER BY first_name, last_name
            """)
            
            members = cursor.fetchall()
            cursor.close()
            
            # Clear existing data
            for item in self.members_table.get_children():
                self.members_table.delete(item)
            
            # Insert new data
            for member in members:
                self.members_table.insert("", tk.END, values=(
                    member['member_id'],
                    f"{member['first_name']} {member['last_name']}",
                    member['email'],
                    member['phone'] if member['phone'] else "",
                    member['membership_status'].capitalize(),
                    datetime.strptime(member['join_date'], '%Y-%m-%d %H:%M:%S').strftime("%Y-%m-%d")
                ))
        except sqlite3.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")

    def search_members(self):
        search_term = self.member_search_entry.get().strip()
        
        if not search_term:
            self.load_members()  # If search is empty, load all members
            return
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
            SELECT member_id, first_name, last_name, email, phone, membership_status, join_date
            FROM members
            WHERE first_name LIKE ? OR last_name LIKE ? OR email LIKE ? OR phone LIKE ?
            ORDER BY first_name, last_name
            """, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
            
            members = cursor.fetchall()
            cursor.close()
            
            # Clear existing data
            for item in self.members_table.get_children():
                self.members_table.delete(item)
            
            # Insert new data
            for member in members:
                self.members_table.insert("", tk.END, values=(
                    member['member_id'],
                    f"{member['first_name']} {member['last_name']}",
                    member['email'],
                    member['phone'] if member['phone'] else "",
                    member['membership_status'].capitalize(),
                    datetime.strptime(member['join_date'], '%Y-%m-%d %H:%M:%S').strftime("%Y-%m-%d")
                ))
        except sqlite3.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")

    def update_member(self, member_id, first_name, last_name, email, phone, address, status, window):
        if not first_name or not last_name or not email:
            messagebox.showerror("Input Error", "First Name, Last Name and Email are required fields")
            return
        
        # Validate email format
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            messagebox.showerror("Input Error", "Please enter a valid email address")
            return
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
            UPDATE members
            SET first_name = ?, last_name = ?, email = ?, phone = ?, 
                address = ?, membership_status = ?
            WHERE member_id = ?
            """, (first_name, last_name, email, phone, address.strip(), status, member_id))
            self.conn.commit()
            cursor.close()
            
            # Refresh the members table
            self.load_members()
            
            # Close the window
            window.destroy()
            
            messagebox.showinfo("Success", "Member updated successfully!")
        except sqlite3.IntegrityError:
            messagebox.showerror("Database Error", "A member with this email already exists")
        except sqlite3.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")

    def delete_selected_member(self):
        if not self.selected_member_id:
            messagebox.showerror("Selection Error", "Please select a member to delete")
            return
        
        # Confirm deletion
        confirm = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this member?")
        if not confirm:
            return
        
        try:
            # Check if member has any active book issues
            cursor = self.conn.cursor()
            cursor.execute("""
            SELECT COUNT(*) FROM book_issues
            WHERE member_id = ? AND status IN ('issued', 'overdue')
            """, (self.selected_member_id,))
            
            result = cursor.fetchone()[0]
            
            if result > 0:
                messagebox.showerror("Delete Error", "Cannot delete member who has books issued")
                cursor.close()
                return
            
            # Delete member from database
            cursor.execute("DELETE FROM members WHERE member_id = ?", (self.selected_member_id,))
            self.conn.commit()
            cursor.close()
            
            # Refresh the members table
            self.load_members()
            
            # Reset selection
            self.selected_member_id = None
            
            messagebox.showinfo("Success", "Member deleted successfully!")
        except sqlite3.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")

    def save_book(self, title, author, isbn, publisher, year, category, copies, description, window):
        if not title or not author:
            messagebox.showerror("Input Error", "Title and Author are required fields")
            return
        
        try:
            # Get category_id from category_name
            category_id = None
            if category:
                cursor = self.conn.cursor()
                cursor.execute("SELECT category_id FROM categories WHERE category_name = ?", (category,))
                result = cursor.fetchone()
                if result:
                    category_id = result[0]
                cursor.close()
            
            # Validate year and copies
            pub_year = None
            if year:
                try:
                    pub_year = int(year)
                except ValueError:
                    messagebox.showerror("Input Error", "Publication Year must be a number")
                    return
            
            total_copies = 1
            if copies:
                try:
                    total_copies = int(copies)
                    if total_copies < 1:
                        raise ValueError("Total copies must be at least 1")
                except ValueError:
                    messagebox.showerror("Input Error", "Total Copies must be a positive number")
                    return
            
            # Insert book into database
            cursor = self.conn.cursor()
            cursor.execute("""
            INSERT INTO books (title, author, isbn, publisher, publication_year, category_id, 
                              total_copies, available_copies, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                title, author, isbn, publisher, pub_year, category_id, 
                total_copies, total_copies, description.strip()
            ))
            self.conn.commit()
            cursor.close()
            
            # Refresh the books table
            self.load_books()
            
            # Close the window
            window.destroy()
            
            messagebox.showinfo("Success", "Book added successfully!")
        except sqlite3.IntegrityError:
            messagebox.showerror("Database Error", "A book with this ISBN already exists")
        except sqlite3.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")
            
    def get_categories(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT category_id, category_name FROM categories ORDER BY category_name")
            categories = cursor.fetchall()
            cursor.close()
            return [dict(category) for category in categories]
        except sqlite3.Error:
            return []

    def show_login_frame(self):
        # Clear root window
        for widget in self.root.winfo_children():
            widget.destroy()
            
        # Create main frame
        login_frame = ttk.Frame(self.root, style="TFrame", padding="20")
        login_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Title
        title_label = ttk.Label(login_frame, text="Library Management System", style="Header.TLabel")
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Username
        username_label = ttk.Label(login_frame, text="Username:", style="TLabel")
        username_label.grid(row=1, column=0, sticky="e", padx=(0, 10), pady=5)
        self.username_entry = ttk.Entry(login_frame)
        self.username_entry.grid(row=1, column=1, pady=5)
        
        # Password
        password_label = ttk.Label(login_frame, text="Password:", style="TLabel")
        password_label.grid(row=2, column=0, sticky="e", padx=(0, 10), pady=5)
        self.password_entry = ttk.Entry(login_frame, show="*")
        self.password_entry.grid(row=2, column=1, pady=5)
        
        # Login button
        login_button = ttk.Button(login_frame, text="Login", command=self.login)
        login_button.grid(row=3, column=0, columnspan=2, pady=(20, 0))
        
        # Bind Enter key to login
        self.username_entry.bind('<Return>', lambda e: self.password_entry.focus())
        self.password_entry.bind('<Return>', lambda e: self.login())
        
        # Set focus to username entry
        self.username_entry.focus()

    def show_dashboard(self):
        # Clear root window
        for widget in self.root.winfo_children():
            widget.destroy()
            
        # Create main menu frame
        main_menu = ttk.Frame(self.root, style="TFrame")
        main_menu.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Welcome message
        welcome_label = ttk.Label(main_menu, 
                                text=f"Welcome, {self.current_user['full_name']}",
                                style="Header.TLabel")
        welcome_label.pack(pady=(0, 20))
        
        # Create button frame
        button_frame = ttk.Frame(main_menu, style="TFrame")
        button_frame.pack(expand=True)
        
        # Add menu buttons
        ttk.Button(button_frame, text="Manage Books", 
                  command=lambda: self.show_books_management()).pack(pady=10)
        ttk.Button(button_frame, text="Manage Members", 
                  command=lambda: self.show_members_management()).pack(pady=10)
        ttk.Button(button_frame, text="Issue/Return Books", 
                  command=lambda: self.show_book_circulation()).pack(pady=10)
        
        if self.is_admin:
            ttk.Button(button_frame, text="User Management", 
                      command=lambda: self.show_user_management()).pack(pady=10)
        
        ttk.Button(button_frame, text="Reports", 
                  command=lambda: self.show_reports()).pack(pady=10)
        ttk.Button(button_frame, text="Logout", 
                  command=lambda: self.show_login_frame()).pack(pady=10)

    def show_books_management(self):
        # Clear root window
        for widget in self.root.winfo_children():
            widget.destroy()
            
        # Create main frame
        main_frame = ttk.Frame(self.root, style="TFrame")
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text="Books Management", style="Header.TLabel")
        title_label.pack(pady=(0, 20))
        
        # Search frame
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        
        self.book_search_entry = ttk.Entry(search_frame)
        self.book_search_entry.pack(side="left", padx=(0, 10))
        
        ttk.Button(search_frame, text="Search", 
                  command=self.search_books).pack(side="left")
        
        ttk.Button(search_frame, text="Add New Book", 
                  command=self.show_add_book_dialog).pack(side="right")
        
        # Create Treeview
        columns = ("ID", "Title", "Author", "ISBN", "Category", "Total", "Available", "Year")
        self.books_table = ttk.Treeview(main_frame, columns=columns, show="headings")
        
        # Set column headings
        for col in columns:
            self.books_table.heading(col, text=col)
            self.books_table.column(col, width=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.books_table.yview)
        self.books_table.configure(yscrollcommand=scrollbar.set)
        
        # Pack table and scrollbar
        self.books_table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Load books data
        self.load_books()
        
        # Back button
        ttk.Button(main_frame, text="Back to Dashboard", 
                  command=self.show_dashboard).pack(pady=10)

    def show_add_book_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Book")
        dialog.geometry("400x600")
        dialog.grab_set()
        
        # Create and pack widgets
        ttk.Label(dialog, text="Title:").pack(pady=5)
        title_entry = ttk.Entry(dialog)
        title_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Author:").pack(pady=5)
        author_entry = ttk.Entry(dialog)
        author_entry.pack(pady=5)
        
        ttk.Label(dialog, text="ISBN:").pack(pady=5)
        isbn_entry = ttk.Entry(dialog)
        isbn_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Publisher:").pack(pady=5)
        publisher_entry = ttk.Entry(dialog)
        publisher_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Publication Year:").pack(pady=5)
        year_entry = ttk.Entry(dialog)
        year_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Category:").pack(pady=5)
        categories = [cat['category_name'] for cat in self.get_categories()]
        category_var = tk.StringVar(dialog)
        category_combo = ttk.Combobox(dialog, textvariable=category_var, values=categories)
        category_combo.pack(pady=5)
        
        ttk.Label(dialog, text="Number of Copies:").pack(pady=5)
        copies_entry = ttk.Entry(dialog)
        copies_entry.insert(0, "1")
        copies_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Description:").pack(pady=5)
        description_text = tk.Text(dialog, height=4, width=40)
        description_text.pack(pady=5)
        
        # Save button
        ttk.Button(dialog, text="Save", 
                  command=lambda: self.save_book(
                      title_entry.get(),
                      author_entry.get(),
                      isbn_entry.get(),
                      publisher_entry.get(),
                      year_entry.get(),
                      category_var.get(),
                      copies_entry.get(),
                      description_text.get("1.0", tk.END),
                      dialog
                  )).pack(pady=10)

    def show_members_management(self):
        # Clear root window
        for widget in self.root.winfo_children():
            widget.destroy()
            
        # Create main frame
        main_frame = ttk.Frame(self.root, style="TFrame")
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text="Members Management", style="Header.TLabel")
        title_label.pack(pady=(0, 20))
        
        # Search frame
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        
        self.member_search_entry = ttk.Entry(search_frame)
        self.member_search_entry.pack(side="left", padx=(0, 10))
        
        ttk.Button(search_frame, text="Search", 
                  command=self.search_members).pack(side="left")
        
        ttk.Button(search_frame, text="Add New Member", 
                  command=self.show_add_member_dialog).pack(side="right")
        
        # Create Treeview
        columns = ("ID", "Name", "Email", "Phone", "Status", "Join Date")
        self.members_table = ttk.Treeview(main_frame, columns=columns, show="headings")
        
        # Set column headings
        for col in columns:
            self.members_table.heading(col, text=col)
            self.members_table.column(col, width=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.members_table.yview)
        self.members_table.configure(yscrollcommand=scrollbar.set)
        
        # Pack table and scrollbar
        self.members_table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Load members data
        self.load_members()
        
        # Back button
        ttk.Button(main_frame, text="Back to Dashboard", 
                  command=self.show_dashboard).pack(pady=10)

    def show_book_circulation(self):
        # Clear root window
        for widget in self.root.winfo_children():
            widget.destroy()
            
        # Create main frame
        main_frame = ttk.Frame(self.root, style="TFrame")
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text="Book Circulation", style="Header.TLabel")
        title_label.pack(pady=(0, 20))
        
        # Create button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Issue Book", 
                  command=self.show_issue_book_dialog).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Return Book", 
                  command=self.show_return_book_dialog).pack(side="left", padx=5)
        
        # Create Treeview for current issues
        columns = ("Issue ID", "Book Title", "Member Name", "Issue Date", "Due Date", "Status")
        self.issues_table = ttk.Treeview(main_frame, columns=columns, show="headings")
        
        # Set column headings
        for col in columns:
            self.issues_table.heading(col, text=col)
            self.issues_table.column(col, width=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.issues_table.yview)
        self.issues_table.configure(yscrollcommand=scrollbar.set)
        
        # Pack table and scrollbar
        self.issues_table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Load current issues
        self.load_current_issues()
        
        # Back button
        ttk.Button(main_frame, text="Back to Dashboard", 
                  command=self.show_dashboard).pack(pady=10)

    def show_user_management(self):
        if not self.is_admin:
            messagebox.showerror("Access Denied", "Only administrators can access user management")
            return
            
        # Clear root window
        for widget in self.root.winfo_children():
            widget.destroy()
            
        # Create main frame
        main_frame = ttk.Frame(self.root, style="TFrame")
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text="User Management", style="Header.TLabel")
        title_label.pack(pady=(0, 20))
        
        # Add User button
        ttk.Button(main_frame, text="Add New User", 
                  command=self.show_add_user_dialog).pack(pady=10)
        
        # Create Treeview
        columns = ("ID", "Username", "Full Name", "Email", "Role", "Last Login")
        self.users_table = ttk.Treeview(main_frame, columns=columns, show="headings")
        
        # Set column headings
        for col in columns:
            self.users_table.heading(col, text=col)
            self.users_table.column(col, width=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.users_table.yview)
        self.users_table.configure(yscrollcommand=scrollbar.set)
        
        # Pack table and scrollbar
        self.users_table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Load users
        self.load_users()
        
        # Back button
        ttk.Button(main_frame, text="Back to Dashboard", 
                  command=self.show_dashboard).pack(pady=10)
    
    def show_reports(self):
        # Clear root window
        for widget in self.root.winfo_children():
            widget.destroy()
            
        # Create main frame
        main_frame = ttk.Frame(self.root, style="TFrame")
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text="Reports", style="Header.TLabel")
        title_label.pack(pady=(0, 20))
        
        # Create reports buttons frame
        reports_frame = ttk.Frame(main_frame)
        reports_frame.pack(expand=True)
        
        # Add report buttons
        ttk.Button(reports_frame, text="Books Report", 
                  command=lambda: self.generate_report("books")).pack(pady=5)
        ttk.Button(reports_frame, text="Members Report", 
                  command=lambda: self.generate_report("members")).pack(pady=5)
        ttk.Button(reports_frame, text="Circulation Report", 
                  command=lambda: self.generate_report("circulation")).pack(pady=5)
        ttk.Button(reports_frame, text="Overdue Books Report", 
                  command=lambda: self.generate_report("overdue")).pack(pady=5)
        ttk.Button(reports_frame, text="Fine Collection Report", 
                  command=lambda: self.generate_report("fines")).pack(pady=5)
        
        # Back button
        ttk.Button(main_frame, text="Back to Dashboard", 
                  command=self.show_dashboard).pack(pady=10)

    def show_issue_book_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Issue Book")
        dialog.geometry("400x500")
        dialog.grab_set()
        
        # Create and pack widgets
        ttk.Label(dialog, text="Select Book:").pack(pady=5)
        book_var = tk.StringVar(dialog)
        book_combo = ttk.Combobox(dialog, textvariable=book_var)
        book_combo.pack(pady=5)
        
        ttk.Label(dialog, text="Select Member:").pack(pady=5)
        member_var = tk.StringVar(dialog)
        member_combo = ttk.Combobox(dialog, textvariable=member_var)
        member_combo.pack(pady=5)
        
        ttk.Label(dialog, text="Due Date:").pack(pady=5)
        due_date_entry = ttk.Entry(dialog)
        due_date_entry.insert(0, (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"))
        due_date_entry.pack(pady=5)
        
        # Button frame for better layout
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Issue Book", 
                  command=lambda: self.issue_book(
                      book_var.get(), member_var.get(), 
                      due_date_entry.get(), dialog
                  )).pack(side="left", padx=5)
        
        ttk.Button(button_frame, text="Back to Dashboard", 
                  command=lambda: [dialog.destroy(), self.show_dashboard()]).pack(side="left", padx=5)
        
        # Load books and members data
        self.load_available_books(book_combo)
        self.load_active_members(member_combo)

    def show_return_book_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Return Book")
        dialog.geometry("400x300")
        dialog.grab_set()
        
        # Create and pack widgets
        ttk.Label(dialog, text="Select Issue:").pack(pady=5)
        issue_var = tk.StringVar(dialog)
        issue_combo = ttk.Combobox(dialog, textvariable=issue_var)
        issue_combo.pack(pady=5)
        
        ttk.Label(dialog, text="Fine Amount:").pack(pady=5)
        fine_entry = ttk.Entry(dialog)
        fine_entry.insert(0, "0.00")
        fine_entry.pack(pady=5)
        
        ttk.Button(dialog, text="Return Book", 
                  command=lambda: self.return_book(
                      issue_var.get(), fine_entry.get(), dialog
                  )).pack(pady=10)
        
        # Load current issues
        self.load_current_issues_for_return(issue_combo)

    def show_add_user_dialog(self):
        if not self.is_admin:
            messagebox.showerror("Access Denied", "Only administrators can add users")
            return
            
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New User")
        dialog.geometry("400x500")
        dialog.grab_set()
        
        # Create and pack widgets
        ttk.Label(dialog, text="Username:").pack(pady=5)
        username_entry = ttk.Entry(dialog)
        username_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Password:").pack(pady=5)
        password_entry = ttk.Entry(dialog, show="*")
        password_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Full Name:").pack(pady=5)
        fullname_entry = ttk.Entry(dialog)
        fullname_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Email:").pack(pady=5)
        email_entry = ttk.Entry(dialog)
        email_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Role:").pack(pady=5)
        role_var = tk.StringVar(value="staff")
        role_combo = ttk.Combobox(dialog, textvariable=role_var, 
                                 values=["admin", "librarian", "staff"])
        role_combo.pack(pady=5)
        
        ttk.Button(dialog, text="Add User", 
                  command=lambda: self.add_user(
                      username_entry.get(),
                      password_entry.get(),
                      fullname_entry.get(),
                      email_entry.get(),
                      role_var.get(),
                      dialog
                  )).pack(pady=10)

    def show_add_member_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Member")
        dialog.geometry("400x500")
        dialog.grab_set()
        
        # Create and pack widgets
        ttk.Label(dialog, text="First Name:").pack(pady=5)
        first_name_entry = ttk.Entry(dialog)
        first_name_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Last Name:").pack(pady=5)
        last_name_entry = ttk.Entry(dialog)
        last_name_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Email:").pack(pady=5)
        email_entry = ttk.Entry(dialog)
        email_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Phone:").pack(pady=5)
        phone_entry = ttk.Entry(dialog)
        phone_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Address:").pack(pady=5)
        address_text = tk.Text(dialog, height=3, width=40)
        address_text.pack(pady=5)
        
        ttk.Label(dialog, text="Status:").pack(pady=5)
        status_var = tk.StringVar(value="active")
        status_combo = ttk.Combobox(dialog, textvariable=status_var, 
                                  values=["active", "inactive", "suspended"])
        status_combo.pack(pady=5)
        
        # Save button
        ttk.Button(dialog, text="Save", 
                  command=lambda: self.save_member(
                      first_name_entry.get(),
                      last_name_entry.get(),
                      email_entry.get(),
                      phone_entry.get(),
                      address_text.get("1.0", tk.END),
                      status_var.get(),
                      dialog
                  )).pack(pady=10)

    def generate_report(self, report_type):
        try:
            cursor = self.conn.cursor()
            
            if report_type == "books":
                cursor.execute("""
                SELECT b.title, b.author, c.category_name, b.total_copies, 
                       b.available_copies, COUNT(bi.book_id) as times_borrowed
                FROM books b
                LEFT JOIN categories c ON b.category_id = c.category_id
                LEFT JOIN book_issues bi ON b.book_id = bi.book_id
                GROUP BY b.book_id
                ORDER BY times_borrowed DESC
                """)
            elif report_type == "members":
                cursor.execute("""
                SELECT m.first_name || ' ' || m.last_name as name, 
                       m.email, m.membership_status,
                       COUNT(bi.member_id) as books_borrowed,
                       SUM(CASE WHEN bi.status = 'overdue' THEN 1 ELSE 0 END) as overdue_books
                FROM members m
                LEFT JOIN book_issues bi ON m.member_id = bi.member_id
                GROUP BY m.member_id
                ORDER BY books_borrowed DESC
                """)
            elif report_type == "circulation":
                cursor.execute("""
                SELECT b.title, m.first_name || ' ' || m.last_name as member_name,
                       bi.issue_date, bi.due_date, bi.return_date, bi.status
                FROM book_issues bi
                JOIN books b ON bi.book_id = b.book_id
                JOIN members m ON bi.member_id = m.member_id
                ORDER BY bi.issue_date DESC
                """)
            elif report_type == "overdue":
                cursor.execute("""
                SELECT b.title, m.first_name || ' ' || m.last_name as member_name,
                       bi.issue_date, bi.due_date,
                       julianday('now') - julianday(bi.due_date) as days_overdue
                FROM book_issues bi
                JOIN books b ON bi.book_id = b.book_id
                JOIN members m ON bi.member_id = m.member_id
                WHERE bi.status = 'overdue'
                ORDER BY days_overdue DESC
                """)
            elif report_type == "fines":
                cursor.execute("""
                SELECT m.first_name || ' ' || m.last_name as member_name,
                       b.title, f.amount, f.fine_date, f.payment_status
                FROM fines f
                JOIN book_issues bi ON f.issue_id = bi.issue_id
                JOIN books b ON bi.book_id = b.book_id
                JOIN members m ON bi.member_id = m.member_id
                ORDER BY f.fine_date DESC
                """)
            
            # Fetch all rows
            rows = cursor.fetchall()
            cursor.close()
            
            if not rows:
                messagebox.showinfo("Report", "No data available for this report")
                return
            
            # Ask user where to save the report
            file_path = filedialog.asksaveasfilename(
                defaultextension='.csv',
                filetypes=[("CSV files", "*.csv")],
                initialfile=f"{report_type}_report_{datetime.now().strftime('%Y%m%d')}.csv"
            )
            
            if not file_path:
                return
            
            # Write to CSV
            with open(file_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                # Write headers
                writer.writerow([description[0] for description in cursor.description])
                # Write data rows
                writer.writerows(rows)
            
            messagebox.showinfo("Success", f"Report has been saved to {file_path}")
            
        except sqlite3.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")

    def load_current_issues(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
            SELECT bi.issue_id, b.title, m.first_name || ' ' || m.last_name as member_name,
                   bi.issue_date, bi.due_date, bi.status
            FROM book_issues bi
            JOIN books b ON bi.book_id = b.book_id
            JOIN members m ON bi.member_id = m.member_id
            WHERE bi.status IN ('issued', 'overdue')
            ORDER BY bi.issue_date DESC
            """)
            
            issues = cursor.fetchall()
            cursor.close()
            
            # Clear existing data
            for item in self.issues_table.get_children():
                self.issues_table.delete(item)
            
            # Insert new data
            for issue in issues:
                self.issues_table.insert("", tk.END, values=(
                    issue['issue_id'],
                    issue['title'],
                    issue['member_name'],
                    datetime.strptime(issue['issue_date'], '%Y-%m-%d %H:%M:%S').strftime("%Y-%m-%d"),
                    datetime.strptime(issue['due_date'], '%Y-%m-%d %H:%M:%S').strftime("%Y-%m-%d"),
                    issue['status'].capitalize()
                ))
        except sqlite3.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")

    def load_users(self):
        if not self.is_admin:
            return
            
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
            SELECT user_id, username, full_name, email, role, last_login
            FROM users
            ORDER BY username
            """)
            
            users = cursor.fetchall()
            cursor.close()
            
            # Clear existing data
            for item in self.users_table.get_children():
                self.users_table.delete(item)
            
            # Insert new data
            for user in users:
                self.users_table.insert("", tk.END, values=(
                    user['user_id'],
                    user['username'],
                    user['full_name'],
                    user['email'],
                    user['role'].capitalize(),
                    datetime.strptime(user['last_login'], '%Y-%m-%d %H:%M:%S').strftime("%Y-%m-%d %H:%M") if user['last_login'] else "Never"
                ))
        except sqlite3.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")

    def load_available_books(self, combo):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
            SELECT book_id, title, author
            FROM books
            WHERE available_copies > 0
            ORDER BY title
            """)
            books = cursor.fetchall()
            cursor.close()
            
            combo['values'] = [f"{book['title']} by {book['author']}" for book in books]
        except sqlite3.Error:
            combo['values'] = []

    def load_active_members(self, combo):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
            SELECT member_id, first_name, last_name
            FROM members
            WHERE membership_status = 'active'
            ORDER BY first_name, last_name
            """)
            members = cursor.fetchall()
            cursor.close()
            
            combo['values'] = [f"{member['first_name']} {member['last_name']}" for member in members]
        except sqlite3.Error:
            combo['values'] = []

    def load_current_issues_for_return(self, combo):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
            SELECT bi.issue_id, b.title, m.first_name || ' ' || m.last_name as member_name
            FROM book_issues bi
            JOIN books b ON bi.book_id = b.book_id
            JOIN members m ON bi.member_id = m.member_id
            WHERE bi.status IN ('issued', 'overdue')
            ORDER BY bi.issue_date DESC
            """)
            issues = cursor.fetchall()
            cursor.close()
            
            combo['values'] = [f"#{issue['issue_id']} - {issue['title']} ({issue['member_name']})" 
                             for issue in issues]
        except sqlite3.Error:
            combo['values'] = []

    def issue_book(self, book_selection, member_selection, due_date, dialog):
        if not book_selection or not member_selection or not due_date:
            messagebox.showerror("Input Error", "Please select both book and member, and specify a due date")
            return
            
        try:
            # Parse book_id from selection string
            book_title = book_selection.split(" by ")[0]
            cursor = self.conn.cursor()
            cursor.execute("SELECT book_id FROM books WHERE title = ?", (book_title,))
            book_result = cursor.fetchone()
            
            if not book_result:
                messagebox.showerror("Error", "Selected book not found")
                cursor.close()
                return
                
            book_id = book_result['book_id']
            
            # Parse member_id from selection string
            member_name = member_selection.split()
            cursor.execute("""
            SELECT member_id FROM members 
            WHERE first_name = ? AND last_name = ?
            """, (member_name[0], member_name[1]))
            member_result = cursor.fetchone()
            
            if not member_result:
                messagebox.showerror("Error", "Selected member not found")
                cursor.close()
                return
                
            member_id = member_result['member_id']
            
            # Validate due date format
            try:
                due_date_obj = datetime.strptime(due_date, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Input Error", "Due date must be in YYYY-MM-DD format")
                cursor.close()
                return
            
            # Check if book is available
            cursor.execute("""
            SELECT available_copies 
            FROM books WHERE book_id = ?
            """, (book_id,))
            book_status = cursor.fetchone()
            
            if book_status['available_copies'] <= 0:
                messagebox.showerror("Error", "No copies of this book are currently available")
                cursor.close()
                return
            
            # Create issue record
            cursor.execute("""
            INSERT INTO book_issues (book_id, member_id, due_date, issued_by)
            VALUES (?, ?, ?, ?)
            """, (book_id, member_id, due_date_obj.strftime("%Y-%m-%d"), self.current_user['user_id']))
            
            # Update available copies
            cursor.execute("""
            UPDATE books 
            SET available_copies = available_copies - 1
            WHERE book_id = ?
            """, (book_id,))
            
            self.conn.commit()
            cursor.close()
            
            # Close dialog and refresh
            dialog.destroy()
            self.load_current_issues()
            messagebox.showinfo("Success", "Book issued successfully!")
            
        except sqlite3.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")

    def return_book(self, issue_selection, fine_amount, dialog):
        if not issue_selection:
            messagebox.showerror("Input Error", "Please select an issue to return")
            return
            
        try:
            # Parse issue_id from selection string
            issue_id = int(issue_selection.split(" - ")[0].replace("#", ""))
            
            cursor = self.conn.cursor()
            
            # Get book_id for updating available copies
            cursor.execute("SELECT book_id FROM book_issues WHERE issue_id = ?", (issue_id,))
            issue = cursor.fetchone()
            
            if not issue:
                messagebox.showerror("Error", "Selected issue not found")
                cursor.close()
                return
            
            book_id = issue['book_id']
            
            # Update issue status
            cursor.execute("""
            UPDATE book_issues 
            SET status = 'returned', 
                return_date = CURRENT_TIMESTAMP,
                fine_amount = ?
            WHERE issue_id = ?
            """, (float(fine_amount), issue_id))
            
            # Update available copies
            cursor.execute("""
            UPDATE books 
            SET available_copies = available_copies + 1
            WHERE book_id = ?
            """, (book_id,))
            
            # Create fine record if fine amount > 0
            if float(fine_amount) > 0:
                cursor.execute("""
                INSERT INTO fines (issue_id, amount)
                VALUES (?, ?)
                """, (issue_id, float(fine_amount)))
            
            self.conn.commit()
            cursor.close()
            
            # Close dialog and refresh
            dialog.destroy()
            self.load_current_issues()
            messagebox.showinfo("Success", "Book returned successfully!")
            
        except ValueError:
            messagebox.showerror("Input Error", "Invalid fine amount")
        except sqlite3.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")

    def add_user(self, username, password, fullname, email, role, dialog):
        if not username or not password or not fullname or not email or not role:
            messagebox.showerror("Input Error", "All fields are required")
            return
            
        # Validate email format
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            messagebox.showerror("Input Error", "Please enter a valid email address")
            return
            
        try:
            # Hash the password
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            cursor = self.conn.cursor()
            cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, email, role)
            VALUES (?, ?, ?, ?, ?)
            """, (username, password_hash, fullname, email, role))
            
            self.conn.commit()
            cursor.close()
            
            # Close dialog and refresh
            dialog.destroy()
            self.load_users()
            messagebox.showinfo("Success", "User added successfully!")
            
        except sqlite3.IntegrityError:
            messagebox.showerror("Database Error", "Username or email already exists")
        except sqlite3.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")

if __name__ == "__main__":
    root = ThemedTk(theme="arc")  # Using ThemedTk instead of regular tk.Tk()
    app = LibraryManagementSystem(root)
    root.mainloop()