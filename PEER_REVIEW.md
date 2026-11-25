# Peer review on GitHub

Whole-book peer review uses GitHub pull-request approvals. There is no second
website, user database, or deployment.

## One-time repository setup

1. Keep this repository private while unfinished translation work is private.
2. Add each reviewer as a GitHub collaborator or organization member with
   permission to read and review pull requests.
3. In the protection rule or ruleset for `main`, require a pull request before
   merging and require the desired number of approvals (at least two for
   multiple-person review).
4. Enable dismissal of stale approvals when new commits are pushed. This keeps
   every approval bound to the exact version the reviewer read.

GitHub then owns authentication and records the reviewer's account, approval,
date, review text, and commit.

## Review one book

1. Finish the book on a branch and run:

   ```sh
   python3 tools/verify.py <book>
   ```

2. Confirm that the translation stage is `ready`. Verification never approves
   the Spanish and never writes `done`.
3. Push the branch and open a pull request using
   `.github/PULL_REQUEST_TEMPLATE/book-peer-review.md`.
4. Request the required reviewers.
5. Each reviewer reads the entire `translation/{nt|ot}/<book>.md` file, checks
   the source packet or alignment where needed, and submits GitHub's
   **Approve** review only if they personally approve the translation.
6. If the translation changes, reviewers reread the affected material and
   approve the new commit. The stale-approval rule removes the old approval.
7. Merge only after the configured number of current approvals is present.

## Canonical status boundary

GitHub peer approvals are review evidence; they do not automatically edit
`STATUS.md`, approve alignment, or mark a book `done`. The repository's
existing named-human `ready` → `done` control remains governed by
`DATA_CONTRACT.md`. Automation must never infer `done` from a pull request.

For a book that is already on `main`, make any requested review corrections on
a new branch and open the review pull request from that branch. If no change is
needed, record the review in a GitHub issue that names the book and exact commit;
each reviewer gives a named approval comment there. Future books should enter
`main` through the pull-request workflow so GitHub's formal approval control is
available.
