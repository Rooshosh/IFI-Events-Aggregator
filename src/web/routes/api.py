from flask import Blueprint, jsonify, request
import subprocess
import sys
import os
from pathlib import Path
import logging
from typing import Optional, Dict, Any
import io
from contextlib import contextmanager

# Configure logging
logger = logging.getLogger(__name__)

# Create the blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Path to the events.py script
EVENTS_SCRIPT = Path(__file__).parent.parent.parent.parent / 'scripts' / 'events.py'

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
        env['LOG_TO_STDOUT'] = '1'     # Custom flag to make script log to stdout
        
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
        if result.stderr.strip():
            output.append(result.stderr.strip())
            
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
        if e.stderr.strip():
            output.append(e.stderr.strip())
        return {
            'status': 'error',
            'error': '\n'.join(output),
            'command': ' '.join(cmd)
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'command': ' '.join(cmd)
        }

@api_bp.route('/events/fetch', methods=['POST'])
def fetch_events():
    """
    Fetch events from specified source(s).
    
    Query Parameters:
        source: Source to fetch from (default: 'all')
        live: Force live data fetch (default: False)
        no_store: Don't store in database (default: False)
        detailed: Show detailed information (default: False)
        quiet: Reduce output verbosity (default: True)
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
        quiet=data.get('quiet', True),
        snapshot_id=data.get('snapshot_id'),
        debug=data.get('debug', False)
    )
    
    return jsonify(result)

@api_bp.route('/events/list', methods=['GET'])
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
def clear_events():
    """
    Clear events from the database.
    
    Query Parameters:
        source: Source to clear (default: 'all')
        quiet: Reduce output verbosity (default: True)
    """
    data = request.get_json() or {}
    source = data.get('source', 'all')
    
    result = run_events_command(
        'clear',
        source,
        quiet=data.get('quiet', True)
    )
    
    return jsonify(result)

@api_bp.route('/events/show/<event_id>', methods=['GET'])
def show_event(event_id):
    """
    Show a specific event.
    
    Path Parameters:
        event_id: Event ID to show, 'r' for random, or 'n' for next
    """
    result = run_events_command('show', event_id)
    return jsonify(result)

@api_bp.route('/events/deduplicate', methods=['POST'])
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