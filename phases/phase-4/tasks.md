# Phase 4 — Task Checklist

## Pre-Implementation
- [x] Read build-sequence.md Phase 4 section
- [x] Read Phase 3 exit receipt
- [x] Verify MongoDB connection (2,532 documents)
- [x] Verify Anthropic API access (Haiku + web search)
- [x] Create plan.md, context.md, tasks.md
- [ ] **Builder approves plan** ← GATE

## Implementation
- [ ] Write enrichment prompt (`prompts/context_enrichment_v1.txt`)
- [ ] Write validation prompt (`prompts/context_validation_v1.txt`)
- [ ] Build enrichment script (`pipeline/09_haiku_enrichment.py`)
- [ ] Commit: prompts and script

## Pilot (25 Schools)
- [ ] Select 25 representative schools from MongoDB
- [ ] Run pilot batch
- [ ] Verify Fairhaven findings against known facts
- [ ] Generate pilot report (`phases/phase-4/pilot_report.md`)
- [ ] Commit: pilot results
- [ ] **Builder reviews and approves pilot report** ← GATE

## Full Batch
- [ ] Run full batch (all 2,532 schools)
- [ ] Monitor progress and cost
- [ ] Handle any failures

## Verification
- [ ] Fairhaven golden school check
- [ ] Distribution summary
- [ ] Sensitivity findings inventory
- [ ] "Other" findings inventory
- [ ] Cost summary
- [ ] Generate verification receipt (`phases/phase-4/receipt.md`)
- [ ] Final commit
