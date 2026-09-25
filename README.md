### Administration

Administration Management System AMS

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app administration
```

### Updating Flat Rent Request to Flat Request

Deploy the complete app revision, including the new `flat_request` package and both
rename patches. From the Bench directory, run:

```bash
bench --site admin.cscec.live backup
bench --site admin.cscec.live migrate
bench --site admin.cscec.live clear-cache
bench restart
```

The pre-schema patch renames the existing DocType and table. The post-schema patch
migrates the three contract/request link fields to `flat_request` and updates stored
script references. Existing request IDs and the `FRQ` naming series are retained.
The Desk route is now `/app/flat-request`; refresh the browser after deployment.
Do not create a separate Flat Request DocType before migrating.

### Restoring the Document Approval tab

Deploy the complete app revision and run `bench --site admin.cscec.live migrate`,
then `bench --site admin.cscec.live clear-cache` and `bench restart`.
Hard-refresh the Flat Request form after deployment. The migration repairs the
approval tab layout after saved customizations are synchronized, and keeps it
visible before the first workflow action. Existing approval rows are retained.
The table shows status, approving role, user, full name, date, note and attachments.
Workflow notes are optional. Use **Attach Files** in the action dialog, upload one
or more files, then confirm. Attachment links are recorded on that action's
approval row. Uploaded files remain attached to the request if the action is
cancelled, but no approval row is created.

### Add Flat to Contract approval workflow

The active workflow is `Add Flat to Contract Approval`. The Accommodation
supervisor requests approval from Draft, sending the document to Administration
Manager, then General Director, then VP-General. VP-General approval submits the
document. Administration Manager reviews return to Admin Team leader, where the
Accommodation supervisor can approve it back to Administration Manager. Director
and VP reviews return to Administration Manager; their rejection ends at Rejected.

Both forms use the same optional-note and multiple-attachment dialog. Each action
records its status, role, user, full name, date, note and attachments in Document
Approval. Existing submitted documents retain their submitted status and are
assigned Approved during installation of the workflow, without invented audit rows.

Deploy all files, then run from the Bench directory:

```bash
bench --site admin.cscec.live backup
bench build --app administration
bench --site admin.cscec.live migrate
bench --site admin.cscec.live clear-cache
bench restart
```

Hard-refresh Desk to load the shared approval dialog. Migration installs the new
workflow once and repairs both approval-tab layouts on subsequent migrations.

### Flat Contract legal approval

Only Legal User can create Flat Contracts. Drafts can be saved without a contract
file, but **Request** requires **Attach Contract**. The workflow is Draft → Legal
Manager → Admin Team leader → Administration Manager → General Director →
VP-General → Approved. Legal Manager can Review back to Legal User, who can Request
again. From Admin Team leader onward, review/rejection routing matches Add Flat to
Contract. Only final approval submits the document.

Document Approval records every action with role, user, date, optional note and
attachment links. The existing Legal User/Legal Manager attachment restriction
also applies to attachments in the workflow dialog. Deploy and run the build,
migrate, cache-clear and restart commands above, then hard-refresh Desk.

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/administration
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.


### License

mit
