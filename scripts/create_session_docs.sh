#!/bin/bash
# Script to create dated session documentation files

# Get current date
TODAY=$(date +"%Y-%m-%d")
TOMORROW=$(date -d "tomorrow" +"%Y-%m-%d")

# Template for SESSION_SUMMARY file
SESSION_TEMPLATE="# Session Summary: [Brief Title] ($TODAY)

## Overview
Brief overview of what was accomplished in this session.

## Key Achievements
1. **[Major Achievement Category]**
   - Specific accomplishment
   - Specific accomplishment

2. **[Major Achievement Category]**
   - Specific accomplishment
   - Specific accomplishment

## Technical Implementation Details
1. **[Implementation Area]**
   - Technical details
   - Design decisions

## Code Modifications
1. **Created New Modules**:
   - List of new files and their purposes

2. **Modified Existing Files**:
   - List of modified files and changes

## Learning Insights
Lessons learned during implementation.

## Next Steps
Brief list of immediate next steps (detailed in NEXT_SESSION file).

See [NEXT_SESSION_$TOMORROW.md](NEXT_SESSION_$TOMORROW.md) for detailed tasks and planning."

# Template for NEXT_SESSION file
NEXT_TEMPLATE="# Tasks for Next Session ($TOMORROW)

## Implemented Features to Review
1. **[Feature Name]**
   - ✅ Completed tasks
   - Next steps

## Critical Issues to Address
1. **[Issue Category]**
   - Specific tasks
   - Expected challenges

## Enhancement Ideas
1. **[Enhancement Category]**
   - Specific ideas
   - Implementation considerations

## Documentation Needs
- Documentation tasks"

# Create session summary file
echo "Creating SESSION_SUMMARY_$TODAY.md"
echo "$SESSION_TEMPLATE" > "../SESSION_SUMMARY_$TODAY.md"

# Create next session file
echo "Creating NEXT_SESSION_$TOMORROW.md"
echo "$NEXT_TEMPLATE" > "../NEXT_SESSION_$TOMORROW.md"

# Update symbolic links
echo "Updating symbolic links..."
cd ..
rm -f SESSION_SUMMARY.md NEXT_SESSION.md
ln -s "SESSION_SUMMARY_$TODAY.md" SESSION_SUMMARY.md
ln -s "NEXT_SESSION_$TOMORROW.md" NEXT_SESSION.md

echo "Done! Created the following files:"
echo "- SESSION_SUMMARY_$TODAY.md"
echo "- NEXT_SESSION_$TOMORROW.md"
echo "And updated the symbolic links."