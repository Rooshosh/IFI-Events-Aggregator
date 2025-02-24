from flask import Blueprint, jsonify, request, send_file
import subprocess
import sys
import os
from pathlib import Path
import logging
from typing import Optional, Dict, Any
import io
from functools import wraps
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler

# Configure logging
logger = logging.getLogger(__name__)

# Create the blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Path to the events.py script
EVENTS_SCRIPT = Path(__file__).parent.parent.parent.parent / 'scripts' / 'events.py'
LOGS_DIR = Path(__file__).parent.parent.parent.parent / 'logs'

# Create logs directory if it doesn't exist
LOGS_DIR.mkdir(exist_ok=True)
log_file = LOGS_DIR / 'events.log'

# Configure logging to both file and console
handlers = []

# Always add console handler when LOG_TO_STDOUT is set
if os.environ.get('LOG_TO_STDOUT'):
    handlers.append(logging.StreamHandler(sys.stdout))
else:
    # In normal operation, use both file and console handlers
    handlers.extend([
        # Console handler
        logging.StreamHandler(),
        # File handler with rotation (keep 30 days of logs, max 10MB per file)
        RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=30,
            encoding='utf-8'
        )
    ])

logging.basicConfig(
    format='%(message)s' if os.environ.get('LOG_TO_STDOUT') else '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=handlers
)

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        expected_key = os.environ.get('API_KEY')
        
        if not expected_key:
            logger.error("API_KEY environment variable not set")
            return jsonify({'error': 'Server configuration error'}), 500
            
        if not api_key:
            return jsonify({'error': 'API key missing'}), 401
            
        if api_key != expected_key:
            return jsonify({'error': 'Invalid API key'}), 401
            
        return f(*args, **kwargs)
    return decorated_function

@contextmanager
def capture_logs():
    """Capture logs in a string buffer."""
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setFormatter(logging.Formatter('%(message)s'))
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    try:
        yield log_capture
    finally:
        root_logger.removeHandler(handler)

def run_events_command(command: str, *args, **kwargs) -> Dict[str, Any]:
    """
    Run the events.py script with the given command and arguments.
    
    Args:
        command: The command to run (fetch, list, clear, etc.)
        *args: Additional positional arguments
        **kwargs: Additional keyword arguments
    
    Returns:
        Dict containing the command output and status
    """
    cmd = [sys.executable, str(EVENTS_SCRIPT), command]
    
    # Add positional arguments
    cmd.extend(args)
    
    # Add keyword arguments
    for key, value in kwargs.items():
        if value is True:
            cmd.append(f'--{key}')
        elif value not in (None, False):
            cmd.append(f'--{key}')
            cmd.append(str(value))
    
    try:
        # Set environment variables to control logging
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'  # Ensure Python output is not buffered
        # Remove LOG_TO_STDOUT to ensure full logging output
        env.pop('LOG_TO_STDOUT', None)
        
        # Log the command being executed
        logger.info(f"Executing command: {' '.join(cmd)}")
        
        # Run the command with the modified environment
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            env=env
        )
        
        # Combine stdout and stderr for the output
        output = []
        if result.stdout.strip():
            output.append(result.stdout.strip())
            # Split and log each line to preserve formatting
            for line in result.stdout.strip().split('\n'):
                logger.info(line)
        if result.stderr.strip():
            output.append(result.stderr.strip())
            # Split and log each line to preserve formatting
            for line in result.stderr.strip().split('\n'):
                logger.warning(line)
            
        return {
            'status': 'success',
            'output': '\n'.join(output),
            'command': ' '.join(cmd)
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        # Combine stdout and stderr for error output
        output = []
        if e.stdout.strip():
            output.append(e.stdout.strip())
            # Split and log each line to preserve formatting
            for line in e.stdout.strip().split('\n'):
                logger.error(line)
        if e.stderr.strip():
            output.append(e.stderr.strip())
            # Split and log each line to preserve formatting
            for line in e.stderr.strip().split('\n'):
                logger.error(line)
        return {
            'status': 'error',
            'error': '\n'.join(output),
            'command': ' '.join(cmd)
        }
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': error_msg,
            'command': ' '.join(cmd)
        }

@api_bp.route('/events/fetch', methods=['POST'])
@require_api_key
def fetch_events():
    """
    Fetch events from specified source(s).
    
    Query Parameters:
        source: Source to fetch from (default: 'all')
        live: Force live data fetch (default: False)
        no_store: Don't store in database (default: False)
        detailed: Show detailed information (default: False)
        quiet: Reduce output verbosity (default: False)
        snapshot_id: Use existing snapshot ID for Facebook (optional)
        debug: Show debug information (default: False)
    """
    data = request.get_json() or {}
    source = data.get('source', 'all')
    
    result = run_events_command(
        'fetch',
        source,
        live=data.get('live', False),
        no_store=data.get('no_store', False),
        detailed=data.get('detailed', False),
        quiet=data.get('quiet', False),
        snapshot_id=data.get('snapshot_id'),
        debug=data.get('debug', False)
    )
    
    return jsonify(result)

@api_bp.route('/events/list', methods=['GET'])
@require_api_key
def list_events():
    """
    List events from the database.
    
    Query Parameters:
        source: Source to list (default: 'all')
        detailed: Show detailed information (default: False)
    """
    source = request.args.get('source', 'all')
    detailed = request.args.get('detailed', '').lower() == 'true'
    
    result = run_events_command(
        'list',
        source,
        detailed=detailed
    )
    
    return jsonify(result)

@api_bp.route('/events/clear', methods=['POST'])
@require_api_key
def clear_events():
    """
    Clear events from the database.
    
    Query Parameters:
        source: Source to clear (default: 'all')
        quiet: Reduce output verbosity (default: False)
    """
    data = request.get_json() or {}
    source = data.get('source', 'all')
    
    result = run_events_command(
        'clear',
        source,
        quiet=data.get('quiet', False)
    )
    
    return jsonify(result)

@api_bp.route('/events/show/<event_id>', methods=['GET'])
@require_api_key
def show_event(event_id):
    """
    Show a specific event.
    
    Path Parameters:
        event_id: Event ID to show, 'r' for random, or 'n' for next
    """
    result = run_events_command('show', event_id)
    return jsonify(result)

@api_bp.route('/events/deduplicate', methods=['POST'])
@require_api_key
def deduplicate_events():
    """
    Deduplicate events in the database.
    
    Query Parameters:
        source: Source to deduplicate (default: 'all')
        title_similarity: Title similarity threshold (default: 0.85)
        time_window: Time window in minutes (default: 120)
        require_location: Require location match (default: False)
        require_exact_time: Require exact time match (default: False)
    """
    data = request.get_json() or {}
    source = data.get('source', 'all')
    
    result = run_events_command(
        'deduplicate',
        source,
        title_similarity=data.get('title_similarity', 0.85),
        time_window=data.get('time_window', 120),
        require_location=data.get('require_location', False),
        require_exact_time=data.get('require_exact_time', False)
    )
    
    return jsonify(result)

@api_bp.route('/logs/events', methods=['GET'])
@require_api_key
def get_events_log():
    """
    Download the events.log file.
    
    Returns:
        The events.log file as an attachment
    """
    log_file = LOGS_DIR / 'events.log'
    
    if not log_file.exists():
        return jsonify({'error': 'Log file not found'}), 404
        
    return send_file(
        log_file,
        mimetype='text/plain',
        as_attachment=True,
        download_name='events.log'
    )

@api_bp.route('/db/events', methods=['GET'])
@require_api_key
def get_events_db():
    """
    Download the events database file.
    
    Returns:
        The events.db file as an attachment
    """
    db_file = Path(__file__).parent.parent.parent.parent / 'data' / 'events.db'
    
    if not db_file.exists():
        return jsonify({'error': 'Database file not found'}), 404
        
    return send_file(
        db_file,
        mimetype='application/x-sqlite3',
        as_attachment=True,
        download_name='events.db'
    ) 