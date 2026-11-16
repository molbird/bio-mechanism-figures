# Controlled image evaluation

Evaluate actual images, not prompts. A reference is a comparison artifact, not
automatically perfect ground truth.

1. Define realistic factual briefs before inspecting results. Match content,
   density, resolution and generation budget between with-skill and baseline.
2. For text-only tests neither condition receives the reference pixels. If testing
   style-conditioning, give both the same authorized reference and record the mode.
3. Use independent executors when available. Keep generation settings equal;
   record actual tool/model data, not guessed model names or invented time/tokens.
4. Randomize neutral image IDs before grading. Give graders only the factual brief,
   images and rubric; require visual evidence and uncertainty notes.
5. A critical scientific failure rejects a candidate regardless of aesthetic score.
   Score each dimension 0–4 with explicit anchors and compute a weighted total:

| Dimension | Weight |
|---|---:|
| Scientific identities, directions and stoichiometry | 35 |
| Spatial/compartment correctness | 20 |
| Mechanism clarity and information density | 15 |
| Labels, typography and readability | 15 |
| Restrained consistent visual finish | 10 |
| Component separability for later editing | 5 |

The last criterion is preparation for editing, not proof that a PNG is editable.
Dimensions and hashes can be checked deterministically; biological meaning and
beauty require inspection. Word counts, pixel similarity and successful tool calls
do not establish scientific quality.

Use the same score anchors for every candidate: 0 = absent or fundamentally wrong;
1 = major defects make that dimension unreliable; 2 = partly successful but with
substantial visible omissions or ambiguity; 3 = sound overall with minor defects;
4 = the full supplied requirements for that dimension are clearly met. Half-points
can express an intermediate judgment. Name the visible evidence rather than
assigning a score from reputation or generation method. Any critical failure still
blocks selection even when other dimension scores are high.

6. Inspect style consistency across sets and retain per-task failures/ties.
7. Repair observed recurring weaknesses, retain all versions and grade repairs
   without revealing identity. Improve general decision rules rather than memorizing
   test answers. Include a held-out biological mechanism/context.
8. Stop within the revision budget when critical checks pass and gains plateau.
   Report best among tested candidates, with sample size and limits; one draw does
   not establish population-level superiority or a global optimum.

Keep large images, local source paths, transcripts, pair mappings and reviewer
judgments in the evaluation workspace, outside the portable skill. Produce an
accessible comparison viewer and retain original scores before summarizing them.
