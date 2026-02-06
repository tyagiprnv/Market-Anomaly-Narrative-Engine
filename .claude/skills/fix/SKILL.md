## Bug Fix Workflow
1. Ask user for the EXACT error message and status code
2. Reproduce the error by reading the relevant log or endpoint
3. Identify root cause — check for: enum case mismatches, UUID validation, null checks, React hooks order
4. Make the minimal fix
5. Test the fix by running the relevant endpoint or UI action
6. Commit with message: "fix: <description of what was broken and why>"
