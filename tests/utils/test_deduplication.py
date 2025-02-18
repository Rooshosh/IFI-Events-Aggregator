"""Test cases for event deduplication."""

from tests.base import BaseTestCase
from tests.fixtures import create_duplicate_events
from src.utils.deduplication import are_events_duplicate, merge_events, DuplicateConfig
from datetime import datetime
from zoneinfo import ZoneInfo

class TestDeduplication(BaseTestCase):
    """Test cases for event deduplication logic"""
    
    def test_duplicate_detection(self):
        """Test that we can detect duplicate events"""
        events = create_duplicate_events()
        original = events[0]
        duplicate1 = events[1]  # Same title, different time
        duplicate2 = events[2]  # Similar title, same time
        
        # Ensure all events are in Oslo timezone
        oslo_tz = ZoneInfo("Europe/Oslo")
        for event in events:
            event.start_time = event.start_time.astimezone(oslo_tz)
            if event.end_time:
                event.end_time = event.end_time.astimezone(oslo_tz)
        
        # Test with default config (should detect exact title match)
        config = DuplicateConfig()
        self.assertTrue(are_events_duplicate(original, duplicate1, config))
        
        # Test with more lenient config (should detect similar titles)
        lenient_config = DuplicateConfig(title_similarity_threshold=0.7)
        self.assertTrue(are_events_duplicate(original, duplicate2, lenient_config))
    
    def test_event_merging(self):
        """Test that events are merged correctly"""
        events = create_duplicate_events()
        original = events[0]
        duplicate = events[1]
        
        # Ensure all events are in Oslo timezone
        oslo_tz = ZoneInfo("Europe/Oslo")
        for event in events:
            event.start_time = event.start_time.astimezone(oslo_tz)
            if event.end_time:
                event.end_time = event.end_time.astimezone(oslo_tz)
        
        # Merge events
        merged = merge_events(original, duplicate)
        
        # Check that merged event has combined information
        self.assertEqual(merged.title, original.title)
        self.assertEqual(merged.start_time, min(original.start_time, duplicate.start_time))
        self.assertTrue(merged.start_time.tzinfo.key == "Europe/Oslo")
        self.assertTrue(
            merged.source_name in [original.source_name, duplicate.source_name] or
            all(source in merged.source_name for source in [original.source_name, duplicate.source_name])
        ) 