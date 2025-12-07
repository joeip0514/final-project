# Project Delegation Platform

A comprehensive web-based platform for delegating projects and managing the entire project lifecycle from creation to closure.

## Features

### Authentication
- User registration with role selection (Delegator or Recipient)
- Secure login/logout functionality
- Session-based authentication

### For Delegators
- **Project Management**: Create and modify pending projects
- **Delegate Selection**: View quotes from recipients and select delegates
- **Communication**: Real-time messaging during project execution
- **Project Closure**: Accept or return closure files
- **History**: Access historical project list

### For Recipients
- **Browse Projects**: View all available projects for delegation
- **Submit Quotes**: Express willingness to undertake projects with pricing
- **Communication**: Real-time messaging during project execution
- **File Upload**: Upload closure files upon project completion
- **History**: Access historical project list

## Technology Stack

- **Backend**: Python Flask
- **Database**: SQLite (with SQLAlchemy ORM)
- **Frontend**: HTML, CSS, JavaScript
- **File Storage**: Local file system for closure documents

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Run the Flask application:
```bash
python app.py
```

3. Open your browser and navigate to:
```
http://localhost:8080
```

## Usage

### Getting Started

1. **Register an Account**
   - Go to the Register page
   - Fill in username, email, and password
   - Select your role: Delegator or Recipient
   - Submit the form

2. **Login**
   - Use your credentials to log in
   - You'll be redirected to your role-specific dashboard

### For Delegators

1. **Create a Project**
   - Click "Create New Project" on your dashboard
   - Fill in the title and description
   - Save the project

2. **Review Quotes**
   - When recipients submit quotes, click "View Quotes"
   - Review all submitted quotes
   - Select a delegate by clicking "Select This Delegate"

3. **Manage Active Projects**
   - View active projects on your dashboard
   - Use "Messages" to communicate with the delegate
   - When project is complete, use "Close Project" to accept closure

4. **View History**
   - Click "History" tab to see all completed/closed projects

### For Recipients

1. **Browse Available Projects**
   - View all pending projects on the "Available Projects" tab
   - Click "Submit Quote" to express interest

2. **Submit a Quote**
   - Enter your quote amount
   - Add an optional message
   - Submit your quote

3. **Manage Your Projects**
   - Once selected, view your active projects on "My Projects" tab
   - Communicate with delegators via "Messages"
   - Upload closure files when project is complete

4. **View History**
   - Click "History" tab to see all completed projects

## Project Structure

```
login-system/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── project_delegation.db  # SQLite database (created automatically)
├── uploads/              # Closure file storage (created automatically)
├── templates/
│   ├── index.html        # Home page
│   ├── login.html        # Login page
│   ├── register.html     # Registration page
│   ├── delegator_dashboard.html  # Delegator interface
│   └── recipient_dashboard.html  # Recipient interface
└── static/
    ├── style.css         # Main stylesheet
    ├── auth.js           # Authentication logic
    ├── delegator.js      # Delegator functionality
    └── recipient.js      # Recipient functionality
```

## Database Schema

- **User**: Stores user accounts with role information
- **Project**: Stores project details and status
- **Quote**: Stores quotes submitted by recipients
- **Message**: Stores communication messages between users
- **ClosureFile**: Stores uploaded closure documents

## Security Notes

- Passwords are hashed using Werkzeug's security functions
- Session-based authentication prevents unauthorized access
- File uploads are validated and stored securely
- SQL injection protection via SQLAlchemy ORM

## Development Notes

- The application runs in debug mode by default
- Database is automatically created on first run
- Upload folder is created automatically if it doesn't exist
- Maximum file upload size is 16MB

## Future Enhancements

- Email notifications
- File preview functionality
- Advanced search and filtering
- Project templates
- Rating and feedback system
- Real-time notifications
- Export project reports

