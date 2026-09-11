"""Artifact emission: Terraform repo + signed transcript.

var/out/<user>/<lab>/ plays the student's GitHub repo in dev mode. The
README binds the emitted files to the signed transcript so a reviewer
sees the work is the student's validated output, not bot noise.
"""

import time
from pathlib import Path

from .db import Database
from .signing import TranscriptSigner


def emit_artifacts(
    db: Database, signer: TranscriptSigner, out_dir: Path,
    user, lab: dict, task_results: list[dict], verify_base_url: str = "",
) -> dict:
    payload = {
        "schema": "freetier-prep/transcript/v1",
        "user_email": user["email"],
        "lab_id": lab["id"],
        "lab_title": lab["title"],
        "completed_at": time.time(),
        "tasks": task_results,
        "artifact_repo_ref": f"{user['email']}/{lab['id']}",  # reference only
    }
    doc, sig = signer.sign(payload)
    transcript_id = db.save_transcript(user["id"], lab["id"], doc, sig)

    repo = Path(out_dir) / user["email"].split("@")[0] / lab["id"]
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "main.tf").write_text(lab["hcl"])
    (repo / "transcript.json").write_text(
        '{"payload": ' + doc + f', "signature": "{sig}",\n'
        f' "transcript_id": "{transcript_id}"}}\n'
    )
    verify_url = f"{verify_base_url}/verify/{transcript_id}"
    (repo / "README.md").write_text(
        f"# {lab['title']}\n\n"
        "Infrastructure built hands-on in my own GCP account with "
        "[freetier-prep](https://github.com/allwritesri/freetier-prep).\n\n"
        f"- **Signed transcript:** [{transcript_id}]({verify_url})\n"
        f"- **Tasks validated:** {len(task_results)}/{len(lab['tasks'])}\n"
        "- `main.tf` is the exact infrastructure exercised in the lab; the\n"
        "  transcript signature attests the validated outcomes and merely\n"
        "  references this repo, so verification survives repo changes.\n"
    )
    return {"transcript_id": transcript_id, "repo_path": str(repo),
            "verify_url": verify_url}
