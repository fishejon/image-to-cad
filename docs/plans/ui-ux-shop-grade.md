# Image to CAD: UI and UX Specification

Nov 7, 2026 · Jonny Fisher

This spec covers every interface change needed to move from the current one-shot spec generator to the shop-grade path: a worker-run agent loop that turns a photo into a model, a cut list, and a material list. It is written from a design perspective and sets the usability bar the build has to meet.

> **Status:** ADOPTED as UI source of truth after photo-to-cutlist backend phases 0–6. Backend worker exists; this doc drives product UI. Tracker: align with [`photo-to-cutlist.md`](photo-to-cutlist.md).

## 1. Design stance

The product promise is simple: take a picture, get something you can build. The risk is that an AI result that looks right but isn't will cost someone real lumber. So the interface has to earn trust, not just impress.

### Principles

1. **Show the work.** Every result comes with what the tool saw, what it assumed, and what it checked.
2. **Be honest about uncertainty.** Estimates look different from measured facts, and the tool says when it is guessing.
3. **Always editable.** The first result is a draft. Correcting a size, a material, or a part is as easy as accepting it.
4. **Fast first feedback.** Something visible happens within two seconds of every action, even when the full result takes minutes.
5. **Never lose work.** Runs survive refreshes, closed tabs, and network drops.
6. **Simple first, expert on demand.** The default path has few choices. Models, connections, and raw specs live behind Advanced.

## 2. Users and jobs to be done

| User | Main job | What they need from the tool |
| --- | --- | --- |
| Hobbyist woodworker | “I saw this piece and want to build it.” | A believable model, a shopping list, and a cut list they can take to the shop |
| Small shop or maker | “Quote and plan this from a customer photo.” | Accurate sizes, material totals with waste, and a printable cut list |
| Designer | “Turn my reference into something I can refine.” | An editable model and export to CAD |

Three jobs drive every screen: get a model from a photo, know what to buy and cut, and fix what is wrong.

**Success looks like:** a first-time user reaches a reviewed model and an exported cut list in one sitting without help, and can say what the tool assumed.

## 3. End-to-end flow

| Step | User goal | Screen | Success signal |
| --- | --- | --- | --- |
| 1. Start | Begin a new design | New design sheet | Photo accepted, quality check passed |
| 2. Add context | Give scale and intent | Intake form | One known size set, or an explicit “no size” choice |
| 3. Confirm understanding | Check what the tool sees | Read-back screen | Parts and assumptions confirmed or corrected |
| 4. Wait | Know it’s working | Run progress | Live status and a preview each round |
| 5. Review | Judge the match | Review view | Side-by-side or overlay compared with the photo |
| 6. Correct | Fix what’s off | Inspect, Adjust, Ask for change | Model and lists update |
| 7. Plan the build | Get the lists | Lists tab | Cut list and materials reviewed |
| 8. Ship | Take it elsewhere | Ship tab | File downloaded, with the project saved |

Every step has a way back, and the run can be left and resumed at steps 4 to 8.

## 4. Information architecture

The current layout works for viewing: a file bar, a parts tree on the left, the 3D view in the middle, and tabs on the right (Inspect, Adjust, Move, Check, Ship, Spec). The cut list is a modal. That is the wrong place for one of the two main outputs.

| Area | Today | Change |
| --- | --- | --- |
| New design | AI design modal | Full sheet with an intake form, then a read-back step (section 5.1, 5.2) |
| Right tabs | Inspect, Adjust, Move, Check, Ship, Spec | Inspect, Adjust, Lists (new), Check, Ship. Move becomes part of the viewport tools, and Spec moves under Advanced in Ship |
| Cut list | Modal | Becomes the Lists tab, with a full-width view for printing |
| Reference photo | Small pane in the viewport | Add compare modes (side by side, overlay) and per-round previews |
| Settings | “Connection & model” inside the AI box | Separate Advanced settings, shown only for Classic runs (section 5.10) |
| Build guide | Separate full screen | Unchanged, but hidden for agent-built parts until joinery data exists |

The parts tree, camera views, edge toggle, section plane, explode slider, and measure tool stay as they are.

## 5–16

Full screen specs, states, a11y, responsive, performance, content, testing, phase UI map, and open decisions are in the authoring copy below (same as user brief of Nov 7, 2026). Implementation trackers will link section numbers rather than duplicating every bullet here on every change.

### UI changes by phase (build order)

| Phase | UI deliverables |
| --- | --- |
| 0. Baseline | Terminology and status vocabulary agreed, wireframes for intake, progress, review, and Lists |
| 1. Cut-list-first spike | Lists tab prototype fed by a static parts model, with blank sizes, estimate flags, and settings |
| 2. Loop and scoring | Run progress with per-round previews, stop and keep best, resume after refresh, worker status, compare modes, Check timeline, mesh part adapter for the viewer |
| 3. Photo-to-spec with questions | New intake with known size and extra photos, read-back and question cards, assumptions list |
| 4. Editable parts and lists | Part card, Adjust with named dimensions, undo and versions, Ask for a change, live Lists updates, STEP and PDF export |
| 5. Integration and rollout | Run mode selector and Advanced settings changes, error and cap states, first-run experience, accessibility audit, mobile pass |
| 6. Hardening and coverage | Scope-tier banners, domain profiles for lists, multi-photo review, sheet layout view |

### Open decisions

1. Does the user pay per run, and does that change how cost is shown?
2. Do shop users need quotes or customer sharing, which would add a share view?
3. How long should a run be allowed to continue in the background before it is stopped?
4. Should the build guide be extended to agent-built parts, or stay Classic-only?
5. What is the minimum supported phone and browser?
