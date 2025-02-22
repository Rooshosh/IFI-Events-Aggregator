import logging
import os
import sys

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.utils.deduplication import deduplicate_database, DuplicateConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    # Run deduplication
    config = DuplicateConfig()
    duplicate_count, merged_events = deduplicate_database(config)
    
    print(f"Found and merged {duplicate_count} duplicate events")
    print(f"Database now contains {len(merged_events)} unique events") 