import logging
import os
import sys

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.utils.deduplication import deduplicate_database, DuplicateConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    # Create a config with default settings
    config = DuplicateConfig(
        title_similarity_threshold=0.85,  # 85% title similarity required
        time_window_minutes=120,  # Events within 2 hours of each other
        require_same_location=False,  # Don't require exact location match
        require_exact_time=False,  # Don't require exact time match
        ignore_case=True,  # Ignore case in string comparisons
        normalize_whitespace=True  # Normalize whitespace in strings
    )
    
    # Run deduplication
    db_path = os.path.join(os.path.dirname(__file__), '..', 'events.db')
    duplicate_count, merged_events = deduplicate_database(db_path, config)
    
    logger.info(f"Found and merged {duplicate_count} duplicate events")
    logger.info(f"Database now contains {len(merged_events)} unique events") 