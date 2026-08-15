# Administration Home + Contract Owner UX Repair

The owner-facing Administration route now opens on a live operational workspace with compact Contract and Invoice previews, lane counts, clear secondary actions, and a derived Inputs & Go-Live status. Billing remains reachable at `/billing` for compatibility, but is no longer a duplicate primary Administration navigation item.

The Contract detail route now renders one coherent workspace: Proposal Origin, Client / Party, Client Document and LPO evidence, Contract Documents & Sources, Project & Commercial Terms, commitments, one Accept Contract control, gated Project Activation, Billing & Invoices context, and Work / Issues / Notifications / History links. Legacy stacked workbench, authority-control, and duplicate commercial renderers were removed from the owner route source.

The product boundary remains explicit: synthetic/local document verification is available for the test environment, production Synology verification remains external, Contract acceptance is internal AMEC approval rather than legal execution, and Project Activation requires an accepted Contract revision at both the UI and server layers.
