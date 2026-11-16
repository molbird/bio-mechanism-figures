---
name: bio-mechanism-figures
description: >-
  Generate, revise and scientifically inspect biomolecular and cellular mechanism
  illustrations: signaling, organelles, nanodelivery, molecular binding and
  multi-panel biomedical schematics. Use for 生物分子绘图、细胞机制图、信号通路示意、
  纳米递送图、BioRender风格科研插图 and related graphical abstracts. Produces actual
  images, short verified labels and traceable sources; optionally prepares editable
  artwork. Not for experimental-image synthesis, quantitative plots, microscopy
  analysis or ordinary presentation design.
---

# Biomolecular and cellular mechanism figures

Create an explanatory scientific image whose visual relationships are as carefully
specified as its labels. A beautiful wrong arrow is a failed figure. Prefer clear,
restrained molecular/cellular illustration over decorative complexity.

## Choose the deliverable

- Generate a requested raster illustration with the available built-in image tool,
  inspect the actual result, and deliver its file; a brief alone is not completion.
- Inspect an existing image before editing. Distinguish edit targets from style
  references and preserve approved regions during targeted repairs.
- For editable-only artwork, use native vector/PPT elements where feasible. For
  reconstruction of approved rasters, read [editable-delivery.md](references/editable-delivery.md).
- Keep measurements, microscopy, blots and charts in data-specific workflows.
  Do not label a synthetic illustration as an experimental observation.

Honor the user's language, palette, density, format and approval gates. Defaults
are starting points, not reasons to override an explicit choice. Automatic internal
testing does not authorize publishing or skipping a user-requested checkpoint.

## Establish a small scientific contract

Extract supplied information before asking questions. Record the one-sentence
message, audience, panel roles, exact short labels and source identifiers. Inventory
entities and locations. For each important connection name its start, end,
biological meaning and evidence status. Define critical visual checks, output
size/aspect, raster versus editable format and any approval boundary.

Use supplied sources for facts. Verify unresolved, niche or consequential claims
against primary literature before drawing them as established. Do not invent
mechanisms, chemical structures, dosing, effect sizes or clinical benefits to fill
space. Put necessary model/timing/clinical qualifications in the caption when they
would overload the image. Omit unknown links or mark them proposed. A biological
arrow is not merely a layout arrow.

Read [mechanism-checks.md](references/mechanism-checks.md) for relevant error
families. Apply organism-, cell- and assay-specific biology; nuclear transcription
is not a universal rule for bacteria, mitochondria or every nucleic-acid task.

## Draw a sparse visual argument

Unless the user specifies otherwise:

- Mark subpanels within one composite figure with standalone uppercase English
  letters A, B, C, ... in reading order (left to right, then top to bottom).
  Use black letters in consistent positions. The marker is the letter alone:
  no lowercase, numbers, punctuation, parentheses, prefixes, enclosing circles,
  boxes or badge backgrounds. An explicitly requested marker convention takes
  priority; this rule concerns panel markers, not numbered mechanistic steps.
- Use white background, simple 2D vector-like biomedical forms, smooth contours,
  a few soft semantic colors and restrained local shading. English labels are
  black; white text may appear inside black badges. Separate structure color from
  text color.
- Show recognizable membranes, organelles and molecular interfaces. Avoid glossy
  3D spheres, decorative particles, deep shadows and branches without roles.
  Simplicity should preserve mechanism, not turn the image into plain boxes.
- Keep the scientific graph as internal planning scaffolding. Render proteins,
  ligands and membranes as biological forms, not a network of rounded text pills.
  Containers suit workflows and genuine comparisons; they are not the default
  appearance of every molecule. Prefer panel letters and short object labels over
  extra sentence headings. Do not print editorial instructions such as draft
  status, representation notes or the internal checklist inside the artwork.
- Give the key causal step more space; use a grid for genuinely parallel items.
  Place short labels in whitespace with short leaders. Put explanation in captions.
  Use representative particles/cells rather than repeating them to fill space.
- Make compartments and topology readable first. Separate parallel pathways and
  distinguish carrier, released cargo and measured signal. Make binding convergence
  and independently expressed protein branches unmistakable.
- Declare line semantics. Dashed lines can denote proposed links, transport or
  inset leaders depending on context; do not infer meaning from appearance alone.
- Keep repeated text levels, objects, margins and gutters consistent. Inspect at
  the intended reading size as well as useful zoom.
- Apply the text-color choice to small chemical symbols, icon text and insets as
  well as main labels. Check each leader's visible endpoint against its object;
  drawing the correct cell elsewhere does not make a misplaced leader correct.

If a set needs style approval, make the requested sample first. Reuse an already
approved visual grammar without asking for the same approval again.

## Generate a controlled request

Write a concise prompt: purpose/concept role and reading order; visual grammar
and focal mechanism; each panel's entities, compartments and typed relations;
exact labels and the few critical invariants; requested output and relevant
exclusions. Do not inflate every request with unrelated examples or a fixed number
of panels and labels.

Use `scripts/prepare_brief.py --input brief.json --out prompt.txt` when structured
input prevents repeated transcription. Its graph validation does not prove biology
or replace visual inspection. Free-form prompts also suit simple figures.

Follow the built-in tool's actual schema. Request transparency only when needed.
Do not silently switch model/provider/API because a diagram is difficult. Preserve
the exact returned path rather than guessing the newest file. Record unreported
provider/model versions as unknown.

Use `scripts/record_asset.py` to retain the versioned original image, exact prompt,
reference files/hashes, dimensions and SHA-256. Pass `--request` to preserve the
actual original tool-request JSON; otherwise its request record contains only
declared recorder inputs. Record edit-target/style-reference roles in the brief or
source map. Never overwrite an approved image. A raster wrapped in SVG/PPT remains
raster; enlarged pixels or changed DPI metadata do not create scientific detail.

## Inspect the actual image and repair narrowly

Inspect the complete image and enlarged high-risk regions. Read every label; zoom
before deciding that a small glyph or subscript is wrong. Check entity identity,
meaningful count/stoichiometry, endpoints and compartments. Check T-bars, binding
convergence, barriers, secretion, transcription/translation, context/model and
proposed-versus-established distinctions. Check spelling, color, extra/missing
text, legibility, overlaps, curvature, clipping and duplicate boundaries. Check
panel-marker order and the requested/default marker convention. Check whether the
image strengthens the evidence beyond its sources.

A successful tool call or valid PNG is not scientific acceptance. Mark uncertain
details not assessable instead of passing them from the prompt. A failed critical
relation blocks selection even when the picture is attractive.

Compare the full factual contract as well as the preselected critical list. A
short checklist can miss cargo-in-water versus cargo-in-lipid, the membrane side
of a protein, or a qualification box that wrongly covers two study contexts.
Record those omissions instead of advertising a narrow checklist pass as complete
correctness. For conceptual chemistry, abstract donor markers are safer than
invented skeletal bonds: if no verified bond-level structure was supplied, do not
add one to make the illustration look more technical.

Repair the smallest region that fixes the observed problem. State what changes
and what stays fixed, repeat the critical invariants, then inspect that feature
and its neighbors for regressions. Prefer targeted repairs over regenerating every
correct panel. Normally budget an initial candidate and up to two repairs; honor a
different explicit budget. If critical errors repeat or gains plateau, change the
representation or report the unresolved element instead of promising endless retries.

## Deliver and test reproducibly

Deliver the selected image, brief/prompt, concise caption/source map, version and
review record, plus a file/hash manifest. Supply native sources only when actually
created. `scripts/validate_job.py` checks provenance and current-hash review coverage;
file validity alone must remain `needs_visual_review`.

Across a set, check shared colors, typography and semantic conventions. For skill
improvement, read [evaluation.md](references/evaluation.md): compare actual images
under matched requirements, blind graders, separate critical failures from style
and test an unseen mechanism. Report best among tested candidates, not a global optimum.

For a named journal submission, verify that journal's current official AI-artwork
and disclosure rules. Otherwise describe generative output as a reviewed concept
or design draft, not automatically submission-cleared artwork.
