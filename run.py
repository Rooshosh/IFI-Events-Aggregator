import os
from src.web import app

if __name__ == '__main__':
    """
    Development vs Production Configuration:
    
    Development:
        - Set FLASK_ENV=development to enable:
            * Debug mode with detailed error pages
            * Interactive debugger
            * Auto-reload on code changes
        Example: FLASK_ENV=development python run.py
    
    Production:
        - Never enable debug mode
        - Use a production WSGI server (e.g., Gunicorn, uWSGI)
        - Set FLASK_ENV=production or don't set it at all
        - Remove or disable test routes (like test-500)
        Example: python run.py
        
    Note: The current setup is intended for development. 
    For production deployment, additional security measures should be implemented.
    """
    # Set debug mode based on environment variable
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    # Run the app
    app.run(debug=debug_mode) 