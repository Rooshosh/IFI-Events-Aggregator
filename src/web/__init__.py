from flask import Flask, render_template
from .routes import events_bp

# Initialize Flask app
app = Flask(__name__)

# Register blueprints
app.register_blueprint(events_bp)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500

# Development configuration
app.config['DEBUG'] = True 