import { formatStatusRow, statusRow } from "./bookWorkflow.js";

// Fetch updates tracking refs only. Never merge, rebase, commit, or push here.
export async function readSourcePublication({ runGit, book, translation, alignment, liveRow }) {
  const fetched = await runGit(["fetch", "--quiet", "origin", "main"], {
    allowFailure: true, timeoutMs: 15000
  });
  if (!fetched.ok) return {
    checked: false, bookOnMain: false,
    message: "Could not check the source repository on GitHub. Local commits do not confirm that the LPF website has received this book."
  };
  const [counts, ledger, content, branch] = await Promise.all([
    runGit(["rev-list", "--left-right", "--count", "HEAD...refs/remotes/origin/main"], { allowFailure: true }),
    runGit(["show", "refs/remotes/origin/main:STATUS.md"], { allowFailure: true }),
    runGit(["diff", "--quiet", "HEAD", "refs/remotes/origin/main", "--", translation, alignment], { allowFailure: true }),
    runGit(["symbolic-ref", "--quiet", "--short", "HEAD"], { allowFailure: true })
  ]);
  const match = counts.stdout.match(/^(\d+)\s+(\d+)$/u);
  if (!match || !ledger.ok || (!content.ok && content.code !== 1)) return {
    checked: false, bookOnMain: false,
    message: "Could not compare this book with the source repository on GitHub."
  };
  const ahead = Number(match[1]);
  const behind = Number(match[2]);
  const remoteRow = statusRow(ledger.stdout, book);
  const bookOnMain = Boolean(content.ok && remoteRow && liveRow
    && formatStatusRow(remoteRow) === formatStatusRow(liveRow));
  const messages = [];
  if (ahead && behind) messages.push(`Source branches have diverged: ${ahead} local commits and ${behind} remote commits. Reconcile both sides before pushing; nothing is merged automatically.`);
  else if (behind) messages.push(`The local source branch is ${behind} commits behind GitHub. Update it before making the next book commit.`);
  else if (ahead) messages.push(`The local source branch has ${ahead} commits not on origin/main.`);
  messages.push(bookOnMain
    ? "This book's source and approval row match origin/main. The LPF website still needs a successful Pages deployment."
    : "This book's source or approval row is not on origin/main. The LPF website cannot show these local approvals until the source changes are pushed. Publishing to cgv-data does not push the source repository.");
  return { checked: true, ahead, behind, branch: branch.stdout, bookOnMain, message: messages.join(" ") };
}
