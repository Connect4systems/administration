# Test-site validation: employee user creation and leave approval

Date: 18 October 2026 (Africa/Cairo)
Site: https://admin.cscec.live/
Account: test@connect4systems.com

## Result

Partial validation completed. User creation fails in the site's outgoing email configuration. Full leave approval routes cannot be completed with the supplied account because it lacks the Employee role required for the initial workflow action.

| Check | Result | Evidence |
| --- | --- | --- |
| Login and Employee form | PASS | Authenticated successfully; test Employee form loaded. |
| Create User dialog | PASS | Email plus Leave Approver, Expense Approver, and Line Manager checkboxes displayed. Only one create-user handler registered. |
| User Manager permission configuration | PASS (configuration) | Employee read/write/select and User read/create/select are deployed. The account has many other roles, so User Manager-only authorization was not isolated. |
| User creation: all optional roles selected | FAIL | Browser returned HTTP 500, SMTPRecipientsRefused, during standard User insertion. |
| User creation: Leave Approver only | FAIL | Same SMTP error through the create-user API. |
| User creation: no optional roles | FAIL | Same SMTP error through the create-user API. |
| Default Employee roles, selected roles, project permission, default Employee permission, and Administration-only modules | BLOCKED | Failure occurs before the application's provisioning steps execute. |
| Two-level manager requirements and user mapping | PASS | Missing first approver and duplicate managers rejected; distinct managers mapped to their Users. |
| One-level configuration | PASS | Second Employee approver and second User approver cleared. |
| No Approval Required configuration | PASS | Both Employee approvers and both User approvers cleared. |
| New leave configuration snapshots | PASS | LWP drafts stored the appropriate no-approval, one-level, and two-level configurations. |
| Request employee / approval snapshot changes | PASS | Changes rejected on all three saved drafts. |
| Direct approval from Open | PASS | Rejected with HTTP 403 on all three drafts, even though the supplied account has HR Leave Approver. |
| Submit for Approval | BLOCKED | Workflow get_transitions returned no actions; apply_workflow returned WorkflowTransitionError. Supplied account lacks Employee. |
| No-approval direct-to-HR route | PASS (configuration), BLOCKED (execution) | Deployed transition targets Pending HR Approval, but initial submission cannot be exercised. |
| Full one-level / two-level approval, HR final approval, rejection, cancellation, and assignment handoff | BLOCKED | Cannot enter pending workflow states with the supplied account. |
| Preserve System Manager's later edits | NOT TESTED live | Supplied account lacks System Manager; initial user provisioning did not complete. |

## Findings

1. **Welcome email prevents user creation.** The SMTP server rejects the sender with `550 5.1.0 <test@connect4systems.com>: Sender address rejected: User unknown`. The exception originates in standard User creation, before Employee linking and the custom role/module/permission setup.
2. **Failed creation leaves partial User records.** Each failed request left a User in the database while the Employee remained unlinked. A retry would encounter an existing user rather than a clean new-user creation. The test-created partial Users are included in cleanup.
3. **Applicant workflow access is missing on the supplied account.** Its boot roles include User Manager, HR User, HR Manager, Leave Approver, and HR Leave Approver, among many others, but do not include Employee or System Manager. The initial Submit for Approval transition requires Employee.

## Test data and evidence

Only new, clearly named QA Employees and LWP draft applications were used. No existing employee was edited and no leave was approved or deducted from a paid allocation. Test email addresses used the reserved `example.invalid` domain, with no real recipient.

- `create-user-dialog.png`: browser dialog with all three optional roles checked.
- `create-user-result.png`: browser SMTP error.
- `checks.json`: individual server-side validation outcomes.
- `test-records.json`: temporary records created for this run.
- `cleanup.json`: deletion and absence verification results.

## Cleanup

All 3 temporary Leave Applications, 3 Employees, and 3 partial Users were deleted; subsequent reads confirmed each record was absent. Email Queue inspection returned HTTP 403, so test email queue/log remnants could not be inspected or removed with this account.

## Required to complete testing

Correct the test site's outgoing email sender (or configure an appropriate test mail sink), and provide an applicant account with Employee plus the necessary management/HR test actors. A separate account with only User Manager and the normal baseline roles is needed to isolate User Manager permissions. Rerun successful creation and all three leave routes after these prerequisites are ready.

No application code or live mail/role configuration was changed during this validation.
