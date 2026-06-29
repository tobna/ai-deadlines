# Frontend Redesign Critique ("The Deadline Console")

## Architecture

- [ ] **Duplicated CSS file.** `styles.css` and `styles.tailwind.css` are byte-identical (both 879 lines). The comment says one is "copied verbatim" to the other, which is a manual process that will inevitably drift. If this was meant to replace Tailwind entirely, the `update_tailwind.sh` script and `make_website.sh` references should be cleaned up rather than leaving two copies.

- [ ] **Loss of Tailwind flexibility.** The old design used Tailwind utility classes inline in JS template strings, making per-card tweaks trivial. The new design requires adding CSS rules for any visual change — fine for a stable system, painful during active iteration.

## Bugs

- [ ] **Memory leak on re-render.** `renderConferences` clears intervals stored on `card.dataset.intervalId`, but `populateTagFilter` is called *inside* `applyAllFilters` which rebuilds the entire tag DOM every filter change (search input keystroke, toggle, etc.) — unnecessary DOM churn.

- [ ] **`innerHTML` without sanitization.** Conference notes, titles, and shortnames are interpolated directly into `innerHTML` (scripts.js:340). If any source data contains malicious HTML/JS, it executes. The old code had the same pattern but worth flagging.

- [ ] **Proximity meter is out of sync.** The meter bar animates with `transition: width 1s linear`, but JS updates every second. This means the bar always chases a value that was already superseded — it never actually reaches its target width.

## Performance

- [ ] **One interval per card, forever.** Each non-approximate card gets a `setInterval` at scripts.js:364. On a page with 50+ conferences, that's 50 concurrent intervals ticking every second. For cards in the archive viewed with "Show past", all their intervals still run.

- [ ] **Hero stats computed synchronously during render.** `updateHeroStats` runs once at load (fine), but `renderNextUp` calls `pickNextDeadline` which iterates *all* conferences on every second tick of the hero countdown — O(n) per frame for a value that only changes when the nearest deadline crosses a threshold.

## Accessibility

- [ ] **Blinking cursor.** `.brand .cursor` at styles.css:160 has an infinite blink animation. While `prefers-reduced-motion` is handled, the `@keyframes` rule applies to `*::before, *::after` generically — it may not catch a pseudo-element applied via inline style (`display: inline-block` on a span).

- [ ] **No focus trapping in modal.** Clicking outside or pressing Escape removes `.is-open`, but there's no `trapFocus` logic. Tabbing from the modal button lands you in the conference grid behind the overlay.

- [ ] **Card has `tabIndex="0"`** (scripts.js:253) wrapping a flex column with internal links — this creates an awkward tab stop that jumps focus to the middle of the page rather than a natural reading order element.

## Design / UX

- [ ] **Blinking cursor on the brand name.** It's meant to evoke a terminal/console, but it competes for attention with the actual countdown digits that should be the focal point. Users will ignore it or find it distracting.

- [ ] **Hero stats show `—` until first render.** There's no skeleton or cached value. On slow connections the hero reads "conferences tracked: — / due within 7 days: —" which looks broken rather than loading.

- [ ] **Mobile drawer has no close affordance.** The filter strip toggles open but there's no visible "close" button inside it on mobile — only the toggle button at the top. Users might not realize they can tap it again to collapse.

- [ ] **`--accent-ink: #2A2007` in light mode.** The CSS comment says "AA on the CTA" but `#B8780C` on `#2A2007` actually gives ~5.2:1 (passes AA). Still, it's an unusual dark brown for button text — consider whether the contrast is intentional or a typo for `#FFFFFF`.

## Misc

- [ ] **Animation delay capped at 12.** `Math.min(index, 12) * 45ms` means card 13+ all get the same 600ms delay — no stagger. Fine if you never exceed ~15 cards, but brittle.

- [ ] **No CSS custom property for animation timing.** Every animation has hardcoded durations scattered across the file. A design-token approach (`--duration-fast`, etc.) would make dark/light or reduced-motion tweaks easier.
