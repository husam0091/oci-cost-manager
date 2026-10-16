# Interface 2.1: integration and deployment

The first HTML redesign was delivered as a standalone file. PR #2 changed Cost Analysis and backend behavior but did not integrate the full design into the application shell or home page. Master later incorporated main through PR #3, so the branch contents were identical when the missing UI was reported. The running server and container image could not be inspected from this session.

This correction integrates the new design into the React application: login, sidebar, navigation, header, home overview, service distribution, resource-spend table, compact service-health disclosure, dark theme and mobile layout. Existing detailed dashboard widgets remain at `/analytics` and all existing sections stay accessible.

Overview reads actual OCI billing through `/api/v1/billing/spend`. Service/resource aggregates cover the full scoped result before pagination and keep currencies separate. The Inspect action carries the selected resource and dates into the spend explorer. No demo chart or invented cost is displayed.

Both the login and application footer display **Interface 2.1.0**. Vite emits `/release.json` with UI version, revision and build timestamp. Docker builds accept `VITE_BUILD_SHA`; Compose forwards `BUILD_SHA`. Nginx revalidates HTML and release metadata while caching fingerprinted assets, on HTTP and generated HTTPS configuration.

## Update the existing server

From its repository checkout, after pulling this release, run:

```sh
bash deploy/update-app.sh
```

The helper requires a clean tracked working tree and main/master branch, fast-forwards that same branch, and rebuilds backend, worker and frontend using the existing Compose configuration. It supports an installed Docker or Podman Compose provider and does not remove persistent volumes.

To obtain the helper initially, on an existing master checkout:

```sh
git pull --ff-only origin master
bash deploy/update-app.sh
```

Use `main` in the pull command if the checkout tracks main. Do not switch branches over uncommitted server changes.

Verify:

```sh
git log -1 --oneline
curl -fsS http://localhost:8080/release.json
```

The metadata must say `uiVersion: 2.1.0`; then reload the browser. If the file returns HTML or an older version, the request is still reaching an old frontend image, another server, or a proxy cache. If it shows 2.1.0 but the page is old, compare the host/port and clear the browser or upstream proxy cache. The application version shown by the API is independent of the frontend interface version.

Existing HTTPS configs already written into a running container are replaced when that frontend container is recreated by the rebuild. No automatic remote deployment or live OCI reconciliation was performed in the development session.
