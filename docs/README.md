# Project Documentation

This directory contains project documentation, architectural decisions, and future feature specifications.

## Directory Structure

- `/docs/features/` - Detailed specifications for future features and enhancements
  - Contains markdown files describing planned features, their requirements, and implementation details
  - Example: `poster-upload.md` describes the event poster upload feature

- `/docs/architecture/` - Documentation about system architecture and design
  - System component diagrams
  - Data flow descriptions
  - Technology stack decisions

- `/docs/decisions/` - Architectural Decision Records (ADRs)
  - Records of important technical decisions
  - Reasoning behind architectural choices
  - Format: `YYYY-MM-DD-decision-title.md`

## Usage

- When planning new features, create a new markdown file in `/features/`
- For major architectural decisions, create an ADR in `/decisions/`
- Keep documentation up to date as the project evolves
- Reference these docs in commit messages when implementing related changes

## Best Practices

1. Keep documentation concise but comprehensive
2. Update docs when implementing related features
3. Use markdown for consistent formatting
4. Include diagrams when helpful (can use Mermaid or PlantUML)
5. Link to external resources when relevant 