# Advanced Event Merging Strategies

This document outlines potential future improvements to event merging/deduplication logic.

## Current Implementation

The current implementation is simple and timestamp-based:
- Always use data from the newer event (based on `fetched_at` timestamp)
- Only keep old data if the timestamps are identical
- Preserve `id` and `created_at` from the existing database entry

## Potential Future Improvements

### 1. Quality-Based Merging

Define what makes an event entry "better quality" and score events based on:
- Number of non-empty fields
- Description length/content (with special handling of placeholder text like "Mer info kommer")
- Presence of specific details (food, location, spots left, etc.)
- Always choose the higher quality version, regardless of timestamp

### 2. Field-by-Field Smart Merging

Each field gets its own merge logic:
- Description: 
  - Prefer non-placeholder content
  - Consider length and information density
  - Maybe use NLP to assess content quality
- Food/Location/Spots: 
  - Prefer non-null values
  - Consider format and completeness
- Timestamps: 
  - Keep most complete/accurate information
  - Handle timezone edge cases

### 3. Timestamp-Based with Exceptions

Enhanced version of current approach:
- Generally prefer newer data
- Have exceptions for certain fields if old data is clearly better
- Special case handling for placeholder content
- Consider source reliability

### 4. Content Analysis

Use more sophisticated content analysis:
- Compare text similarity between versions
- Detect information loss/gain
- Identify content copying vs. new information
- Handle multilingual content

### 5. Source-Aware Merging

Different strategies based on event source:
- Consider source reliability
- Handle source-specific quirks
- Special handling for known patterns

## Implementation Considerations

When implementing any of these strategies:

1. Performance Impact
   - Cache comparison results
   - Optimize text analysis
   - Consider batch processing

2. Error Handling
   - Graceful fallback for failed comparisons
   - Logging of merge decisions
   - Recovery options

3. Configuration
   - Make thresholds configurable
   - Allow per-source settings
   - Enable/disable features

4. Testing
   - Unit tests for each strategy
   - Integration tests with real data
   - Performance benchmarks

## Example Use Cases

1. Navet Events Evolution
   - Initial placeholder "Mer info kommer"
   - Basic event details added
   - Full description and logistics later
   - Need to handle this progression

2. Location Updates
   - Initial generic location
   - Specific room/building added
   - Address details added
   - Should preserve most detailed version

3. Capacity Changes
   - Initial capacity set
   - Spots filling up
   - Capacity increased
   - Need to track these changes

## Next Steps

1. Implement basic quality scoring
2. Add configuration options
3. Enhance logging for merge decisions
4. Create test suite with real examples
5. Monitor system performance 