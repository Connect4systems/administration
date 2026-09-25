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
The table shows status, approving role, user, full name, date and note.

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
