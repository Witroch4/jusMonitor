# Design System: JUSMONITOR
**Project ID:** 538325528689641160

## 1. Visual Theme & Atmosphere
The aesthetic philosophy of JusMonitor is a "Minimalist Legal Dashboard Variant." It features an elegant, luxurious, and highly authoritative atmosphere. The density is airy but structured, relying on a sophisticated split between a dominant dark mode and a crisp light mode. It leans heavily on premium visual cues—subtle golds against deep charcoal or stark white—to convey trust, precision, and high-end legal service. The mood is serious, focused, and undeniably premium.

## 2. Color Palette & Roles
* **Premium Gold (Primary Action):** `#D4AF37` for dark mode / `#B89650` for light mode. Used as the primary accent color for active navigation items, key metrics, icons, and primary actions. Instills a sense of luxury and authority.
* **Charcoal Canvas (Dark Mode Bg):** `#121212`. The main canvas color for dark mode, providing a deep, high-contrast foundation.
* **Crisp Canvas (Light Mode Bg):** `#F8F9FA`. The main canvas color for light mode, offering a clean, airy backdrop.
* **Elevated Charcoal (Dark Mode Card):** `#1E1E1E`. Used for dark mode cards and elevated surfaces to create depth.
* **Midnight Sidebar (Dark & Light Mode Navigation):** `#161616` / `#0B0F19`. A consistent, very dark anchor for the left sidebar regardless of light/dark mode, providing strong visual grounding.
* **Muted Slate/Gray (Borders):** `#333333` / `slate-200`. Used for subtle dividers and borders to structure content without overwhelming the interface.
* **Alert Crimson (Functional):** `text-red-400` / `text-red-600`. Used functionally to highlight urgent items, deadlines, and critical risk metrics.
* **Light Text (Dark Mode):** `#E5E7EB`. For primary text in dark mode.

## 3. Typography Rules
* **Headers (Display):** **Playfair Display** (serif). Used for major headings (e.g., "Central Operacional", large metric numbers). Adds traditional legal authority. Weights are typically Bold or Semi-bold.
* **Body (Sans-serif):** **Inter** (sans-serif). Used for all UI elements, data tables, and secondary text. Ensures modern legibility. Weights are Regular or Medium.
* **Letter-spacing (Tracking):** Wide tracking (`tracking-wider`, `tracking-widest`) is consistently applied to small, uppercase labels (e.g., table headers, dates) to create a refined, editorial look.

## 4. Component Stylings
* **Buttons:** Gently rounded corners (`rounded-xl` or `rounded-full`), usually with a solid background or subtle border. Hover states introduce a border color change to the primary gold or a subtle background shift. Often include an icon alongside text.
* **Cards/Containers:** Generously rounded corners (`rounded-2xl`). They feature subtle, whisper-soft diffused shadows (`shadow-sm`) and often incorporate a thick left border accent (`border-l-4`) colored with the primary gold or alert red to indicate category or status.
* **Inputs/Forms:** Fully rounded, pill-shaped inputs (`rounded-full`) like the search bar, featuring a subtle border, an inline icon on the left, and a primary gold focus ring.
* **Data Tables:** Clean, minimalist rows separated by subtle borders (`divide-y divide-dark-border` or `divide-y divide-slate-100`). Subtle hover states (`hover:bg-white/5` or `hover:bg-slate-50`). Table headers are small text (`text-[11px]`), bold, uppercase, with wide tracking.
* **Icons:** Uniformly using **Material Symbols Outlined** (or Material Icons Outlined) for a clean, consistent, and professional iconography style.

## 5. Layout Principles
* **Grid Alignment:** The dashboard content is organized using strict CSS Grid. Top-level stats use a 4-column structure (`lg:grid-cols-4`), while the main lower section splits into a dominant 2-column wide area and a 1-column side area (`lg:grid-cols-3` -> `lg:col-span-2`).
* **Whitespace Strategy:** Relies on generous padding internally (`p-6`, `p-8`) and significant gaps between structural components (`gap-6`, `gap-8`). This maintains an airy, uncrowded feel that lets the data breathe.
* **Alignment:** Strong left-alignment for textual data, with key actions, small status badges, and icons pushed to the right extremities of their containers.
