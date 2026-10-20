# Live workflow test ? 20 October 2026

Site: https://admin.cscec.live. Tested through authenticated HTTP sessions and Chromium form views. No source code or deployment changes were made.

## Accounts changed

The following four accounts had their passwords reset to the password supplied by the user. Each login was verified. The administrator test account was unchanged.

| Role | User |
| --- | --- |
| Requester (Employee 360) | essam_mohamed@chinaconstruction.com |
| First approver | ahmed_sabaah@chinaconstruction.com |
| Second approver | noha.saleh@chinaconstruction.com |
| HR approver | fady_atef_atta@chinaconstruction.com |

Employee approval configuration was not changed.

## Blocking failures

1. **Annual leave: second approval fails.** Request HR-LAP-2026-00015, 26 October 2026, progresses through requester submission and first approval. It remains Pending Management Approval, docstatus 0. The configured second approver receives HTTP 403, ?Not allowed via controller permission check,? when approving. The approver can open the form. The first approver's assignment closes and a second-approver assignment opens correctly.
2. **Business trip: first approval fails.** Request 5e6f6n28ku, 27 October 2026, reaches Pending Approval, docstatus 0. The configured first approver receives the same controller permission error when approving. The approver can open the form and has an open assignment. The other business trip test requests reproduce this failure.

The failures occur on legitimate stage transitions, despite correct stored approver snapshots and assignments. The exact deployed cause has not been verified. Local administration/leave_approval.py already contains persisted-stage authorization logic; live deployment parity needs checking before choosing a fix.

## Passed checks

- All four role-specific logins.
- Request creation and submission for annual leave and business trips, with Two Level Approval snapshots.
- Annual leave first approval and routing/assignment handoff to management.
- First-approver rejection of annual leave HR-LAP-2026-00016 (28 October), leaving Rejected/docstatus 0 and closing its assignment.
- Requester self-approval and out-of-stage approver actions are denied.
- Changes to saved approval snapshots are denied for both request types.
- Business trip reason cannot change after requesting approval.
- Each inspected pending request has exactly one open current-stage assignment.
- Pending annual leave has no debit ledger entry; pending business trip has no generated attendance.
- Annual leave overlap validation blocks another live application on the same day.

## Not reached

Second approval completion, final HR approval/rejection, submission, approved-leave ledger effects, trip attendance creation, and post-approval cancellation could not be completed through the normal workflow because of the blockers above. One-level and No Approval Required routes were not exercised.

## Retained test records

| Type | Record | Final observed state |
| --- | --- | --- |
| Annual Leave | HR-LAP-2026-00015 | Pending Management Approval |
| Annual Leave | HR-LAP-2026-00016 | Rejected |
| Business Trip | 5e6f6n28ku | Pending Approval |
| Business Trip | 5enflgusgc | Pending Approval |
| Business Trip | 5f5skan3q7 | Pending Approval |
| Business Trip | 5flf8ckd5g | Pending Approval |

Test records are retained for reproduction. No submitted leave or trip was created. Initial results.json contains three follow-on leave creation failures due to reusing the pending leave date; these are expected overlap validation, not three additional defects. A separate 28 October request verified first-stage rejection.

Evidence: results.json, rejection-check.json, additional-checks.json, first-browser.png and second-browser.png. Passwords and session cookies are not saved in these artifacts.
