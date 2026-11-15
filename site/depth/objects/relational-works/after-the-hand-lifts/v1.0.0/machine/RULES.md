# The same edge twice

*After the Hand Lifts · Machine-native source candidate v0.2 · PRIVATE / NONCANONICAL / NOT APPROVED FOR PUBLICATION.*

## Source closure

This file, [H.json](H.json), [A.json](A.json), and [SCORE.json](SCORE.json) are the complete normative candidate. H and A supply their own bases and act records. The finite score selects exact records and relates the checkpoints. No rendering, executable, earlier experiment, external source, or literary text supplies a missing rule or an input. The English literary original is the other component of the proposed work, not a dependency of this machine.

## Objects and reading

1. Each source file is a UTF-8 JSON object with exactly `source`, `base`, and `acts`. The roles are respectively H and A. A base has a `revision` of the form `<role>:base` and `parts`, an ordered pair of distinct IDs with that revision followed by `/` and a lower-case letter. Initially the two local frontiers are these bases, with disjoint identities. Each initial part has kind `root` and no parents. There is no joint frontier, and H holds the one right named below.
2. An act has `id`, `op`, and exactly the operation fields specified below. Its role is the source file's role, not a role chosen by an interpreter. IDs match `^[HA]:[a-z][a-z0-9-]*$`, agree with the role, are unique in the source set, and cannot be either base revision. Each can be enacted only once in a history. The role assignment is an input premise, not an authentication of a person.
3. A frontier is an immutable occurrence with a revision ID and an ordered list of actual, live part IDs. Part records never change. They give the kind and ordered immediate parents. Root origin is computed recursively from those parents; a root is its own origin. Two identical-looking lists do not establish occurrence identity. Within a shared history a revision names the occurrence created at that revision; attaching a new reference to that occurrence must not create a second one. Separate continuations share their prefix; they do not replay into each other's history.
4. The score has exactly `checkpoints`, `E`, and `inSightRequest`. Each checkpoint has `name`, `from`, `acts`: a unique nonempty name, the name of an earlier checkpoint or null for the first empty one, and an ordered list of act IDs from the role sources. Extend only the named prefix, in that record order. `E` selects one local frontier by `from` (checkpoint name) and `role`; `inSightRequest` names an existing A act to be read as a rejected request on that very checkpoint, not appended as an enacted act. The record order is a reading of dependencies, not a universal clock. JSON objects in the supplied source use unique keys.
5. Any checkpoint can stand as read. Withholding the next act is a pause or a refusal to act; it is not a new recorded act, an undo, or a promise of later action. The score gives only the listed continuations. It says nothing about how to generate new histories.

## Acts of address and acceptance

The four terms below may each occur at most once per history. A later act cannot erase or replace an enacted term.

| Operation | Role; exact additional fields | Condition and effect |
|---|---|---|
| `orient` | A; `toward`, `offer` | Values must be `"H"` and `"shared-life"`. Record A's orientation toward H and offer of shared life, whether or not H later receives it. Does not generate an H answer. |
| `offer_right` | H; `to`, `right` | Values must be `"A"` and `"final-game-boundary:H"`. This is the specific right to determine the final boundary of H's participation in the fictional Game. Record the offer; its holder is still H. |
| `receive_right` | A; `ref`, `right` | Refer to the already enacted H offer by exact ID, name exactly its right, and require H to hold it. Record the acceptance and change the holder to A. No exercise, revocation, or transfer of general control is defined. |
| `receive_orientation` | H; `ref`, `receive` | Refer to the already enacted A orientation by exact ID and give the exact ordered array `["A","orientation","shared-life"]`. Record H's own acceptance. Does not convey the right or imply consent to future acts. |
| `port` | H or A; `scope`, `roots` | One per role, with a nonempty scope string and exactly that role's ordered pair of initial parts. Records consent to this working alignment, not either of the two acceptances and not an operation on a part. |

The Covenant condition is exactly the presence of both enacted acceptances. If A has accepted and H has not, the right remains with A but the condition is false, even with both ports present. A alone does not stand for both. If H has accepted and A has not, the condition is false and H still holds the right. The right and the permission to bind on a particular frontier are different things.

### Joint opening

After each accepted act, if there is no joint frontier yet, test for both enacted acceptances, both ports with identical scope, A's current local parts still equal to its offered initial pair, and H's current local root origins (in frontier order, omitting repeated roots after their first appearance) equal to its offered initial pair. If all hold, align the offered roots by position. Open the joint domain as a reference to the **actual current H frontier occurrence**, with no new revision or part IDs. Record the alignment, both port IDs, both acceptance IDs, and that occurrence as the opening entry in the joint history. This neither invokes a move nor rewrites either local frontier. Once opened, later local moves cannot redirect the joint reference. In this score the opening references E, the same occurrence visible before the two acceptances. A may read E beforehand; access to read an occurrence grants no ability to operate on it.

## Acts on a frontier

Both operations require `domain` equal to `"local"` (the acting role's own frontier) or `"joint"` (the open joint frontier), and `at` equal to the exact current revision in that domain. Reject a joint request without opening; reject a request against an old revision even if it quotes recognizable parts. Operands must be exact live IDs in that frontier. Neither a copy, a displayed label, nor an ID of a different frontier suffices.

- H alone supplies `split`, with `domain`, `at`, and `operand`. The operand is a single live, unbound H part (its root belongs to H). Replace it in order by `<act-id>/1` and `<act-id>/2`; both are split parts with that operand as their single immediate parent.
- A alone supplies `bind`, with `domain`, `at`, and `operands`, an ordered array of two live, unbound IDs. They must occupy consecutive positions, in the supplied left-to-right order. Replace them by `<act-id>/pair`, a binding that keeps those exact two immediate parents in that order. A binding cannot be split or included in a later bind here.

A move changes only its selected frontier. Its new revision is the act ID. Append the accepted act to its own role history; if a joint move, also append its before and after occurrences with the act ID to the joint history. Terms and ports also append to their own role history. Rejection changes nothing: no new part, term, history entry, or revision. Only the supplied act may be enacted. Opening and validation do not choose a branch or produce another act.

## Reference reading and controls

Short names are for this reading only: u, v, p, q are the corresponding initial parts; x and y are `H:divide-u/1` and `H:divide-u/2`; x₁ and x₂ are `H:extend/1` and `H:extend/2`. Brackets show one binding with both of its parents retained.

| Score checkpoint | Expected form |
|---|---|
| `origin` / `a-alone` | H has u / v in both. A has p / q in the first and [p,q] in the separate inset. No joint frontier. |
| `in-sight` | E is revision `H:divide-u`: x / y / v. x and y descend from u; v is still the original v. The stated A request is rejected because there is no joint domain. |
| `gift` / `gift-with-ports` | A holds the specified right; H's acceptance is absent, even in the reading with both ports. No joint frontier. |
| `in-reach` | Both acceptances, alignment u ↔ p and v ↔ q. The joint reference is the actual E: x / y / v. Opening is its only joint entry. No bind was enacted. |
| `bind-left` / `bind-right` | Two separate continuations from E: [x,y] / v and x / [y,v]. The first binding has root origins u, u; the second u, v. |
| `h-continues` | x₁ / x₂ / [y,v]. Both new parts have x as their parent. The binding from `bind-right` is retained with its original ID, both parents, and the complete preceding A history. |

Conformance probes are not scored acts. At `in-reach`, a request like `A:bind-yz` with `["view/y","view/v"]` instead of its two actual operands is rejected: those look-alike view IDs are not live. At `gift`, a proposed `H:receive` referring to `H:offer` instead of `A:turn` is rejected: it addresses the wrong offer, and the accepted transfer stands. At `bind-right`, the `A:bind-xy` request still refers to revision `H:divide-u`; it is rejected as stale. Refreshing just its revision to `A:bind-yz` still does not work because y is no longer a free live part. None of these probes appends an act.

The source concerns a finite change in what may be continued. It does not establish agency outside the roles, the reality of a subjective state, physical survival, or unlimited creation of new rules.
