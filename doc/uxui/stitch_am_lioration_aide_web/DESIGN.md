# Design System Specification: Editorial SaaS Experience

## 1. Overview & Creative North Star
### The Creative North Star: "The Ethereal Workspace"
This design system moves away from the rigid, heavy-handed borders of traditional project management tools. Instead, it adopts a philosophy of **Ethereal Workspace**—where clarity is achieved through light, depth, and sophisticated tonal layering. 

We break the "standard template" look by utilizing intentional asymmetry in layout and high-contrast typography scales. The interface should feel less like a database and more like a high-end digital editorial. By using expansive breathing room and overlapping surfaces, we create a tool that feels premium, calm, and authoritative.

---

## 2. Colors & Surface Philosophy
The palette centers on a deep, authoritative blue and a vibrant, intellectual purple, grounded by a warm, sophisticated "Paper" background.

### The "No-Line" Rule
**Explicit Instruction:** Traditional 1px solid borders for sectioning are strictly prohibited. Boundaries between sidebars, headers, and Kanban columns must be defined solely through background color shifts or subtle tonal transitions. 

### Surface Hierarchy & Nesting
Treat the UI as a physical stack of fine paper or frosted glass. Use the `surface-container` tokens to create "nested" depth:
- **Base Layer:** `surface` (#fff7fe) - Used for the main application background.
- **Structural Sections:** `surface-container-low` (#faf1fa) - Used for Kanban column backgrounds or sidebar foundations.
- **Interactive Elements:** `surface-container-lowest` (#ffffff) - Use this for cards sitting on top of a lower-tier container to create a natural, "lifted" feel without heavy shadows.

### The "Glass & Gradient" Rule
To elevate the experience from "generic" to "custom," floating elements (like modals or dropdowns) should utilize **Glassmorphism**. 
- **Tokens:** Apply `surface_variant` with 70% opacity and a `backdrop-blur` of 12px-20px.
- **CTAs:** Use subtle gradients for primary actions, transitioning from `primary` (#002e60) to `primary_container` (#004489) at a 135-degree angle. This adds "soul" and a tactile quality to interactions.

---

## 3. Typography
The system uses a pairing of **Manrope** for high-impact display and **Inter** for functional reading.

*   **Display & Headlines (Manrope):** Chosen for its modern, geometric character. Use `display-lg` to `headline-sm` for page titles and major dashboard sections. The exaggerated scale difference between headlines and body text is intentional—it mimics high-end editorial layouts.
*   **Body & Titles (Inter):** A workhorse sans-serif for high legibility in dense Kanban boards. 
    *   `title-md` (Inter, 1.125rem) is the standard for Task Card titles.
    *   `body-md` (Inter, 0.875rem) handles primary content.
*   **Labels (Inter):** Use `label-sm` (0.6875rem) in all-caps with increased letter-spacing (0.05rem) for metadata and status tags to provide a premium, "curated" feel.

---

## 4. Elevation & Depth
Depth is a functional tool, not just an aesthetic choice. We use **Tonal Layering** to guide the eye.

*   **The Layering Principle:** Avoid "box shadows" for standard layout hierarchy. Instead, place a `surface-container-lowest` object on a `surface-container-high` background to create a crisp, modern separation.
*   **Ambient Shadows:** For "floating" elements like Task Cards being dragged or floating action buttons, use an extra-diffused shadow:
    *   `box-shadow: 0 12px 32px -4px rgba(30, 26, 33, 0.06);` 
    *   The shadow color must be a tinted version of `on-surface`, never a pure grey.
*   **The "Ghost Border" Fallback:** If accessibility requires a border (e.g., in high-contrast modes), use a "Ghost Border": the `outline-variant` token (#cec3d2) at **15% opacity**. Never use 100% opaque lines.

---

## 5. Components

### Buttons
*   **Primary:** Gradient of `primary` to `primary_container`. Roundedness: `DEFAULT` (0.5rem). High-contrast `on_primary` text.
*   **Secondary:** `secondary_container` background with `on_secondary_container` text. No border.
*   **Tertiary:** Transparent background. Text in `primary`. For use in low-emphasis actions like "Cancel."

### Task Cards (Kanban)
*   **Style:** No borders. Background: `surface-container-lowest`. 
*   **Separation:** Use the `xl` (1.5rem) spacing between cards to create a sense of focus and calm.
*   **States:** On hover, apply a `surface-dim` tint and the **Ambient Shadow** specified above.

### Chips (Labels & Status)
*   **Visuals:** Use `secondary_fixed` for a soft, professional splash of purple. Roundedness: `full`.
*   **Context:** For project management, ensure status chips (e.g., "In Progress") use `tertiary_fixed` for a warm, distinct visual cue that doesn't compete with primary actions.

### Input Fields
*   **Resting:** `surface_container_highest` background. No border.
*   **Focus:** Transition to a "Ghost Border" of `primary` at 40% opacity with a subtle inner glow.
*   **Typography:** Labels must use `label-md` in `on_surface_variant`.

### Lists
*   **Rule:** Forbid the use of divider lines. 
*   **Alternative:** Use vertical white space (16px - 24px) or alternating backgrounds of `surface` and `surface-container-low` for list item rows.

---

## 6. Do's and Don'ts

### Do
*   **Do** use asymmetrical margins. For example, a wider left margin for the main header than the right margin to create an editorial feel.
*   **Do** prioritize "Breathing Room." If a layout feels cramped, increase the padding by 1.5x before considering a divider line.
*   **Do** use `backdrop-blur` for all navigation overlays to maintain a sense of environmental awareness.

### Don't
*   **Don't** use 1px black or grey borders. This instantly flattens the design and makes it look like a generic framework.
*   **Don't** use high-saturation shadows. Shadows should feel like light being blocked, not ink on the page.
*   **Don't** use `primary` blue for everything. Reserve the deep blue for high-level authority and the `secondary` purple for creative, interactive elements.
*   **Don't** use standard "box" layouts. Overlap elements slightly (e.g., a header card overlapping a colored hero section) to create visual interest.