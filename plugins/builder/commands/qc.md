---
description: Run the QC gate on what was just made, before Dex sees it
---
Run the quality-control (QC) gate on: $ARGUMENTS (if nothing is named, the deliverable from this session).

1. Run the checks the thing has: its tests, its validator, its self-test, or a dry run against real data.
2. Hand it to the `qc-reviewer` agent with the request Dex made and the deliverable's location. Ask the agent for findings only.
3. Fix every finding that is real. For any you reject, write one line on why.
4. Open the artifact yourself (the page, the file, the output) and look at it.
5. Report:
   - what was checked and how;
   - what was fixed;
   - every claim labeled **Proven**, **Tested** or **Expected**;
   - what was not verified.

   Keep it to short lines, with the payload at the bottom.
