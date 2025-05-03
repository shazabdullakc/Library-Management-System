import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import mysql.connector
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
        style.configure("TButton", background=self.secondary_color, foreground="white", font=("Helvetica", 11))
        style.configure("Header.TLabel", font=("Helvetica", 16, "bold"), background=self.bg_color, foreground=self.primary_color)
        style.configure("Title.TLabel", font=("Helvetica", 24, "bold"), background=self.primary_color, foreground="white")
        style.configure("Sidebar.TFrame", background=self.primary_color)
        style.configure("Sidebar.TButton", font=("Helvetica", 12), background=self.primary_color, foreground="white")
        style.configure("Accent.TButton", background=self.accent_color)
        style.map("TButton", background=[('active', self.secondary_color)], foreground=[('active', 'white')])
        style.map("Accent.TButton", background=[('active', self.accent_color)])
        
        # Display Login Frame
        self.show_login_frame()
    
    def db_connection(self):
        try:
            # Get database configuration
            params = config()
            
            # Connect to database
            self.conn = mysql.connector.connect(**params)
            
            # Test connection
            if not self.conn.is_connected():
                raise mysql.connector.Error("Failed to connect to database")
                
            # Create database if it doesn't exist
            cursor = self.conn.cursor()
            cursor.execute("CREATE DATABASE IF NOT EXISTS library_management")
            cursor.execute("USE library_management")
            cursor.close()
            
            # Create tables
            self.create_tables()
            return True
            
        except mysql.connector.Error as err:
            if self.conn:
                self.conn.close()
            messagebox.showerror("Database Error", f"Could not connect to database: {err}")
            return False
        except Exception as e:
            if self.conn:
                self.conn.close()
            messagebox.showerror("Error", f"An error occurred: {e}")
            return False
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Create Categories Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            category_id INT AUTO_INCREMENT PRIMARY KEY,
            category_name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT
        )
        """)
        
        # Create Books Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            book_id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            author VARCHAR(255) NOT NULL,
            isbn VARCHAR(13) UNIQUE,
            publisher VARCHAR(255),
            publication_year INT,
            category_id INT,
            total_copies INT DEFAULT 1,
            available_copies INT DEFAULT 1,
            description TEXT,
            added_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            cover_image VARCHAR(255),
            FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE SET NULL
        )
        """)
        
        # Create Members Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS members (
            member_id INT AUTO_INCREMENT PRIMARY KEY,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            phone VARCHAR(20),
            address TEXT,
            join_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            membership_status ENUM('active', 'inactive', 'suspended') DEFAULT 'active',
            profile_image VARCHAR(255)
        )
        """)
        
        # Create Users Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            full_name VARCHAR(255) NOT NULL,
            role ENUM('admin', 'librarian', 'staff') NOT NULL,
            created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_login DATETIME
        )
        """)
        
        # Create Book Issues Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS book_issues (
            issue_id INT AUTO_INCREMENT PRIMARY KEY,
            book_id INT NOT NULL,
            member_id INT NOT NULL,
            issue_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            due_date DATETIME NOT NULL,
            return_date DATETIME,
            fine_amount DECIMAL(10,2) DEFAULT 0.00,
            status ENUM('issued', 'returned', 'overdue') DEFAULT 'issued',
            issued_by INT,
            FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE CASCADE,
            FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE,
            FOREIGN KEY (issued_by) REFERENCES users(user_id) ON DELETE SET NULL
        )
        """)
        
        # Create Fines Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS fines (
            fine_id INT AUTO_INCREMENT PRIMARY KEY,
            issue_id INT NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            fine_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            payment_date DATETIME,
            payment_status ENUM('paid', 'unpaid') DEFAULT 'unpaid',
            FOREIGN KEY (issue_id) REFERENCES book_issues(issue_id) ON DELETE CASCADE
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
            VALUES (%s, %s, %s, %s, %s)
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
            VALUES (%s, %s)
            """, default_categories)
        
        self.conn.commit()
        cursor.close()
    
    def show_login_frame(self):
        # Clear existing frames
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Create Login Frame
        login_frame = ttk.Frame(self.root, style="TFrame")
        login_frame.pack(fill=tk.BOTH, expand=True)
        
        # Center login form
        center_frame = ttk.Frame(login_frame, style="TFrame")
        center_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=400, height=450)
        
        # Title and logo
        title_label = ttk.Label(center_frame, text="Library Management System", style="Header.TLabel")
        title_label.pack(pady=(0, 20))
        
        # Add a logo or image here if desired
        # logo_img = ImageTk.PhotoImage(Image.open("logo.png").resize((100, 100)))
        # logo_label = ttk.Label(center_frame, image=logo_img)
        # logo_label.image = logo_img
        # logo_label.pack(pady=(0, 20))
        
        # Login form
        form_frame = ttk.Frame(center_frame, style="TFrame")
        form_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)
        
        username_label = ttk.Label(form_frame, text="Username:", style="TLabel")
        username_label.pack(anchor=tk.W, pady=(10, 5))
        
        self.username_entry = ttk.Entry(form_frame, width=30, font=("Helvetica", 12))
        self.username_entry.pack(fill=tk.X, pady=(0, 15))
        
        password_label = ttk.Label(form_frame, text="Password:", style="TLabel")
        password_label.pack(anchor=tk.W, pady=(10, 5))
        
        self.password_entry = ttk.Entry(form_frame, width=30, font=("Helvetica", 12), show="*")
        self.password_entry.pack(fill=tk.X, pady=(0, 25))
        
        # Login button
        login_button = ttk.Button(form_frame, text="Login", command=self.login, style="TButton")
        login_button.pack(fill=tk.X, pady=(20, 10))
        
        # Default credentials note
        note_text = "Default Admin Credentials:\nUsername: admin\nPassword: admin123"
        note_label = ttk.Label(form_frame, text=note_text, foreground="gray", background=self.bg_color, font=("Helvetica", 10))
        note_label.pack(pady=(20, 0))
        
    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not username or not password:
            messagebox.showerror("Login Error", "Please enter both username and password")
            return
        
        # Hash the password for comparison
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("""
            SELECT * FROM users 
            WHERE username = %s AND password_hash = %s
            """, (username, password_hash))
            
            user = cursor.fetchone()
            cursor.close()
            
            if user:
                self.current_user = user
                self.is_admin = (user['role'] == 'admin')
                
                # Update last login time
                cursor = self.conn.cursor()
                cursor.execute("""
                UPDATE users SET last_login = NOW()
                WHERE user_id = %s
                """, (user['user_id'],))
                self.conn.commit()
                cursor.close()
                
                # Show main dashboard
                self.show_dashboard()
            else:
                messagebox.showerror("Login Error", "Invalid username or password")
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")
    
    def show_dashboard(self):
        # Clear existing frames
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Create Main Container
        main_container = ttk.Frame(self.root, style="TFrame")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create Sidebar
        sidebar = ttk.Frame(main_container, width=220, style="Sidebar.TFrame")
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)  # Prevent the sidebar from resizing
        
        # App Title
        title_frame = ttk.Frame(sidebar, style="Sidebar.TFrame")
        title_frame.pack(fill=tk.X, padx=10, pady=20)
        
        title_label = ttk.Label(title_frame, text="Library MS", 
                               font=("Helvetica", 18, "bold"), 
                               foreground="white", 
                               background=self.primary_color)
        title_label.pack(side=tk.LEFT)
        
        # User Info
        user_frame = ttk.Frame(sidebar, style="Sidebar.TFrame")
        user_frame.pack(fill=tk.X, padx=10, pady=(0, 20))
        
        user_label = ttk.Label(user_frame, 
                              text=f"Welcome, {self.current_user['full_name']}", 
                              font=("Helvetica", 10), 
                              foreground="white", 
                              background=self.primary_color,
                              wraplength=200)
        user_label.pack(anchor=tk.W)
        
        role_label = ttk.Label(user_frame, 
                              text=f"Role: {self.current_user['role'].capitalize()}", 
                              font=("Helvetica", 9), 
                              foreground="#ccc", 
                              background=self.primary_color)
        role_label.pack(anchor=tk.W)
        
        # Navigation Buttons
        nav_frame = ttk.Frame(sidebar, style="Sidebar.TFrame")
        nav_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Navigation Buttons with custom style
        dashboard_btn = tk.Button(nav_frame, text="Dashboard", 
                                 font=("Helvetica", 12), 
                                 bg=self.primary_color, 
                                 fg="white", 
                                 bd=0, 
                                 activebackground=self.secondary_color,
                                 activeforeground="white",
                                 highlightthickness=0,
                                 command=self.show_dashboard_content)
        dashboard_btn.pack(fill=tk.X, pady=5)
        
        books_btn = tk.Button(nav_frame, text="Books Management", 
                             font=("Helvetica", 12), 
                             bg=self.primary_color, 
                             fg="white", 
                             bd=0, 
                             activebackground=self.secondary_color,
                             activeforeground="white",
                             highlightthickness=0,
                             command=self.show_books_management)
        books_btn.pack(fill=tk.X, pady=5)
        
        members_btn = tk.Button(nav_frame, text="Members Management", 
                               font=("Helvetica", 12), 
                               bg=self.primary_color, 
                               fg="white", 
                               bd=0, 
                               activebackground=self.secondary_color,
                               activeforeground="white",
                               highlightthickness=0,
                               command=self.show_members_management)
        members_btn.pack(fill=tk.X, pady=5)
        
        issues_btn = tk.Button(nav_frame, text="Book Issues", 
                              font=("Helvetica", 12), 
                              bg=self.primary_color, 
                              fg="white", 
                              bd=0, 
                              activebackground=self.secondary_color,
                              activeforeground="white",
                              highlightthickness=0,
                              command=self.show_issues_management)
        issues_btn.pack(fill=tk.X, pady=5)
        
        categories_btn = tk.Button(nav_frame, text="Categories", 
                                  font=("Helvetica", 12), 
                                  bg=self.primary_color, 
                                  fg="white", 
                                  bd=0, 
                                  activebackground=self.secondary_color,
                                  activeforeground="white",
                                  highlightthickness=0,
                                  command=self.show_categories_management)
        categories_btn.pack(fill=tk.X, pady=5)
        
        reports_btn = tk.Button(nav_frame, text="Reports", 
                               font=("Helvetica", 12), 
                               bg=self.primary_color, 
                               fg="white", 
                               bd=0, 
                               activebackground=self.secondary_color,
                               activeforeground="white",
                               highlightthickness=0,
                               command=self.show_reports)
        reports_btn.pack(fill=tk.X, pady=5)
        
        # Show Admin button only for admin users
        if self.is_admin:
            users_btn = tk.Button(nav_frame, text="Users Management", 
                                 font=("Helvetica", 12), 
                                 bg=self.primary_color, 
                                 fg="white", 
                                 bd=0, 
                                 activebackground=self.secondary_color,
                                 activeforeground="white",
                                 highlightthickness=0,
                                 command=self.show_users_management)
            users_btn.pack(fill=tk.X, pady=5)
        
        # Settings and Logout
        bottom_frame = ttk.Frame(sidebar, style="Sidebar.TFrame")
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=20)
        
        settings_btn = tk.Button(bottom_frame, text="Settings", 
                                font=("Helvetica", 12), 
                                bg=self.primary_color, 
                                fg="white", 
                                bd=0, 
                                activebackground=self.secondary_color,
                                activeforeground="white",
                                highlightthickness=0,
                                command=self.show_settings)
        settings_btn.pack(fill=tk.X, pady=5)
        
        logout_btn = tk.Button(bottom_frame, text="Logout", 
                              font=("Helvetica", 12), 
                              bg=self.accent_color, 
                              fg="white", 
                              bd=0, 
                              activebackground="#c0392b",
                              activeforeground="white",
                              highlightthickness=0,
                              command=self.logout)
        logout_btn.pack(fill=tk.X, pady=5)
        
        # Create Content Frame
        self.content_frame = ttk.Frame(main_container, style="TFrame")
        self.content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # By default, show dashboard content
        self.show_dashboard_content()
    
    def logout(self):
        self.current_user = None
        self.is_admin = False
        self.show_login_frame()
    
    def clear_content_frame(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def show_dashboard_content(self):
        self.clear_content_frame()
        
        # Header
        header_frame = ttk.Frame(self.content_frame, style="TFrame")
        header_frame.pack(fill=tk.X, padx=20, pady=20)
        
        header_label = ttk.Label(header_frame, text="Dashboard", style="Header.TLabel")
        header_label.pack(side=tk.LEFT)
        
        # Get current datetime
        now = datetime.now()
        date_label = ttk.Label(header_frame, 
                              text=now.strftime("%B %d, %Y - %H:%M"), 
                              style="TLabel")
        date_label.pack(side=tk.RIGHT)
        
        # Create dashboard content with stats
        stats_frame = ttk.Frame(self.content_frame, style="TFrame")
        stats_frame.pack(fill=tk.BOTH, padx=20, pady=10)
        
        # Create 4 stat boxes
        self.create_stat_box(stats_frame, "Total Books", self.get_total_books(), "📚", "#3498db", 0, 0)
        self.create_stat_box(stats_frame, "Total Members", self.get_total_members(), "👥", "#2ecc71", 0, 1)
        self.create_stat_box(stats_frame, "Books Issued", self.get_issued_books(), "📖", "#e67e22", 1, 0)
        self.create_stat_box(stats_frame, "Overdue Books", self.get_overdue_books(), "⏰", "#e74c3c", 1, 1)
        
        # Recent Activities Section
        activities_frame = ttk.Frame(self.content_frame, style="TFrame")
        activities_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        activities_label = ttk.Label(activities_frame, text="Recent Activities", style="Header.TLabel")
        activities_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Recent Books Issue Table
        self.recent_issues_table = ttk.Treeview(activities_frame, columns=("ID", "Book", "Member", "Issue Date", "Due Date", "Status"), show="headings", height=10)
        self.recent_issues_table.heading("ID", text="ID")
        self.recent_issues_table.heading("Book", text="Book")
        self.recent_issues_table.heading("Member", text="Member")
        self.recent_issues_table.heading("Issue Date", text="Issue Date")
        self.recent_issues_table.heading("Due Date", text="Due Date")
        self.recent_issues_table.heading("Status", text="Status")
        
        self.recent_issues_table.column("ID", width=50)
        self.recent_issues_table.column("Book", width=200)
        self.recent_issues_table.column("Member", width=150)
        self.recent_issues_table.column("Issue Date", width=120)
        self.recent_issues_table.column("Due Date", width=120)
        self.recent_issues_table.column("Status", width=100)
        
        # Add scrollbar to the table
        scrollbar = ttk.Scrollbar(activities_frame, orient=tk.VERTICAL, command=self.recent_issues_table.yview)
        self.recent_issues_table.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.recent_issues_table.pack(fill=tk.BOTH, expand=True)
        
        # Load recent issues data
        self.load_recent_issues()
    
    def create_stat_box(self, parent, title, value, icon, color, row, col):
        box_frame = ttk.Frame(parent, style="TFrame")
        box_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        
        # Configure grid to expand
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        
        # Create a canvas for drawing the rounded rectangle
        canvas = tk.Canvas(box_frame, height=150, bg=self.bg_color, highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Draw rounded rectangle
        canvas.create_rectangle(0, 0, 500, 150, fill="white", outline="")
        
        # Add color bar at the top
        canvas.create_rectangle(0, 0, 500, 10, fill=color, outline="")
        
        # Add icon
        canvas.create_text(30, 50, text=icon, font=("Helvetica", 30), fill=color)
        
        # Add title and value
        canvas.create_text(150, 50, text=title, font=("Helvetica", 14), fill=self.text_color, anchor=tk.W)
        canvas.create_text(150, 90, text=str(value), font=("Helvetica", 36, "bold"), fill=self.text_color, anchor=tk.W)
    
    def get_total_books(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT SUM(total_copies) FROM books")
            result = cursor.fetchone()[0]
            cursor.close()
            return result if result else 0
        except mysql.connector.Error:
            return 0
    
    def get_total_members(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM members")
            result = cursor.fetchone()[0]
            cursor.close()
            return result
        except mysql.connector.Error:
            return 0
    
    def get_issued_books(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM book_issues WHERE status = 'issued'")
            result = cursor.fetchone()[0]
            cursor.close()
            return result
        except mysql.connector.Error:
            return 0
    
    def get_overdue_books(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM book_issues WHERE status = 'overdue'")
            result = cursor.fetchone()[0]
            cursor.close()
            return result
        except mysql.connector.Error:
            return 0
    
    def load_recent_issues(self):
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("""
            SELECT bi.issue_id, b.title, CONCAT(m.first_name, ' ', m.last_name) as member_name,
                  bi.issue_date, bi.due_date, bi.status
            FROM book_issues bi
            JOIN books b ON bi.book_id = b.book_id
            JOIN members m ON bi.member_id = m.member_id
            ORDER BY bi.issue_date DESC
            LIMIT 10
            """)
            
            issues = cursor.fetchall()
            cursor.close()
            
            # Clear existing data
            for item in self.recent_issues_table.get_children():
                self.recent_issues_table.delete(item)
            
            # Insert new data
            for issue in issues:
                status = issue['status']
                issue_date = issue['issue_date'].strftime("%Y-%m-%d")
                due_date = issue['due_date'].strftime("%Y-%m-%d")
                
                self.recent_issues_table.insert("", tk.END, values=(
                    issue['issue_id'],
                    issue['title'],
                    issue['member_name'],
                    issue_date,
                    due_date,
                    status.capitalize()
                ))
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")

    def show_books_management(self):
        self.clear_content_frame()
        
        # Header
        header_frame = ttk.Frame(self.content_frame, style="TFrame")
        header_frame.pack(fill=tk.X, padx=20, pady=20)
        
        header_label = ttk.Label(header_frame, text="Books Management", style="Header.TLabel")
        header_label.pack(side=tk.LEFT)
        
        search_frame = ttk.Frame(header_frame, style="TFrame")
        search_frame.pack(side=tk.RIGHT)
        
        search_label = ttk.Label(search_frame, text="Search:", style="TLabel")
        search_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.book_search_entry = ttk.Entry(search_frame, width=25)
        self.book_search_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        search_button = ttk.Button(search_frame, text="Search", command=self.search_books)
        search_button.pack(side=tk.LEFT)
        
        # Buttons for book operations
        button_frame = ttk.Frame(self.content_frame, style="TFrame")
        button_frame.pack(fill=tk.X, padx=20, pady=10)
        
        add_button = ttk.Button(button_frame, text="Add New Book", command=self.show_add_book_form)
        add_button.pack(side=tk.LEFT, padx=(0, 10))
        
        edit_button = ttk.Button(button_frame, text="Edit Selected", command=self.edit_selected_book)
        edit_button.pack(side=tk.LEFT, padx=(0, 10))
        
        delete_button = ttk.Button(button_frame, text="Delete Selected", style="Accent.TButton", command=self.delete_selected_book)
        delete_button.pack(side=tk.LEFT)
        
        refresh_button = ttk.Button(button_frame, text="Refresh", command=self.refresh_books_table)
        refresh_button.pack(side=tk.RIGHT)
        
        # Books Table
        table_frame = ttk.Frame(self.content_frame, style="TFrame")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.books_table = ttk.Treeview(table_frame, 
                                        columns=("ID", "Title", "Author", "ISBN", "Category", "Total Copies", "Available", "Publication Year"), 
                                        show="headings", 
                                        height=20)
        
        self.books_table.heading("ID", text="ID")
        self.books_table.heading("Title", text="Title")
        self.books_table.heading("Author", text="Author")
        self.books_table.heading("ISBN", text="ISBN")
        self.books_table.heading("Category", text="Category")
        self.books_table.heading("Total Copies", text="Total Copies")
        self.books_table.heading("Available", text="Available")
        self.books_table.heading("Publication Year", text="Publication Year")
        
        self.books_table.column("ID", width=50)
        self.books_table.column("Title", width=200)
        self.books_table.column("Author", width=150)
        self.books_table.column("ISBN", width=100)
        self.books_table.column("Category", width=100)
        self.books_table.column("Total Copies", width=80)
        self.books_table.column("Available", width=80)
        self.books_table.column("Publication Year", width=100)
        
        # Add scrollbar to the table
        y_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.books_table.yview)
        self.books_table.configure(yscrollcommand=y_scrollbar.set)
        
        x_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.books_table.xview)
        self.books_table.configure(xscrollcommand=x_scrollbar.set)
        
        self.books_table.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind selection event
        self.books_table.bind('<<TreeviewSelect>>', self.on_book_select)
        
        # Load books data
        self.load_books()
    
    def load_books(self):
        try:
            cursor = self.conn.cursor(dictionary=True)
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
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")
    
    def search_books(self):
        search_term = self.book_search_entry.get().strip()
        
        if not search_term:
            self.load_books()  # If search is empty, load all books
            return
        
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("""
            SELECT b.book_id, b.title, b.author, b.isbn, c.category_name, 
                   b.total_copies, b.available_copies, b.publication_year
            FROM books b
            LEFT JOIN categories c ON b.category_id = c.category_id
            WHERE b.title LIKE %s OR b.author LIKE %s OR b.isbn LIKE %s
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
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")
    
    def on_book_select(self, event):
        selected_items = self.books_table.selection()
        if selected_items:
            item = selected_items[0]
            values = self.books_table.item(item, 'values')
            self.selected_book_id = values[0]
    
    def refresh_books_table(self):
        self.load_books()
    
    def show_add_book_form(self):
        # Create a new window for adding a book
        add_window = tk.Toplevel(self.root)
        add_window.title("Add New Book")
        add_window.geometry("500x600")
        add_window.configure(bg=self.bg_color)
        add_window.grab_set()  # Make the window modal
        
        # Create a form frame
        form_frame = ttk.Frame(add_window, style="TFrame")
        form_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(form_frame, text="Title:", style="TLabel")
        title_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        title_entry = ttk.Entry(form_frame, width=30)
        title_entry.grid(row=0, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
        
        # Author
        author_label = ttk.Label(form_frame, text="Author:", style="TLabel")
        author_label.grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
        
        author_entry = ttk.Entry(form_frame, width=30)
        author_entry.grid(row=1, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
        
        # ISBN
        isbn_label = ttk.Label(form_frame, text="ISBN:", style="TLabel")
        isbn_label.grid(row=2, column=0, sticky=tk.W, pady=(0, 10))
        
        isbn_entry = ttk.Entry(form_frame, width=30)
        isbn_entry.grid(row=2, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
        
        # Publisher
        publisher_label = ttk.Label(form_frame, text="Publisher:", style="TLabel")
        publisher_label.grid(row=3, column=0, sticky=tk.W, pady=(0, 10))
        
        publisher_entry = ttk.Entry(form_frame, width=30)
        publisher_entry.grid(row=3, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
        
        # Publication Year
        year_label = ttk.Label(form_frame, text="Publication Year:", style="TLabel")
        year_label.grid(row=4, column=0, sticky=tk.W, pady=(0, 10))
        
        year_entry = ttk.Entry(form_frame, width=30)
        year_entry.grid(row=4, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
        
        # Category
        category_label = ttk.Label(form_frame, text="Category:", style="TLabel")
        category_label.grid(row=5, column=0, sticky=tk.W, pady=(0, 10))
        
        # Get categories from database
        categories = self.get_categories()
        category_var = tk.StringVar()
        
        category_combobox = ttk.Combobox(form_frame, textvariable=category_var, width=28)
        category_combobox['values'] = [cat['category_name'] for cat in categories]
        category_combobox.grid(row=5, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
        
        # Total Copies
        copies_label = ttk.Label(form_frame, text="Total Copies:", style="TLabel")
        copies_label.grid(row=6, column=0, sticky=tk.W, pady=(0, 10))
        
        copies_entry = ttk.Entry(form_frame, width=30)
        copies_entry.grid(row=6, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
        copies_entry.insert(0, "1")  # Default value
        
        # Description
        desc_label = ttk.Label(form_frame, text="Description:", style="TLabel")
        desc_label.grid(row=7, column=0, sticky=tk.NW, pady=(0, 10))
        
        desc_text = tk.Text(form_frame, width=30, height=5)
        desc_text.grid(row=7, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
        
        # Buttons
        button_frame = ttk.Frame(form_frame, style="TFrame")
        button_frame.grid(row=8, column=0, columnspan=2, pady=(20, 0))
        
        save_button = ttk.Button(button_frame, text="Save", command=lambda: self.save_book(
            title_entry.get(),
            author_entry.get(),
            isbn_entry.get(),
            publisher_entry.get(),
            year_entry.get(),
            category_var.get(),
            copies_entry.get(),
            desc_text.get("1.0", tk.END),
            add_window
        ))
        save_button.grid(row=0, column=0, padx=5)
        
        cancel_button = ttk.Button(button_frame, text="Cancel", command=add_window.destroy)
        cancel_button.grid(row=0, column=1, padx=5)
        
        # Configure grid weights
        form_frame.columnconfigure(1, weight=1)
    
    def get_categories(self):
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("SELECT category_id, category_name FROM categories ORDER BY category_name")
            categories = cursor.fetchall()
            cursor.close()
            return categories
        except mysql.connector.Error:
            return []
    
    def save_book(self, title, author, isbn, publisher, year, category, copies, description, window):
        if not title or not author:
            messagebox.showerror("Input Error", "Title and Author are required fields")
            return
        
        try:
            # Get category_id from category_name
            category_id = None
            if category:
                cursor = self.conn.cursor()
                cursor.execute("SELECT category_id FROM categories WHERE category_name = %s", (category,))
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
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")
    
    def edit_selected_book(self):
        if not self.selected_book_id:
            messagebox.showerror("Selection Error", "Please select a book to edit")
            return
        
        try:
            # Get book details
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("""
            SELECT b.*, c.category_name
            FROM books b
            LEFT JOIN categories c ON b.category_id = c.category_id
            WHERE b.book_id = %s
            """, (self.selected_book_id,))
            
            book = cursor.fetchone()
            cursor.close()
            
            if not book:
                messagebox.showerror("Error", "Book not found")
                return
            
            # Create edit window
            edit_window = tk.Toplevel(self.root)
            edit_window.title("Edit Book")
            edit_window.geometry("500x600")
            edit_window.configure(bg=self.bg_color)
            edit_window.grab_set()  # Make the window modal
            
            # Create a form frame
            form_frame = ttk.Frame(edit_window, style="TFrame")
            form_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            # Title
            title_label = ttk.Label(form_frame, text="Title:", style="TLabel")
            title_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
            
            title_entry = ttk.Entry(form_frame, width=30)
            title_entry.grid(row=0, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
            title_entry.insert(0, book['title'])
            
            # Author
            author_label = ttk.Label(form_frame, text="Author:", style="TLabel")
            author_label.grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
            
            author_entry = ttk.Entry(form_frame, width=30)
            author_entry.grid(row=1, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
            author_entry.insert(0, book['author'])
            
            # ISBN
            isbn_label = ttk.Label(form_frame, text="ISBN:", style="TLabel")
            isbn_label.grid(row=2, column=0, sticky=tk.W, pady=(0, 10))
            
            isbn_entry = ttk.Entry(form_frame, width=30)
            isbn_entry.grid(row=2, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
            if book['isbn']:
                isbn_entry.insert(0, book['isbn'])
            
            # Publisher
            publisher_label = ttk.Label(form_frame, text="Publisher:", style="TLabel")
            publisher_label.grid(row=3, column=0, sticky=tk.W, pady=(0, 10))
            
            publisher_entry = ttk.Entry(form_frame, width=30)
            publisher_entry.grid(row=3, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
            if book['publisher']:
                publisher_entry.insert(0, book['publisher'])
            
            # Publication Year
            year_label = ttk.Label(form_frame, text="Publication Year:", style="TLabel")
            year_label.grid(row=4, column=0, sticky=tk.W, pady=(0, 10))
            
            year_entry = ttk.Entry(form_frame, width=30)
            year_entry.grid(row=4, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
            if book['publication_year']:
                year_entry.insert(0, str(book['publication_year']))
            
            # Category
            category_label = ttk.Label(form_frame, text="Category:", style="TLabel")
            category_label.grid(row=5, column=0, sticky=tk.W, pady=(0, 10))
            
            # Get categories from database
            categories = self.get_categories()
            category_var = tk.StringVar()
            if book['category_name']:
                category_var.set(book['category_name'])
            
            category_combobox = ttk.Combobox(form_frame, textvariable=category_var, width=28)
            category_combobox['values'] = [cat['category_name'] for cat in categories]
            category_combobox.grid(row=5, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
            
            # Total Copies
            copies_label = ttk.Label(form_frame, text="Total Copies:", style="TLabel")
            copies_label.grid(row=6, column=0, sticky=tk.W, pady=(0, 10))
            
            copies_entry = ttk.Entry(form_frame, width=30)
            copies_entry.grid(row=6, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
            copies_entry.insert(0, str(book['total_copies']))
            
            # Description
            desc_label = ttk.Label(form_frame, text="Description:", style="TLabel")
            desc_label.grid(row=7, column=0, sticky=tk.NW, pady=(0, 10))
            
            desc_text = tk.Text(form_frame, width=30, height=5)
            desc_text.grid(row=7, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
            if book['description']:
                desc_text.insert("1.0", book['description'])
            
            # Buttons
            button_frame = ttk.Frame(form_frame, style="TFrame")
            button_frame.grid(row=8, column=0, columnspan=2, pady=(20, 0))
            
            save_button = ttk.Button(button_frame, text="Save", command=lambda: self.update_book(
                self.selected_book_id,
                title_entry.get(),
                author_entry.get(),
                isbn_entry.get(),
                publisher_entry.get(),
                year_entry.get(),
                category_var.get(),
                copies_entry.get(),
                desc_text.get("1.0", tk.END),
                book['available_copies'],
                edit_window
            ))
            save_button.grid(row=0, column=0, padx=5)
            
            cancel_button = ttk.Button(button_frame, text="Cancel", command=edit_window.destroy)
            cancel_button.grid(row=0, column=1, padx=5)
            
            # Configure grid weights
            form_frame.columnconfigure(1, weight=1)
            
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")
    
    def update_book(self, book_id, title, author, isbn, publisher, year, category, copies, description, current_available, window):
        if not title or not author:
            messagebox.showerror("Input Error", "Title and Author are required fields")
            return
        
        try:
            # Get category_id from category_name
            category_id = None
            if category:
                cursor = self.conn.cursor()
                cursor.execute("SELECT category_id FROM categories WHERE category_name = %s", (category,))
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
            
            try:
                total_copies = int(copies)
                if total_copies < 1:
                    raise ValueError("Total copies must be at least 1")
                
                # Calculate available copies
                # If total_copies increased, increase available by the difference
                # If total_copies decreased, decrease available by the difference but never below 0
                borrowed_copies = int(total_copies) - int(current_available)
                new_available = max(0, total_copies - borrowed_copies)
                
            except ValueError:
                messagebox.showerror("Input Error", "Total Copies must be a positive number")
                return
            
            # Update book in database
            cursor = self.conn.cursor()
            cursor.execute("""
            UPDATE books
            SET title = %s, author = %s, isbn = %s, publisher = %s, publication_year = %s,
                category_id = %s, total_copies = %s, available_copies = %s, description = %s
            WHERE book_id = %s
            """, (
                title, author, isbn, publisher, pub_year, category_id, 
                total_copies, new_available, description.strip(), book_id
            ))
            self.conn.commit()
            cursor.close()
            
            # Refresh the books table
            self.load_books()
            
            # Close the window
            window.destroy()
            
            messagebox.showinfo("Success", "Book updated successfully!")
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")
    
    def delete_selected_book(self):
        if not self.selected_book_id:
            messagebox.showerror("Selection Error", "Please select a book to delete")
            return
        
        # Confirm deletion
        confirm = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this book?")
        if not confirm:
            return
        
        try:
            # Check if book is currently issued
            cursor = self.conn.cursor()
            cursor.execute("""
            SELECT COUNT(*) FROM book_issues
            WHERE book_id = %s AND status IN ('issued', 'overdue')
            """, (self.selected_book_id,))
            
            result = cursor.fetchone()[0]
            
            if result > 0:
                messagebox.showerror("Delete Error", "Cannot delete book that is currently issued")
                cursor.close()
                return
            
            # Delete book from database
            cursor.execute("DELETE FROM books WHERE book_id = %s", (self.selected_book_id,))
            self.conn.commit()
            cursor.close()
            
            # Refresh the books table
            self.load_books()
            
            # Reset selection
            self.selected_book_id = None
            
            messagebox.showinfo("Success", "Book deleted successfully!")
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")
    
    def show_members_management(self):
        self.clear_content_frame()
        
        # Header
        header_frame = ttk.Frame(self.content_frame, style="TFrame")
        header_frame.pack(fill=tk.X, padx=20, pady=20)
        
        header_label = ttk.Label(header_frame, text="Members Management", style="Header.TLabel")
        header_label.pack(side=tk.LEFT)
        
        search_frame = ttk.Frame(header_frame, style="TFrame")
        search_frame.pack(side=tk.RIGHT)
        
        search_label = ttk.Label(search_frame, text="Search:", style="TLabel")
        search_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.member_search_entry = ttk.Entry(search_frame, width=25)
        self.member_search_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        search_button = ttk.Button(search_frame, text="Search", command=self.search_members)
        search_button.pack(side=tk.LEFT)

        # Buttons for member operations
        button_frame = ttk.Frame(self.content_frame, style="TFrame")
        button_frame.pack(fill=tk.X, padx=20, pady=10)
        
        add_button = ttk.Button(button_frame, text="Add New Member", command=self.show_add_member_form)
        add_button.pack(side=tk.LEFT, padx=(0, 10))
        
        edit_button = ttk.Button(button_frame, text="Edit Selected", command=self.edit_selected_member)
        edit_button.pack(side=tk.LEFT, padx=(0, 10))
        
        delete_button = ttk.Button(button_frame, text="Delete Selected", style="Accent.TButton", command=self.delete_selected_member)
        delete_button.pack(side=tk.LEFT)
        
        refresh_button = ttk.Button(button_frame, text="Refresh", command=self.refresh_members_table)
        refresh_button.pack(side=tk.RIGHT)
        
        # Members Table
        table_frame = ttk.Frame(self.content_frame, style="TFrame")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.members_table = ttk.Treeview(table_frame, 
                                        columns=("ID", "Name", "Email", "Phone", "Status", "Join Date"), 
                                        show="headings", 
                                        height=20)
        
        self.members_table.heading("ID", text="ID")
        self.members_table.heading("Name", text="Name")
        self.members_table.heading("Email", text="Email")
        self.members_table.heading("Phone", text="Phone")
        self.members_table.heading("Status", text="Status")
        self.members_table.heading("Join Date", text="Join Date")
        
        self.members_table.column("ID", width=50)
        self.members_table.column("Name", width=200)
        self.members_table.column("Email", width=200)
        self.members_table.column("Phone", width=120)
        self.members_table.column("Status", width=100)
        self.members_table.column("Join Date", width=100)
        
        # Add scrollbars to the table
        y_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.members_table.yview)
        self.members_table.configure(yscrollcommand=y_scrollbar.set)
        
        x_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.members_table.xview)
        self.members_table.configure(xscrollcommand=x_scrollbar.set)
        
        self.members_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind selection event
        self.members_table.bind('<<TreeviewSelect>>', self.on_member_select)
        
        # Load members data
        self.load_members()

    def search_members(self):
        search_term = self.member_search_entry.get().strip()
        
        if not search_term:
            self.load_members()  # If search is empty, load all members
            return
        
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("""
            SELECT member_id, first_name, last_name, email, phone, membership_status, join_date
            FROM members
            WHERE first_name LIKE %s OR last_name LIKE %s OR email LIKE %s OR phone LIKE %s
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
                    member['join_date'].strftime("%Y-%m-%d")
                ))
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")

    def load_members(self):
        try:
            cursor = self.conn.cursor(dictionary=True)
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
                    member['join_date'].strftime("%Y-%m-%d")
                ))
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")

    def on_member_select(self, event):
        selected_items = self.members_table.selection()
        if selected_items:
            item = selected_items[0]
            values = self.members_table.item(item, 'values')
            self.selected_member_id = values[0]

    def refresh_members_table(self):
        self.load_members()

    def show_add_member_form(self):
        # Create a new window for adding a member
        add_window = tk.Toplevel(self.root)
        add_window.title("Add New Member")
        add_window.geometry("500x600")
        add_window.configure(bg=self.bg_color)
        add_window.grab_set()  # Make the window modal
        
        # Create a form frame
        form_frame = ttk.Frame(add_window, style="TFrame")
        form_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # First Name
        first_name_label = ttk.Label(form_frame, text="First Name:", style="TLabel")
        first_name_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        first_name_entry = ttk.Entry(form_frame, width=30)
        first_name_entry.grid(row=0, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
        
        # Last Name
        last_name_label = ttk.Label(form_frame, text="Last Name:", style="TLabel")
        last_name_label.grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
        
        last_name_entry = ttk.Entry(form_frame, width=30)
        last_name_entry.grid(row=1, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
        
        # Email
        email_label = ttk.Label(form_frame, text="Email:", style="TLabel")
        email_label.grid(row=2, column=0, sticky=tk.W, pady=(0, 10))
        
        email_entry = ttk.Entry(form_frame, width=30)
        email_entry.grid(row=2, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
        
        # Phone
        phone_label = ttk.Label(form_frame, text="Phone:", style="TLabel")
        phone_label.grid(row=3, column=0, sticky=tk.W, pady=(0, 10))
        
        phone_entry = ttk.Entry(form_frame, width=30)
        phone_entry.grid(row=3, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
        
        # Address
        address_label = ttk.Label(form_frame, text="Address:", style="TLabel")
        address_label.grid(row=4, column=0, sticky=tk.NW, pady=(0, 10))
        
        address_text = tk.Text(form_frame, width=30, height=4)
        address_text.grid(row=4, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
        
        # Membership Status
        status_label = ttk.Label(form_frame, text="Status:", style="TLabel")
        status_label.grid(row=5, column=0, sticky=tk.W, pady=(0, 10))
        
        status_var = tk.StringVar(value="active")
        status_combobox = ttk.Combobox(form_frame, textvariable=status_var, width=28)
        status_combobox['values'] = ['active', 'inactive', 'suspended']
        status_combobox.grid(row=5, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
        
        # Buttons
        button_frame = ttk.Frame(form_frame, style="TFrame")
        button_frame.grid(row=6, column=0, columnspan=2, pady=(20, 0))
        
        save_button = ttk.Button(button_frame, text="Save", command=lambda: self.save_member(
            first_name_entry.get(),
            last_name_entry.get(),
            email_entry.get(),
            phone_entry.get(),
            address_text.get("1.0", tk.END),
            status_var.get(),
            add_window
       ))
        save_button.grid(row=0, column=0, padx=5)
        
        cancel_button = ttk.Button(button_frame, text="Cancel", command=add_window.destroy)
        cancel_button.grid(row=0, column=1, padx=5)
        
        # Configure grid weights
        form_frame.columnconfigure(1, weight=1)

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
            VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                first_name, last_name, email, phone, address.strip(), status
            ))
            self.conn.commit()
            cursor.close()
            
            # Refresh the members table
            self.load_members()
            
            # Close the window
            window.destroy()
            
            messagebox.showinfo("Success", "Member added successfully!")
        except mysql.connector.Error as err:
            if err.errno == 1062:  # Duplicate entry error
                messagebox.showerror("Input Error", "This email is already registered")
            else:
                messagebox.showerror("Database Error", f"Error: {err}")

    def edit_selected_member(self):
        if not self.selected_member_id:
            messagebox.showerror("Selection Error", "Please select a member to edit")
            return
        
        try:
            # Get member details
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("""
            SELECT * FROM members WHERE member_id = %s
            """, (self.selected_member_id,))
            
            member = cursor.fetchone()
            cursor.close()
            
            if not member:
                messagebox.showerror("Error", "Member not found")
                return
            
            # Create edit window
            edit_window = tk.Toplevel(self.root)
            edit_window.title("Edit Member")
            edit_window.geometry("500x600")
            edit_window.configure(bg=self.bg_color)
            edit_window.grab_set()  # Make the window modal
            
            # Create a form frame
            form_frame = ttk.Frame(edit_window, style="TFrame")
            form_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            # First Name
            first_name_label = ttk.Label(form_frame, text="First Name:", style="TLabel")
            first_name_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
            
            first_name_entry = ttk.Entry(form_frame, width=30)
            first_name_entry.grid(row=0, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
            first_name_entry.insert(0, member['first_name'])
            
            # Last Name
            last_name_label = ttk.Label(form_frame, text="Last Name:", style="TLabel")
            last_name_label.grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
            
            last_name_entry = ttk.Entry(form_frame, width=30)
            last_name_entry.grid(row=1, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
            last_name_entry.insert(0, member['last_name'])
            
            # Email
            email_label = ttk.Label(form_frame, text="Email:", style="TLabel")
            email_label.grid(row=2, column=0, sticky=tk.W, pady=(0, 10))
            
            email_entry = ttk.Entry(form_frame, width=30)
            email_entry.grid(row=2, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
            email_entry.insert(0, member['email'])
            
            # Phone
            phone_label = ttk.Label(form_frame, text="Phone:", style="TLabel")
            phone_label.grid(row=3, column=0, sticky=tk.W, pady=(0, 10))
            
            phone_entry = ttk.Entry(form_frame, width=30)
            phone_entry.grid(row=3, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
            if member['phone']:
                phone_entry.insert(0, member['phone'])
            
            # Address
            address_label = ttk.Label(form_frame, text="Address:", style="TLabel")
            address_label.grid(row=4, column=0, sticky=tk.NW, pady=(0, 10))
            
            address_text = tk.Text(form_frame, width=30, height=4)
            address_text.grid(row=4, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
            if member['address']:
                address_text.insert("1.0", member['address'])
            
            # Membership Status
            status_label = ttk.Label(form_frame, text="Status:", style="TLabel")
            status_label.grid(row=5, column=0, sticky=tk.W, pady=(0, 10))
            
            status_var = tk.StringVar(value=member['membership_status'])
            status_combobox = ttk.Combobox(form_frame, textvariable=status_var, width=28)
            status_combobox['values'] = ['active', 'inactive', 'suspended']
            status_combobox.grid(row=5, column=1, sticky=tk.EW, pady=(0, 10), padx=(10, 0))
            
            # Buttons
            button_frame = ttk.Frame(form_frame, style="TFrame")
            button_frame.grid(row=6, column=0, columnspan=2, pady=(20, 0))
            
            save_button = ttk.Button(button_frame, text="Save", command=lambda: self.update_member(
                self.selected_member_id,
                first_name_entry.get(),
                last_name_entry.get(),
                email_entry.get(),
                phone_entry.get(),
                address_text.get("1.0", tk.END),
                status_var.get(),
                edit_window
            ))
            save_button.grid(row=0, column=0, padx=5)
            
            cancel_button = ttk.Button(button_frame, text="Cancel", command=edit_window.destroy)
            cancel_button.grid(row=0, column=1, padx=5)
            
            # Configure grid weights
            form_frame.columnconfigure(1, weight=1)
            
        except mysql.connector.Error as err:
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
            SET first_name = %s, last_name = %s, email = %s, phone = %s, 
                address = %s, membership_status = %s
            WHERE member_id = %s
            """, (
                first_name, last_name, email, phone, address.strip(), status, member_id
            ))
            self.conn.commit()
            cursor.close()
            
            # Refresh the members table
            self.load_members()
            
            # Close the window
            window.destroy()
            
            messagebox.showinfo("Success", "Member updated successfully!")
        except mysql.connector.Error as err:
            if err.errno == 1062:  # Duplicate entry error
                messagebox.showerror("Input Error", "This email is already registered")
            else:
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
            WHERE member_id = %s AND status IN ('issued', 'overdue')
            """, (self.selected_member_id,))
            
            result = cursor.fetchone()[0]
            
            if result > 0:
                messagebox.showerror("Delete Error", "Cannot delete member who has books issued")
                cursor.close()
                return
            
            # Delete member from database
            cursor.execute("DELETE FROM members WHERE member_id = %s", (self.selected_member_id,))
            self.conn.commit()
            cursor.close()
            
            # Refresh the members table
            self.load_members()
            
            # Reset selection
            self.selected_member_id = None
            
            messagebox.showinfo("Success", "Member deleted successfully!")
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")

if __name__ == "__main__":
    root = ThemedTk(theme="arc")  # Using ThemedTk instead of regular tk.Tk()
    app = LibraryManagementSystem(root)
    root.mainloop()