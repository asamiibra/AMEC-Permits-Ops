# Accessibility and RTL review

The shell uses semantic navigation, headings, tables, buttons, focus-visible outlines, and `aria-current` on the projected current step. Status is represented with text as well as color. Mixed-direction identifiers continue to use LTR-safe rendering in retained control surfaces. The workflow stepper is horizontally scrollable on small screens and the existing RTL control path remains covered by browser tests.
