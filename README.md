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
  * TODO: a recipe specification "grammar" and tools to process
    that grammar

The "documentation" is provided by the examples.  Yes, I agree,
it's not real documentation, so we'll just use the "this software is
self-documenting" bingo card.

The interface for how recipes are specified might change.  I reserve
the right to rewrite the git history of this repo.

Features will be added as I need them (if I need them).

Example
-------

The recipe _MarBock_ translates to the following output:

```
==============================================================================
Name:              MarBock
Final volume:      19.5l              Water (20.0°C):      34.0l              
IBU (Tinseth):     36.00              BUGU:                0.52               
Color (EBC / SRM): 10.8 / 5.5

Yeast:             WLP833
Water notes:       

Preboil  volume  : 26.9l (70.0°C)     Measured:                               
Preboil  strength: 13.8°P             Measured:                               
Postboil volume  : 22.7l (100.0°C)    Measured:                               
Postboil strength: 16.8°P             Measured:                               

Kettle loss (est): 1.3l               Fermenter loss (est):1.0l               
Mash eff (conf) :  88.0%              Brewhouse eff (est): 78.7%              
==============================================================================

Fermentables                                    amount     extract  °P tot
==============================================================================
Avangard Pilsner                      4.23 kg ( 75.0%)     2.98 kg  12.8°P
Avangard Vienna                         846 g ( 15.0%)       595 g   2.7°P
Avangard Munich light                   564 g ( 10.0%)       399 g   1.8°P
==============================================================================
                                      5.64 kg (100.0%)     3.97 kg  16.9°P

Mashing instructions
==============================================================================
66.0°C : add 14.5l of water at 77.9°C
Sparge water volume: 20.3l (82.0°C)

Steal 0.4l of *well-mixed* preboil wort and blend with 0.1l water
==> 0.5l of 10.0°P stolen wort
==============================================================================

Hops                            AA%                time    amount     IBUs
==============================================================================
Northern Brewer (pellet)        9.9%             90 min    26.1 g    28.60
Saaz (leaf)                     3.1%             30 min    20.0 g     4.48
Hallertau (pellet)              3.8%             15 min    15.0 g     2.92
==============================================================================
                                                           61.1 g    36.00

Speculative apparent attenuation and resulting ABV
==============================================================================
 Strength    Atten.   ABV        Strength    Atten.   ABV       
  7.0°P       60%     5.5%        4.4°P       75%     6.9%      
  6.1°P       65%     6.0%        3.5°P       80%     7.4%      
  5.2°P       70%     6.4%        2.6°P       85%     7.9%      
==============================================================================
```
