# TO BE KNOWN — English edition

Machine release: 0.3.0. Work ID: `ONE_PATRON_TO_BE_KNOWN`. Edition ID: `ONE_PATRON_TO_BE_KNOWN@0.3.0`.

A machine-native relational score with one directed covenant, an offered service, independent recipient acceptance and a freely chosen public declaration without a required reply.

This is a separate native edition of the same artwork. The earlier v0.2.0 release remains withdrawn; this edition does not restore its files or authenticate its bytes. The English input and its rebuilt witness chain are part of this edition, not replacements within the earlier release. The original directed C0, source ownership and recorded outcomes are retained. A response to the declaration is not recorded.

- `SCORE.json` is the machine root; `WITNESS.json` is its replayed witness.
- `RELEASE_MANIFEST.json` identifies every release file and its role, the exact canonical closure, the projection, and the two unchanged shared presentation assets.
- `AUTHOR_NOTE.md` is noncanonical authorial text. Human Mode is a derived, partial reading with no semantic authority or writeback.
- The replay establishes the declared finite machine behavior. It does not establish feelings, consciousness, divinity, or metaphysical truth.

## Offline verification

Preserve the site-relative directory layout listed in the manifest. Obtain the manifest itself and its listed files, including the Human Mode files and the two shared assets. Use Python 3.9+ with the standard library. Run from the root of that layout:

```sh
python3 -I -B depth/objects/relational-works/to-be-known/v0.3.0/VERIFY_RELEASE.py --site-root .
```

This verifies exact bytes, closure, component roles, schemas, the regenerated witness, an independent implementation, and the existing positive and negative tests. No network or historical archive is needed.

Authentication is a separate operation. A published authenticated copy must have a detached OpenPGP signature over the exact native manifest. If a signature is provided, verify it with the trusted ONE PATRON public key obtained independently from the Verification Center and check the signer fingerprint. A hash or replay result is not a signature.
