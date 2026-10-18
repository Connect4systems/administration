# Live retest after mailbox and Employee-link updates

Site: https://admin.cscec.live/
Date: 18 October 2026 (Africa/Cairo)
Account: test@connect4systems.com

The end-to-end retest remains blocked. A fresh login was used after the reported changes.

| Check | Observed result |
| --- | --- |
| Login | Successful. |
| User creation with all three optional roles | HTTP 500: SMTPRecipientsRefused. The SMTP response still rejects `test@connect4systems.com` as sender: `550 5.1.0 ... Sender address rejected: User unknown`. The failure occurs before custom Employee linking and role/module/permission provisioning. |
| Employee linked to supplied account | Confirmed an existing Employee is linked. It was read only and was not changed. |
| Employee role on supplied account | Absent in the fresh browser session. Employee Self Service is also absent. User Manager, Leave Approver, and HR Leave Approver are present; System Manager is absent. |
| Temporary no-manager-approval LWP request | Created successfully with Open state and No Approval Required snapshot. |
| Submit for Approval / direct-to-HR | No available transitions; action returns HTTP 417 WorkflowTransitionError because the required Employee role is missing. |
| Full one-level, two-level, HR approval/rejection/cancellation | Still blocked by these prerequisites. |

## Required corrections

1. Ensure outbound mail uses an address the vendor permits. The failing request is still using test@connect4systems.com as sender despite the repaired mailbox being cscec@cscec.live. This result does not establish whether the new mailbox password is valid.
2. Add the **Employee role** to test@connect4systems.com, rather than only linking an Employee record. Refresh role caches / log in again as needed.

## Cleanup

The temporary Employee, partial User left by failed creation, and LWP draft were deleted, and each deletion was verified with a subsequent HTTP 404. No existing employee or application configuration was changed. Test addresses used the reserved example.invalid domain. Email Queue access was already denied in the original run, so mail queue/log remnants are not certified as removed.

See checks.json and cleanup.json for the captured outcomes. The original validation report remains in ../live-test-20261018/report.md.
