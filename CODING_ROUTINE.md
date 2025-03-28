# SQL-Agent Coding Routine

This document outlines the standard coding practices and routines to be followed during development of the SQL-Agent project.

## Daily Development Cycle

1. **Session Start**
   - Review the previous session's summary document (`SESSION_SUMMARY_YYYY-MM-DD.md`)
   - Review the current tasks list (`NEXT_SESSION_YYYY-MM-DD.md`)
   - Verify environment setup (virtual environment, dependencies)

2. **During Session**
   - Follow coding standards in CLAUDE.md
   - Use git branches for significant features
   - Add comments for complex logic
   - Write tests for new functionality

3. **Session End**
   - Summarize the day's work in a new `SESSION_SUMMARY_YYYY-MM-DD.md` file
   - Create/update `NEXT_SESSION_YYYY-MM-DD.md` for future tasks
   - Commit all changes with descriptive commit messages
   - Keep work in progress documentation in the appropriate summary files

## Documentation Standards

### Session Summary Files
Session summary files should follow this format:
```
# Session Summary: [Brief Title] (YYYY-MM-DD)

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
```

### Next Session Files
Next session files should follow this format:
```
# Tasks for Next Session (YYYY-MM-DD)

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
- Documentation tasks
```

## Git Practices

### Commit Messages
Commit messages should follow this format:
```
[Concise summary of changes]

- Specific change #1
- Specific change #2
- Specific change #3

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Branching Strategy
- `main` - Stable, production-ready code
- `feature/[feature-name]` - For new features
- `bugfix/[issue-description]` - For bug fixes

## Testing Standards
- Unit tests should be written for all new functionality
- Tests should be run before committing changes
- Tests should cover edge cases and error conditions

## Code Review Process
- All code should be reviewed before merging
- Reviewers should check for:
  - Code quality and style
  - Test coverage
  - Documentation
  - Security implications

## Daily Documentation Update Process
1. Run the automated documentation creation script at the end of each session:
   ```bash
   # Navigate to the scripts directory
   cd scripts
   
   # Run the documentation creation script
   ./create_session_docs.sh
   ```

2. The script will:
   - Create new dated session summary file (SESSION_SUMMARY_YYYY-MM-DD.md)
   - Create new dated next session file (NEXT_SESSION_YYYY-MM-DD.md)
   - Update the symbolic links to point to the latest files
   - Display a summary of actions taken

3. Manually edit the created files to fill in the session details