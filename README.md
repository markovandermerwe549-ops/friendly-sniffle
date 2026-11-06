# DevSpace

A downloadable Python website with password login, account registration, private file uploads/downloads/deletion, and editable developer profiles. The C++ game source has been replaced. Old game releases remain in GitHub's release history.

## Download the 2.2 GB edition

From the latest **DevSpace** release, download all four files into the same folder:

1. `DevSpace.zip.part1` (1,100,000,000 bytes)
2. `DevSpace.zip.part2` (1,100,000,000 bytes)
3. `SHA256.json`
4. `unpack.py`

Install Python 3.11 or newer from python.org, then run `python unpack.py` (`python3 unpack.py` on Linux/macOS). The script verifies both parts, joins them, and extracts the website. Windows: open `DevSpace/start.bat`. Linux/macOS: `python3 DevSpace/server.py`. Open **http://127.0.0.1:8080** in your browser. No pip dependencies are needed.

**The two archive parts together are exactly 2,200,000,000 bytes (2.2 decimal GB, approximately 2.049 GiB).** GitHub's per-asset size limit requires splitting the archive. The ZIP contains clearly labeled zero-filled `download-size-padding` files to satisfy the requested download size. These bytes add no features; the unpacker skips padding. The small manifest and unpack script are additional bytes. Allow around 4.5 GB of free disk space while joining. You can delete the download parts after extraction.

For a small source-only download, use Code → Download ZIP and run `server.py`; this has the same website features without padding.

## Requested developer account

- Username: **hellodev**
- First launch asks you to set the password privately in the terminal. Enter the password requested in the conversation to use those credentials.
- Role: **developer**

Created only when initializing a new data directory. Confirm the password when prompted; there is no password or password hash embedded in source or releases. Passwords are salted PBKDF2-SHA256 hashes with 600,000 iterations. Sessions expire after 24 hours; session identifiers are hashed in the database. The initial password is not published in this repository. For a publicly reachable deployment set `DEVSPACE_INITIAL_PASSWORD` to a private value **before the first launch**.

Users may register their own member accounts. All signed-in users can browse profiles and edit their own profile. Role is assigned by the server; profile updates cannot grant developer access. Files are private to the uploader, including from other developer accounts. Uploaded files always download as attachments and are not executed or served as website assets.

## Storage and settings

- Upload limit: **100 MiB per file**; total server upload quota: **5 GiB**.
- 2.2 GB is the distribution size, not an upload limit or storage allowance.
- SQLite database and uploads live in `data/` (ignored by Git).
- `DEVSPACE_DATA`: alternate data directory.
- `DEVSPACE_HOST`: default `127.0.0.1`.
- `PORT`: default `8080`.
- `DEVSPACE_INITIAL_PASSWORD`: supply the developer password on a fresh database without the interactive prompt.
- `DEVSPACE_HTTPS=1`: set Secure on session cookies when running behind HTTPS.

This release is a local, self-hosted website, not a live GitHub Pages website. GitHub Pages cannot execute its Python backend. For internet deployment, use a maintained Python hosting setup with HTTPS and persistent storage; the bundled standard-library server is intended for local use. Use a private initial password for any internet-facing installation.

## Validation and release

```sh
python -m unittest discover -s tests -v
node --check static/app.js
```

Tests cover real HTTP login, password hashing, CSRF, role assignment, private file isolation, upload/download/delete, profile editing, logout, and blocked data paths. In restricted environments without sockets, `DEVSPACE_TEST_IN_MEMORY=1` runs the same request handling checks without binding a port. JavaScript syntax checks require Node only during development, not when running the website.

Every push to main runs tests, constructs and verifies the exact-size ZIP, splits it, publishes checksums, and creates a DevSpace release. Packaging and unpacking need Python 3.11+. Rebuild manually with `python scripts/package.py`. To smoke-test a small package, pass a byte count: `python scripts/package.py 2000000`.
