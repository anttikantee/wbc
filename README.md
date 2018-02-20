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
  * WIP: a recipe specification "grammar" and tools to process
    that grammar

The "documentation" is provided by the examples.  Yes, I agree,
it's not real documentation, so we'll just use the "this software is
self-documenting" bingo card.

The interface for how recipes are specified might change.  I reserve
the right to rewrite the git history of this repo.

Features will be added as I need them (if I need them).

Example
-------
<!-- BEGIN EXAMPLE -->
recipe:
```
name:   MarBock
yeast:  WLP833
volume: 19.5l
boil:   90min

mashtemps: [ 66degC ]

fermentables:
    anchor: [ strength, 16.8 degP ]

    mash:
        Avangard Pilsner:       rest
        Avangard Vienna:        15%
        Avangard Munich Light:  10%

hops:
    boil:
        - [ [ Northern Brewer, 9.9%, pellet ], 36 Recipe IBU, 90 min ]
        - [ [ Saaz,            3.1%, leaf   ], 20 g,          30 min ]
        - [ [ Hallertau,       3.8%, pellet ], 15 g,          15 min ]
```
translated with `wbctool -u metric -u plato`:
```
==============================================================================
Name:              MarBock
Final volume:      19.5l              Boil:                90 min             
IBU (Tinseth):     36.00              BUGU:                0.52               
Color (EBC / SRM): 10.7 / 5.4         Water (20.0°C):      33.4l              

Yeast:             WLP833
Water notes:       

Preboil  volume  : 26.9l (70.0°C)     Measured:                               
Preboil  strength: 13.8°P             Measured:                               
Postboil volume  : 22.7l (100.0°C)    Measured:                               
Postboil strength: 16.8°P             Measured:                               

Kettle loss (est): 1.3l               Fermenter loss (est):1.0l               
Mash eff (conf) :  88.0%              Brewhouse eff (est): 78.8%              
==============================================================================

Fermentables                                      amount     extract  °P tot
==============================================================================
Avangard Pilsner                        4.17 kg ( 75.0%)     2.94 kg  12.8°P
Avangard Vienna                           835 g ( 15.0%)       588 g   2.7°P
Avangard Munich Light                     556 g ( 10.0%)       394 g   1.8°P
==============================================================================
                                        5.56 kg (100.0%)     3.92 kg  16.9°P

Mashing instructions
==============================================================================
66.0°C : add 14.3l of water at 78.0°C
Sparge water volume: 20.1l (82.0°C)
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

translated with `wbctool -u us -u sg`:
```
==============================================================================
Name:              MarBock
Final volume:      5.2gal             Boil:                90 min             
IBU (Tinseth):     36.00              BUGU:                0.52               
Color (EBC / SRM): 10.7 / 5.4         Water (68.0°F):      8.8gal             

Yeast:             WLP833
Water notes:       

Preboil  volume  : 7.1gal (158.0°F)   Measured:                               
Preboil  strength: 1.056              Measured:                               
Postboil volume  : 6.0gal (212.0°F)   Measured:                               
Postboil strength: 1.069              Measured:                               

Kettle loss (est): 0.4gal             Fermenter loss (est):0.3gal             
Mash eff (conf) :  88.0%              Brewhouse eff (est): 78.8%              
==============================================================================

Fermentables                                      amount     extract  SG tot
==============================================================================
Avangard Pilsner                      9 3/16 lb ( 75.0%)   6 7/16 lb   1.052
Avangard Vienna                      1 13/16 lb ( 15.0%)    1 1/4 lb   1.010
Avangard Munich Light                 1 3/16 lb ( 10.0%)     13.9 oz   1.007
==============================================================================
                                      12 1/4 lb (100.0%)    8 5/8 lb   1.069

Mashing instructions
==============================================================================
150.8°F: add 3.8gal of water at 172.3°F
Sparge water volume: 5.3gal (179.6°F)
==============================================================================

Hops                            AA%                time    amount     IBUs
==============================================================================
Northern Brewer (pellet)        9.9%             90 min    0.9 oz    28.60
Saaz (leaf)                     3.1%             30 min    0.7 oz     4.48
Hallertau (pellet)              3.8%             15 min    0.5 oz     2.92
==============================================================================
                                                           2.2 oz    36.00

Speculative apparent attenuation and resulting ABV
==============================================================================
 Strength    Atten.   ABV        Strength    Atten.   ABV       
  1.028       60%     5.5%        1.017       75%     6.9%      
  1.024       65%     6.0%        1.014       80%     7.4%      
  1.021       70%     6.4%        1.010       85%     7.9%      
==============================================================================

```
