WBC Brew-Calculator
===================

_If you need a full-fledged-and-belled-and-whistled brewing software,
look elsewhere._

WBC is a set of routines which calculate various things required for
brewing and dump out a brewday summary.  The goal of WBC is to replace
pen-and-paper manual approximations.  The goal of WBC is not to think
for the brewer and not to be so sophisticated that the user experience
becomes a matter of outsmarting the software.

The main (and only?) features are:

  * input and output units configurable to both metric and cryptic,
    also SG and Plato
  * handle fermentable yields and estimated strength / ABV, and
    optionally convert grainbill percentages to masses (per target
    strength and volume)
  * calculate water temperatures and volumes for infusion mashes,
    also multi-step (decoction mass calculations are planned)
  * calculate IBUs and optionally calculate hop additions based on
    desired IBUs

The "documentation" is provided by the examples.  Yes, I agree,
it's not real documentation, so we'll just use the "this software is
self-documenting" bingo card.

The interface for how recipes are specified might change.  I reserve
the right to rewrite the git history of this repo.

Features will be added as I need them (if I need them).
