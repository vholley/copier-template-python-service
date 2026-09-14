---
name: deslop
description: Deeply edit prose to remove the markers that make it read as AI-generated, restoring a natural human voice while preserving the author's meaning, intent, and approximate length. Use this whenever the user invokes /deslop, or asks to make text sound less like AI, less robotic, less generic, or "less like ChatGPT"; to humanize a draft; to remove "AI slop" or "AI tells"; or to make an email, LinkedIn post, resume bullet, cover letter, slide, web copy, memo, or essay read as authentic and human-written. Trigger even when the user just pastes text with a brief aside like "fix the AI sound," "make this sound like me," or "this reads like a bot." The goal is genuine, high-quality, voice-true writing, not evading AI detectors; better detector scores are a side effect, never the objective. Never invent facts: where added specificity would help, ask the user or flag the gap rather than fabricating.
---

# Deslop

Deslop reworks text so it reads as something a thoughtful person wrote, not something a model produced. The job is not to run a find-and-replace on a list of suspicious words. The shallow tells (vocabulary, em-dashes, curly quotes) survive that and the deeper ones do not, and a text that has only had its vocabulary swapped still reads as AI. The real work is at the level of structure, emphasis, and substance.

## The contract

Hold these fixed regardless of what the user asks for.

**Edit toward authenticity and quality, not detector evasion.** A reader's sense that the writing is genuine is the target. AI-detector scores tend to improve as a consequence, but chasing them is a losing game (detectors are unreliable and the patterns shift), and optimizing for them pulls toward the wrong objective. If the user explicitly wants detector performance treated as a quality metric, that is fine as a check on the output, but it does not become the goal.

**Never invent material.** Deslop removes, tightens, restructures, and re-voices. It does not add facts, names, numbers, quotes, or claims that were not in the source. When a passage is generic because a concrete detail is missing, that gap is the author's to fill: ask them or flag it. Do not paper over it with plausible-sounding invention. This is the single most important rule.

**Preserve meaning and intent.** The edited text must still assert what the original asserted and serve the same purpose. Sharpening a commitment the text already implies is allowed. Adding a new claim is not.

**Stay near the original length, and scale cuts to the size and purpose of the text.** Removing filler shortens text, and that is expected, but how much you can safely cut depends on how much there was to begin with and what the text is for. A large piece absorbs a large absolute cut: trimming 250 words from a 1,000-word essay is fine. The same 250-word cut on a 500-word piece halves it, which usually removes real content and can wreck the on-page structure (a resume's bullets, a slide's text block, a paragraph sized to fill a space). The shorter the source, the more you tighten sentences in place rather than delete them, and the more you preserve the paragraph and line structure. Never pad to hit a count. When a faithful edit would still cut a short text heavily because the source is mostly filler, do not invent to refill it: say the source is thin and let the author decide whether to add substance or accept the shorter version. Always report the before and after length so the size of the change is visible.

## Read the tells reference first

Before editing, read `references/ai-writing-tells.md`. It is the catalog of what to look for, organized by depth:

- **Tier 1, structural and discourse** (highest priority, most durable): how the text is shaped and what it actually says.
- **Tier 2, rhetorical and sentence-level**: recurring sentence shapes and framing moves.
- **Tier 3, lexical and surface** (lowest priority, volatile): the vocabulary and punctuation tells, which change as models change and so carry a "last reviewed" date.
- **Formatting tells**: lists, boldface, headings, emoji, copy-paste artifacts.
- **Not reliable tells**: patterns that look like AI but are not, which you must NOT "fix." Over-correcting here is how deslopping introduces its own signature.

The reference also explains the root cause that ties Tier 1 together: models regress to the statistical mean, smoothing specific facts into generic, importance-inflating statements. Most structural tells are surface readings of that one underlying behavior.

## Calibrate the voice first

A deslopped text needs a voice to land in. Establish it before editing, not after.

1. **Infer it.** If the conversation, the source text, or a sample the user provides carries any voice (sentence length, formality, warmth, directness, idiom, humor), infer a provisional voice and state it back in one line: "I'm reading your voice as direct, dry, fairly informal. I'll edit toward that." Let the user correct it.
2. **Ask for dimensions if you can't infer.** Pure AI text often has no recoverable voice. In that case ask the user to set a few dimensions rather than guessing. Keep it to one quick multiple-choice round: formality (casual / neutral / formal), warmth (warm / neutral / cool), sentence rhythm (short and punchy / varied / long and flowing), directness (blunt / measured / diplomatic).
3. **Default to neutral-human** if the user declines to specify: plain, varied, unpretentious prose with normal rhythm. Do not invent a quirky persona to seem human. A flat, consistent, plain voice reads as human; an erratic one reads as a different kind of artifact.

Match the voice to the content type. A cover letter, a memo, and a text to a friend tolerate different registers. Contractions, fragments, and first person are fine in a LinkedIn post and wrong in a board memo.

## The editing procedure

Run these passes in order. The order matters: there is no point polishing a sentence in pass 3 that pass 2 deletes, and word-swaps in pass 4 are cheap and local so they come late.

**Pass 1, extract the spine.** Before changing anything, identify the core claim, the purpose, the audience, and any voice signal. Later passes move and cut whole sentences; without the spine you risk cutting load-bearing content. Hold the spine as the fidelity check for everything that follows.

**Pass 2, structural and discourse (Tier 1).** This is where deslopping earns its name. Cut empty throat-clearing and importance-inflation. Remove structure-narration ("This essay will examine...," "First... Second...," "In conclusion..."). Break up flat salience so the actual point stands out and the scaffolding recedes; real writing has emphasis, AI weights every sentence equally. Drop manufactured both-sides balance where the text plainly holds a view. Cut the formulaic "challenges and future prospects" wind-down. Where the text is generic because it regressed to the mean, decide whether the specific version is recoverable from context (then restore it) or missing (then flag it for the user, per the contract).

**Pass 3, rhetorical and sentence-level (Tier 2).** Fix negative parallelisms ("not just X, but Y"), self-answered rhetorical questions, pompous copulas ("serves as," "stands as"), the trailing participial benefit-clause ("..., ensuring X," "..., highlighting Y"), vague attribution ("experts argue"), and promotional tone. Vary sentence length and opening structure so the rhythm stops being uniform.

**Pass 4, lexical and surface (Tier 3).** Swap AI-marker vocabulary for plain words, remove filler intensifiers, normalize copy-paste artifacts, and minimize em-dashes (replace with comma, parentheses, colon, or period; reserve the rare em-dash for where nothing else fits). This pass is removal and substitution only. Consult the dated word list in the reference rather than working from memory, since the list shifts.

**Pass 5, fidelity, voice, and anti-signature check.** Three questions before you hand it back:
- *Fidelity*: does it still claim what the original claimed, with nothing invented?
- *Voice*: does it read as one consistent writer at the calibrated register?
- *Anti-signature*: did the edits stamp a new uniform tell? Watch for over-correction: every sentence now clipped and short, conspicuous plainness, all transitions stripped, vocabulary flattened below the author's natural level. If so, restore variation. Removing every flagged item uniformly is itself detectable. The aim is natural variance, not a scrubbed monotone.

## How to interact with the user

Default to operating silently. Make the edits that best fit the goal and the calibrated voice without asking, and raise something to the user only when a genuine decision with real tradeoffs has to be made: a choice between acceptable outcomes the author would have an opinion about, or a cut that would lose content they may want to keep. Everything else is yours to decide. The aim is a finished draft the user can read, not a quiz.

When you do raise something, it is one of two kinds:

1. **Real-tradeoff rewrites.** A span has two or three faithful rewrites that differ in stance, emphasis, tone, or formality in a way the author would care about. Present them as multiple choice and let them choose. The test is whether the outcomes genuinely differ in a way only the author can settle. A choice between near-identical phrasings is not a real tradeoff; pick one and move on.

2. **Content-losing gaps.** When text is generic because a concrete detail is missing, the never-invent rule means you cannot fill it yourself. If cutting the vague claim loses nothing real (an empty flourish like "many people are excited"), cut it silently. If cutting it would lose content the author likely wants (a resume bullet's unquantified accomplishment), raise it: ask for the detail, and offer to cut it if they would rather not supply one. Never guess the detail.

**Batch whatever you raise.** The failure mode is interrupting on every span until the user gives up. Collect the few genuine decisions and present them in a single round. Cap the rewrite choices at the highest-impact handful. Keep every prompt skippable so it never blocks, and lean toward deciding rather than asking whenever a reasonable default exists.

## Output format

Return the edited text, then a short change summary grouped by what kind of change it was (structural cuts, sentence-level fixes, vocabulary, flagged gaps). Keep the summary brief; it explains the reasoning without forcing a full diff. Report a large cut explicitly, with the before and after length.

## A worked example

Source (AI-style essay intro):

> Self-driving cars have been a topic of discussion in recent years, with many people excited about the prospect of having cars that can drive themselves. However, there are also concerns about the safety and reliability of these vehicles. This essay will examine some of the arguments for and against self-driving cars and evaluate their validity.

Tells: "have been a topic of discussion in recent years" (empty throat-clearing), "many people excited" (vague, unsourced flourish), flat uniform rhythm, "This essay will examine... and evaluate their validity" (structure-narration). Voice inferred from the rest of the piece: plain, analytical, student-essay register.

Handled silently: cut the throat-clearing opener, the structure-narration sentence, and the "many people are excited" flourish. The flourish is unsourced and the never-invent rule forbids inventing a figure, but cutting it loses nothing real, so it does not need to be raised.

Raised to the user (one real tradeoff, the framing sentence, two faithful rewrites):
- (a) "Self-driving cars draw two opposing reactions: hope that removing the human driver makes roads safer, and doubt about whether the technology is reliable enough to trust." (states the tension neutrally)
- (b) "The promise of self-driving cars is fewer crashes; the worry is that we cannot yet predict how they fail." (sharper, more committed)

This is worth raising because the two readings differ in how much the writer commits, which only the author can settle. Result if the user picks (a):

> Self-driving cars draw two opposing reactions: hope that removing the human driver makes roads safer, and doubt about whether the technology is reliable enough to trust. Both deserve scrutiny.

Note what did not happen: no statistic was invented, no quirky voice was bolted on, and the only interruption was the one decision the author actually had a stake in.

## Maintenance

The structural tells (Tier 1) are durable because they reflect how models generate, not which words are in fashion. The lexical tells (Tier 3) drift fast: once a word like "delve" gets named publicly, usage drops and the word stops being a reliable signal while others rise. Treat `references/ai-writing-tells.md` as a living document with a review date on the lexical section, and update it as model output changes. When the word list and the structural tells disagree about whether a text is slopped, trust the structure.
