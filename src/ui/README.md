# Discord UI ownership

`src/cogs/` contains commands, event listeners, and feature behaviour.
`src/ui/` contains reusable presentation and interaction patterns.

## Setup panels

All administrative setup panels use `src.ui.setup.SetupPanel`:

- every surface carries the same `Aether Admin Console` identity and access rail;
- status appears first (`ready`, `incomplete`, `disabled`, or `draft`);
- required settings appear before optional settings;
- button labels describe the action that will happen;
- expired controls are visibly disabled;
- the footer identifies the admin who opened the panel and its lifetime;
- feature-specific database work remains inside its cog.

Panel classes stay beside their feature cog until the feature is split into a
service/repository layer. This avoids circular imports while keeping visual
rules in one obvious location.
