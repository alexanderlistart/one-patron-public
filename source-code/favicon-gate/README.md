# ONE PATRON favicon release gate v0.1

This package preserves the versioned favicon profile, renderer and read-only final-candidate check. It does not create a release, change a page or choose a new icon.

## Profile

For new or byte-changed emitted HTML, use `/favicon-v2.ico` first (16, 32 and 48 px), then `/favicon-v2.svg` (`sizes="any"`). The approved touch and pinned-tab icons are optional. Generate the exact declarations with Python 3.9 or later:

```sh
python3 -B source-code/favicon-gate/favicon_gate.py render
```

The four entries in [the policy](favicon-policy-v0.1.json) are frozen exceptions, not alternatives for new pages. The gate verifies their exact path, byte count, SHA-256, favicon declarations and pinned dependencies on every release check. Renaming an exception or replacing it with newly conforming HTML does not make it eligible. Unchanged unregistered HTML is not re-audited.

## Required final-candidate handoff

Run the finalizer on the **final generated asset tree**, after all generators and post-processing, and **before** sealing, signing or handing off a candidate for upload. The standard local build invokes it unconditionally. Archived builders, manually assembled bundles and direct signing or publishing commands do not invoke it automatically: the operator **must run the same finalizer explicitly** before proceeding. This repository does not contain the private production builder, and this local check does not enforce policy on external commands.

```sh
python3 -B source-code/favicon-gate/finalize-candidate.py \
  --root "$final_generated_assets" \
  --baseline-inventory "$verified_release_inventory" \
  --baseline-sha256 "$accepted_inventory_digest"
```

Use the accepted previous release inventory (a `generated` map from paths to `bytes` and `sha256`) and the digest recorded by the release operator. **The public `site/` tree is not that inventory, a canonical production input, or proof of live production bytes.** Never use it as a substitute. The inventory and any receipt belong outside the generated asset tree. Do not commit either one or the resolved local paths printed by the finalizer.

Only exit zero with `FAVICON_GATE_PASS` qualifies for handoff. Record the returned `candidate_sha256` locally. Re-run with `--expect-candidate-sha256 "$accepted_candidate_digest"` when rechecking that candidate. Before a Wrangler handoff, also pass `--wrangler-config "$selected_config"` to verify that the exact JSON-compatible configuration resolves to the checked asset directory. Use no environment or asset-path override. Treat nonzero exit, a missing receipt or any change to the candidate as a stop; reverify regenerated outputs before sealing. The diagnostic `check` subcommand is not a release check.

This gate discovers new and modified `.html` and `.htm` files and rejects HTML deletion in this profile. It does not cover runtime HTML, other suffixes, actual browser rendering or provider state. It supplements, but does not replace, the authorized release delta and cryptographic integrity checks.

## Tests and copy parity

```sh
python3 -B source-code/favicon-gate/test_integration.py
```

The suite works offline in a clean checkout. It verifies pinned public blobs from `site/` as **fixtures only** and constructs a synthetic candidate and inventory in a temporary directory. It never writes to `site/` or requires an operator's inventory.

Treat this package as the versioned distribution of the gate. Release maintainers must check the installed gate against it before accepting a sync or preparing a release:

```sh
python3 -B source-code/favicon-gate/test_integration.py --compare-install "$installed_gate_directory"
```

That check requires identical validator bytes, identical policy fields after ignoring only status, reference and exception-authority metadata, and identical finalizer bytes except for the digest constant. Each finalizer must pin the bytes of its own policy. Drift fails the check even if the altered policy was re-pinned. Update both copies deliberately and rerun both suites when behavior changes. This comparison is a maintainer step, not an automatic cross-repository control.
