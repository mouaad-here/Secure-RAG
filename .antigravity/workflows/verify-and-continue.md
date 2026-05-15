# Title: Verify Agent Output and Continue
# Description: Human reviews Artifacts, provides feedback, and triggers next unit.

Step 1: Present all Artifacts from the previous unit (Implementation Plan, Screenshots, Recordings, Walkthrough).
Step 2: Wait for human to review Artifacts and leave comments directly on them.
Step 3: If comments exist, address them one by one and regenerate affected Artifacts.
Step 4: Once human marks unit as approved, read PROGRESS_TRACKER.md to identify the next unit.
Step 5: Trigger `/build-unit` for the next unit spec.
