# AI writing tells: a depth-tiered catalog

Lexical section last reviewed: 2026-06. Structural tells are stable; the word lists drift and need periodic review.

This is the catalog deslop edits against. It is organized by depth, because the depth of a tell predicts both how much it matters and how durable it is. Shallow tells (a word, a punctuation mark) are easy to spot, easy to remove, and change fast as models change. Deep tells (how the text is shaped, what it actually says) are harder to spot, harder to fix, and stable across model generations. Prioritize depth.

A tell is a *signal*, not a verdict. Human writing contains every pattern here at some frequency, because models learned these patterns from humans. One instance proves nothing. The signal is in the density and co-occurrence: many tells, many times, in text written after late 2022. Each entry below includes a "when acceptable" note so you do not strip a pattern that is doing legitimate work.

## The root cause behind Tier 1

Most structural tells are one behavior seen from different angles. A language model predicts the most statistically likely continuation, so its output regresses to the mean: it smooths specific, unusual, statistically rare facts into generic, positive, importance-inflating statements that could apply to many subjects. The Wikipedia AI-cleanup project's image for it is apt: a sharp photograph fading into a blurry, generic sketch while the caption shouts louder that the subject is important. The subject becomes simultaneously less specific and more exaggerated. When you see puffery, manufactured significance, or flat genericness, you are seeing regression to the mean. The fix is to restore specificity (from context, or by asking the author) and to cut the inflation.

## Contents

- Tier 1: Structural and discourse tells
- Tier 2: Rhetorical and sentence-level tells
- Tier 3: Lexical and surface tells (dated)
- Formatting tells
- Not reliable tells (do not "fix" these)
- The anti-signature principle
- Sources

---

## Tier 1: Structural and discourse tells

The highest-priority layer. These survive vocabulary swaps and are what make a text "feel" AI even when no single word is wrong.

### Inflated significance and broader-trend padding

The text keeps explaining why the subject matters, connecting it to broader movements, legacies, or trends, often for mundane subjects that do not warrant it. Telltale shapes: "marking a pivotal moment in," "represents a broader shift toward," "stands as a testament to," "cementing its role as," "contributing to the broader history of." Sometimes it hedges first ("though minor, it nonetheless...") and then inflates anyway.

*Why it signals AI*: direct regression to the mean. The model defaults to the statistically common framing (everything is significant) instead of the rare specific fact.

*Fix*: cut the significance claim, or replace it with the concrete fact it was inflating, if that fact is present or the author can supply it.

*When acceptable*: when significance is the actual point and is supported (a genuinely pivotal event, argued with evidence). The tell is unearned, generic importance, not all mention of importance.

### Formulaic "challenges and future prospects" wind-down

A section or closing paragraph that follows a rigid template: "Despite its [positive traits], [subject] faces several challenges, including [list]. Despite these challenges, [subject] continues to [thrive / hold promise], and future [initiatives / developments] could further enhance its [relevance]." It ends on a vaguely upbeat assessment or speculative call to action.

*Why it signals AI*: the model has a canned outline for "wrap up an article" and reaches for it regardless of whether the content needs a forward-looking conclusion.

*Fix*: cut it, or replace with a real conclusion that says something specific. Most short-form pieces do not need a "future outlook" at all.

*When acceptable*: when the piece genuinely is about challenges or future direction and the content is specific rather than templated.

### Structure-narration

The text describes its own organization instead of just being organized: "This essay will examine...," "In this section, we will discuss...," "First, ... Second, ... Finally, ...," "Having established X, we now turn to Y." Intros that preview and conclusions that recap the same points.

*Why it signals AI*: scaffolding from the model's training on formulaic informational writing. A confident human writer usually just makes the point.

*Fix*: delete the narration and let the structure carry itself. Cut preview-intros and recap-conclusions down to whatever actually advances the argument.

*When acceptable*: long technical documents, academic papers, and specs where signposting genuinely aids navigation. Even there, "First/Second/Finally" on a three-item list is usually padding.

### Flat salience (uniform emphasis and rhythm)

Every sentence carries roughly equal weight and runs to roughly equal length. Nothing is foregrounded, nothing is thrown away, no sentence is allowed to be short and blunt or long and winding. Statistically this shows up as low "burstiness."

*Why it signals AI*: human writing has peaks and valleys, throwaway asides next to load-bearing claims. Models default to even, measured pacing.

*Fix*: decide what the most important sentence in each paragraph is and let it stand out, often by making it shorter and putting the rest in service of it. Vary sentence length deliberately. Allow a one-word reaction or a long subordinate chain where it fits.

*When acceptable*: some formal registers (legal, certain technical writing) are deliberately even. Match the register; do not force drama into a contract.

### Lack of depth / generic coverage

The text covers every angle at the same shallow level, touches specific details without the context that would make them matter, or misses the actual point while sounding comprehensive. Breadth substitutes for a load-bearing argument.

*Why it signals AI*: regression to the mean again, plus a tendency to be exhaustive rather than selective. The model lists what is generally true instead of committing to what is specifically true and important here.

*Fix*: this is the hardest one and where the contract bites. If the specific substance is recoverable from the source or surrounding context, restore it. If it is simply absent, you cannot invent it: flag the thinnest passages and ask the author what they actually wanted to say, or note that the passage needs a concrete point.

*When acceptable*: genuine overviews and primers, where breadth is the point. Even then, an overview can have a spine.

### Manufactured balance

Both-sides framing on a question where the author plainly holds a position. "While some argue X, others argue Y, and ultimately it depends on individual perspectives and priorities." Every section gives equal, noncommittal weight to opposing views and the piece refuses to land anywhere.

*Why it signals AI*: safety-trained noncommitment. The model hedges to avoid taking a stance.

*Fix*: if the author has a view (ask if unclear), let the text argue it, while still representing the opposing case fairly. A position with honest counterarguments is human; a tidy refusal to decide is the tell.

*When acceptable*: when even-handedness is the actual goal (a genuine pros-and-cons brief, a neutral reference entry). The tell is false balance masquerading as analysis, not all balance.

### Rule of three as a structural habit

Not just occasional triads, but a pervasive habit of grouping everything in threes: three adjectives, three-item lists, three parallel clauses, used to make superficial points sound complete. "engaging, interactive, and personalized," "accuracy, balance, and integrity."

*Why it signals AI*: the triad is a rhythm the model reaches for to sound thorough. The third item is often filler.

*Fix*: keep the triad only where all three items add something. Otherwise cut to the one or two that carry weight, or break the pattern so it is not every sentence.

*When acceptable*: rhetorical triads are a legitimate human device. The tell is the relentlessness, not a single well-placed three.

---

## Tier 2: Rhetorical and sentence-level tells

Recurring sentence shapes and framing moves. Medium priority: they reinforce the AI read but are more local than Tier 1.

### Negative parallelism

Negating a weaker claim to set up a stronger one: "It's not just X, it's Y," "This isn't X; it's Y," "not a representation of self, but a mechanism for its reinvention," "no X, no Y, just Z." Sometimes spread across two sentences ("His life, however, took a path that...").

*Fix*: state the stronger claim directly. "It's not just slow, it's broken" becomes "It is broken."

*When acceptable*: rarely and sparingly, for genuine contrast where the negated thing is a real expectation being corrected. Once in a long piece, not once a paragraph.

### Self-answered rhetorical questions

Posing a question and immediately answering it: "Why does this matter? Because the data shifts every quarter." "The result? Catastrophic."

*Fix*: cut the question, state the answer.

*When acceptable*: occasionally, in deliberately conversational or rhetorical registers (a speech, an op-ed). The tell is using it as a default transition.

### Pompous copulas (avoidance of "is" and "are")

Replacing plain copulas with weightier verbs: "serves as," "stands as," "marks," "represents," and marketing verbs like "features," "offers," "boasts" in place of "has." "The gallery serves as the association's exhibition space" instead of "is."

*Why it signals AI*: documented drop in "is/are" frequency in post-2022 text. Models inflate copulas to sound substantive.

*Fix*: use "is," "are," "has." Repetition of "is" is better than a parade of "serves as."

*When acceptable*: when the stronger verb is accurate and not just inflation ("the bridge spans the river," not "the bridge is over the river"). Judge whether the verb adds meaning.

### Verdict followed by an empty-noun reason

Asserting a conclusion and appending a short clause that names its cause with a hollow noun: "..., and safety is the reason," "..., and that's the key," "..., and X is the answer." The clause typically announces the verdict and its one-word cause, then the next sentences explain that cause, so the announcement is also redundant with what follows.

*Why it signals AI*: two things at once. It nominalizes a cause, turning "because of safety" into "safety is the reason" (the copula-inflation family pointed at causation), and it puts an empty placeholder noun in the stressed final slot of the clause, where English expects the new, important information. The content word ("safety") gets buried mid-clause and the slot that should carry weight holds "the reason," which carries none.

*Diagnostic (end-focus)*: read the last word of the clause. If it is a hollow noun (reason, key, factor, answer, point, difference) standing in for the actual content word, the clause is inflated. A human is likelier to end on the content word: "...because of safety," or "...and the decisive factor is safety."

*Fix*: cut the announcement and fold the cause into the argument, or rewrite so the content word lands last. "On balance, the benefits outweigh the risks, and safety is the reason" becomes "The benefits outweigh the risks, mostly on safety:" leading straight into the why, or "...and the decisive factor is safety."

*When acceptable*: when the hollow noun is genuinely the subject (a text literally about "the reason X happened"), or as a single deliberate rhetorical beat rather than a default closing move.

### Trailing participial benefit-clauses (superficial analysis)

A present-participle phrase tacked onto the end of a sentence that editorializes about significance: "..., highlighting its enduring legacy," "..., ensuring optimal performance," "..., reflecting the region's rich heritage," "..., contributing to the broader movement." Newer models may attach these to named sources that did not actually say it.

*Why it signals AI*: a canned way to add a veneer of analysis. The clause usually asserts significance the text has not earned, and as unattributed opinion it is often unsupportable.

*Fix*: cut the clause, or convert it to a concrete, supported statement. If it attributes a view to a source, verify the source actually says it before keeping it.

*When acceptable*: when the participial clause states a real, specific consequence rather than generic praise ("..., cutting query time by half").

### Vague attribution and overgeneralized opinion

Attributing claims to a fuzzy authority: "experts argue," "observers note," "industry reports suggest," "critics say," "it is widely believed." Or inflating one source into many: presenting a single citation as a consensus, implying lists are non-exhaustive ("such as ...") when they are complete.

*Fix*: name the source and what it actually says, or state the claim plainly and own it, or cut it. Do not invent a source to fill the attribution.

*When acceptable*: when the generalization is genuinely true and uncontroversial, or when you can name the actual source. The tell is borrowing unnamed authority.

### Promotional / advertisement tone

Travel-brochure or press-release phrasing where neutral prose belongs: "nestled in the heart of," "rich cultural heritage," "boasts a vibrant," "breathtaking," "a must-visit," "seamlessly connecting." A commercial gloss that creeps in even when nothing is being sold.

*Fix*: state what is true plainly. "Nestled in the breathtaking region of X" becomes "in X."

*When acceptable*: actual marketing copy, where some of this is the job, though even there the best copy is specific rather than generically glowing.

### Didactic disclaimers

Cautionary asides aimed at an imagined reader: "it's important to note that," "it's worth remembering," "always consult a professional," "results may vary." Common in older model output.

*Fix*: cut, or fold the substance into the sentence without the throat-clearing.

*When acceptable*: when a genuine caveat changes how the reader should act on the information. The tell is the reflexive, contentless version.

---

## Tier 3: Lexical and surface tells (dated)

Lowest priority and highest volatility. Once a marker word is publicly named, usage drops and the word stops discriminating, while other words rise to replace it. This section needs the most frequent review. Swap these for plain alternatives, but do not strip them so uniformly that the result reads scrubbed (see the anti-signature principle).

### High-density AI vocabulary

Individual words are weak signals; clusters are strong. These co-occur, and a post-2022 text packed with them is one of the more reliable lexical reads. Distribution shifts by model era (below). General list:

delve, underscore, showcase, highlight (as a verb), leverage, harness, tapestry, landscape (as an abstract noun), realm, intricate, intricacies, meticulous, meticulously, pivotal, crucial, key (as an adjective), vital, robust, comprehensive, seamless, enduring, vibrant, rich, profound, testament, boast (meaning "has"), garner, bolster, foster, cultivate, interplay, align, resonate, navigate (figurative), elevate, empower, unlock, embark, myriad, plethora, nuanced, multifaceted, valuable insights, deeply rooted, ever-evolving, fast-paced, in today's world, in the realm of, when it comes to.

### Marker words by model era

Distribution differs by which model produced the text. Approximate, not hard cutoffs; useful for dating older undetected AI text.

- **2023 to mid-2024 (GPT-4 era)**: delve, intricate/intricacies, meticulous/meticulously, tapestry, testament, pivotal, underscore, boast, bolster, garner, interplay, vibrant, additionally, crucial, key, landscape, enduring, valuable.
- **Mid-2024 to mid-2025 (GPT-4o era)**: align with, enhance, emphasizing, fostering, highlighting, showcasing, underscore, pivotal, enduring, vibrant, crucial, bolster.
- **Mid-2025 onward**: emphasizing, enhance, highlighting, showcasing, plus heavy emphasis on notability, sourcing, and media coverage; obvious flowery vocabulary is more suppressed and the tells shift toward structure.

The trajectory matters: "delve" was a strong tell in 2023 to early 2024 and had largely dropped off by 2025, while "significant" and "additionally" kept rising. Newer models suppress the obvious words, which pushes the reliable signal up into Tier 1.

### Filler intensifiers

"deeply," "genuinely," "fundamentally," "remarkably," "incredibly," "truly," "essentially," "arguably," used as weight on claims that do not need it. Keep them where they add specific meaning ("deeply rooted in custom"), cut them as filler ("deeply important").

### Em-dashes

Models overuse the em-dash, especially where a comma, colon, parenthesis, or period would do, and especially in a "punched-up" sales rhythm. Minimize hard: replace with the punctuation the sentence actually wants, and reserve the rare em-dash for cases where nothing else fits. This is *not* dispositive on its own (many humans use em-dashes well, and some newer models suppress them), so weight it lightly as a signal even while editing it out for style.

### Copy-paste and Unicode artifacts

Curly quotes and apostrophes where straight ones are expected (or inconsistent mixing of both), stray bullet characters (•), non-standard spaces, and leftover markup. These come from pasting model output. Normalize them. Curly quotes alone prove nothing (word processors insert them, Chicago style uses them), so treat them as a weak corroborating signal, not evidence.

---

## Formatting tells

Cross-cutting, often the most visually obvious, frequently the easiest to fix.

- **Overuse of lists**, especially nested lists, where connected prose would serve better. Convert list items that are really a flowing argument back into paragraphs. Keep lists for genuinely list-shaped, parallel, independent items.
- **Inline-header vertical lists**: a bullet or number followed by a bolded mini-heading, then a colon, then text. "**Increased Access:** Technology has made..." This is one of the most recognizable ChatGPT structures. Convert to prose or to a clean list without the bolded-colon headers, unless the content is genuinely a labeled reference list.
- **Excessive boldface** for mechanical emphasis, bolding every key term in a "key takeaways" manner. Reserve bold for genuine, occasional emphasis.
- **Title Case On Headings** where sentence case is normal for the register.
- **Emoji as decoration**, especially leading bullets or section headers (🚀 🔑 💡 ✅). Almost always remove outside genuinely casual contexts.
- **Markdown artifacts** when text is pasted somewhere that does not render them: stray `**`, `##`, `---`. Strip or convert.

---

## Not reliable tells (do not "fix" these)

Over-correction here is how deslopping leaves its own fingerprint. These look like AI to an untrained eye but are not reliable signals, and "fixing" them degrades the writing or creates a new artifact. Leave them alone unless they are independently bad.

- **Perfect grammar and spelling.** Many humans write cleanly. Do not introduce typos or errors to seem human; injected mistakes are just a different detectable tell.
- **Formal, academic, or "fancy" prose.** Specific marker words are tells; formality in general is not. Do not dumb down vocabulary below the author's natural level.
- **A single transition word** like "Additionally," "Moreover," or "Furthermore." Only the relentless, sentence-initial overuse is a signal. A few are normal and accepted by style guides.
- **Mixed casual and formal register.** Often just a real person in a technical field, or youth, or personal style.
- **A single em-dash, or curly quotes alone.** Weak signals; do not over-read them.
- **Letter-like formatting** (greeting, sign-off) in something that is actually a letter or email.
- **Length, or the presence of citations**, on their own.

The principle: edit the patterns that are genuinely AI-typical, and resist "fixing" things that are merely formal, clean, or correct. A human who writes well is not a problem to be corrected.

---

## The anti-signature principle

A text that has had every marker word deleted, every sentence clipped to the same short length, every transition stripped, and its vocabulary flattened does not read as human. It reads as scrubbed, which is its own recognizable artifact, and the newer detectors specifically target lightly-humanized AI text. The goal is natural variance, not maximal removal. After editing, check that the result has the irregular rhythm, the occasional longer sentence, the retained strong word, and the consistent single voice of real writing. If the edits produced a monotone, restore variation. Under-correcting and leaving some texture is safer than over-correcting into a new uniformity.

---

## Sources

- Wikipedia, "Signs of AI writing" (WikiProject AI Cleanup field guide), the most detailed and regularly updated community taxonomy. Note that some of its tells are Wikipedia-specific (wikitext, citation templates, AfC submission notes) and are excluded here as out of scope for general prose.
- Kobak, González-Márquez, Horvát, Lause, "Delving into LLM-assisted writing in biomedical publications through excess vocabulary," Science Advances (2025): excess-vocabulary method, the estimate that a large fraction of recent abstracts show LLM fingerprints, and the finding that the marker words are style verbs and adjectives rather than content nouns.
- Geng and Trotta, "Human-LLM Coevolution: Evidence from Academic Writing" (2025): marker words decline after being publicly named while others keep rising; the reason the lexical layer must be dated.
- Reinhart et al., "Do LLMs write like humans? Variation in grammatical and rhetorical styles," PNAS (2025): syntactic and rhetorical differences between models and humans.
