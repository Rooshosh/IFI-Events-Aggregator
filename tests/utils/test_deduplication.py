"""Test cases for event deduplication."""

import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

from src.utils.deduplication import are_events_duplicate, merge_events, DuplicateConfig
from src.db import db_manager
from tests.fixtures import create_duplicate_events

@pytest.mark.db
def test_duplicate_detection(db):
    """Test that we can detect duplicate events"""
    events = create_duplicate_events()
    original = events[0]
    duplicate1 = events[1]  # Same title, different time
    duplicate2 = events[2]  # Similar title, same time
    
    # Add events to session so we can modify them
    for event in events:
        db.add(event)
    
    # Ensure all events are in Oslo timezone
    oslo_tz = ZoneInfo("Europe/Oslo")
    for event in events:
        event.start_time = event.start_time.astimezone(oslo_tz)
        if event.end_time:
            event.end_time = event.end_time.astimezone(oslo_tz)
    
    # Test with default config (should detect exact title match)
    config = DuplicateConfig()
    assert are_events_duplicate(original, duplicate1, config)
    
    # Test with more lenient config (should detect similar titles)
    lenient_config = DuplicateConfig(title_similarity_threshold=0.7)
    assert are_events_duplicate(original, duplicate2, lenient_config)

@pytest.mark.db
def test_event_merging(db):
    """Test that events are merged correctly"""
    events = create_duplicate_events()
    original = events[0]
    duplicate = events[1]
    
    # Add events to session so we can modify them
    for event in events:
        db.add(event)
    
    # Ensure all events are in Oslo timezone
    oslo_tz = ZoneInfo("Europe/Oslo")
    for event in events:
        event.start_time = event.start_time.astimezone(oslo_tz)
        if event.end_time:
            event.end_time = event.end_time.astimezone(oslo_tz)
    
    # Merge events
    merged = merge_events(original, duplicate)
    
    # Check that merged event has combined information
    assert merged.title == original.title
    assert merged.start_time == min(original.start_time, duplicate.start_time)
    assert merged.start_time.tzinfo.key == "Europe/Oslo"
    assert (
        merged.source_name in [original.source_name, duplicate.source_name] or
        all(source in merged.source_name for source in [original.source_name, duplicate.source_name])
    ) 