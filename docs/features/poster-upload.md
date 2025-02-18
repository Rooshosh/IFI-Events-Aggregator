# Event Poster Upload Feature

## Overview
A feature that allows users to submit events by uploading photos of event posters they find on campus. The system will use AI and OCR to automatically extract event information from the images.

## User Flow
1. User visits website on mobile device
2. Takes photo of poster or uploads existing photo
3. Optional preview/crop/adjust
4. Submits image
5. System processes and creates event
6. Optional user verification of extracted data

## System Components

### Frontend Interface
- Mobile-optimized upload page
- Direct camera access
- Image preview capabilities
- Progress tracking

### Backend Services
1. **Upload Service**
   - Handles image uploads
   - Generates submission IDs
   - Queues processing jobs

2. **Image Storage**
   - Cloud storage (e.g., AWS S3)
   - Stores original and processed images
   - Manages image URLs/paths

3. **Processing Pipeline**
   - Image enhancement
   - OCR text extraction
   - AI understanding (GPT-4 Vision or similar)
   - Event data structuring

4. **Event Creation**
   - Database integration
   - Duplicate detection
   - Moderation queue

## Technical Requirements

### Tools & Technologies
- **Frontend**: Mobile-optimized web interface
- **Image Storage**: AWS S3 or similar
- **OCR**: Tesseract/Google Cloud Vision
- **AI Understanding**: GPT-4 Vision API
- **Processing**: Celery/job queue
- **Database**: Existing SQLite + SQLAlchemy

### Database Changes
```python
# Additional fields for Event model
poster_image_url: str  # URL to stored image
submission_type: str   # 'POSTER_UPLOAD', 'SCRAPER', etc.
submitted_by: str     # User identifier or 'SYSTEM'
submission_date: datetime
submission_status: str # 'PROCESSING', 'REVIEW', 'LIVE'
```

## Implementation Phases

### Phase 1: Basic Upload
- Simple image upload
- Manual review process
- Basic storage implementation

### Phase 2: Automation
- OCR integration
- AI processing
- Automatic event creation

### Phase 3: Enhancement
- User feedback loop
- Duplicate detection
- Enhanced image processing

## Future Considerations
- User authentication system
- Mobile app development
- Integration with other event sources
- Advanced moderation tools

## Notes
- Start simple and iterate
- Prioritize user experience
- Maintain data quality through verification
- Consider privacy and data retention policies 