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

  * recipe specification is so compact that you can get an idea
    of the beer with a single glance;
    see [example](#example-recipe) [recipes](example-recipe-1)
  * input and output units configurable to both metric and cryptic,
    also SG and Plato
  * handle fermentable yields and estimated strength / ABV, and
    optionally convert grainbill percentages to masses (per target
    strength and volume)
  * calculate water temperatures and volumes for infusion mashes,
    also multi-step (decoction mass calculations are planned ... some day)
  * calculate IBUs and optionally calculate hop additions based on
    desired IBUs

The recipe interface might change in a way not backward compatible as
the software reaches final gravity.

The "documentation" is provided by the examples.  Yes, I agree,
it's not real documentation, so we'll just use the "this software is
self-documenting" bingo card.  I will write documentation once the
interface will not change.

Examples
========

<!-- BEGIN EXAMPLE -->
Example recipe
---
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
Pitch rate, ale:   258 billion        Pitch rate, lager:   516 billion        

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
66.0°C : add 14.3l of water at 78.0°C (2.5 ratio)
Mashstep water volume: 13.9l @ 20.0°C
Sparge water volume:   20.1l @ 82.0°C
==============================================================================

Hops                              AA%                time    amount     IBUs
==============================================================================
Northern Brewer (pellet)          9.9%             90 min    26.1 g    28.60
Saaz (leaf)                       3.1%             30 min    20.0 g     4.48
Hallertau (pellet)                3.8%             15 min    15.0 g     2.92
==============================================================================
                                                             61.1 g    36.00

Speculative apparent attenuation and resulting ABV
==============================================================================
  Str.    Att.  ABV         Str.    Att.  ABV         Str.    Att.  ABV       
 7.0°P    60%   5.5%       5.2°P    70%   6.4%       3.5°P    80%   7.4%      
 6.1°P    65%   6.0%       4.4°P    75%   6.9%       2.6°P    85%   7.9%      
==============================================================================

```

translated with `wbctool -u us -u sg`:
```
==============================================================================
Name:              MarBock
Final volume:      5.2gal             Boil:                90 min             
IBU (Tinseth):     36.00              BUGU:                0.52               
Color (EBC / SRM): 10.7 / 5.4         Water (68.0°F):      8.8gal             
Pitch rate, ale:   258 billion        Pitch rate, lager:   516 billion        

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
Avangard Munich Light                 1 3/16 lb ( 10.0%)    13.90 oz   1.007
==============================================================================
                                      12 1/4 lb (100.0%)    8 5/8 lb   1.069

Mashing instructions
==============================================================================
150.8°F: add 3.8gal of water at 172.3°F (2.5 ratio)
Mashstep water volume: 3.7gal @ 68.0°F
Sparge water volume:   5.3gal @ 179.6°F
==============================================================================

Hops                              AA%                time    amount     IBUs
==============================================================================
Northern Brewer (pellet)          9.9%             90 min   0.92 oz    28.60
Saaz (leaf)                       3.1%             30 min   0.71 oz     4.48
Hallertau (pellet)                3.8%             15 min   0.53 oz     2.92
==============================================================================
                                                            2.16 oz    36.00

Speculative apparent attenuation and resulting ABV
==============================================================================
  Str.    Att.  ABV         Str.    Att.  ABV         Str.    Att.  ABV       
 1.028    60%   5.5%       1.021    70%   6.4%       1.014    80%   7.4%      
 1.024    65%   6.0%       1.017    75%   6.9%       1.010    85%   7.9%      
==============================================================================

```

Example recipe
---
```
name:   Beer from IPAnema
yeast:  US-05
volume: 19.5l
boil:   30min
mashin: 3

mashtemps: [ 66degC ]

fermentables:
        anchor: [ strength, 15degP ]

        mash:
                Briess Pale:     rest
                Avangard Vienna:  18%

hops:
        defs:
                mosaic:         [ Mosaic,     12.4%,   pellet  ]
                citra:          [ Citra,      14.0%,   pellet  ]

        boil:
                - [ citra,      10g, 30 min ]
                - [ mosaic,     10g, 30 min ]
                - [ citra,      10g, 12 min ]
                - [ mosaic,     10g, 12 min ]

        steep:
                - [ citra,      10g, 10min @ 90degC ]
                - [ mosaic,     10g, 10min @ 90degC ]

        dryhop:
                - [ citra,      25g, keg ]
                - [ mosaic,     25g, keg ]
```
translated with `wbctool -u metric -u plato`:
```
==============================================================================
Name:              Beer from IPAnema
Final volume:      19.5l              Boil:                30 min             
IBU (Tinseth):     33.71              BUGU:                0.55               
Color (EBC / SRM): 12.4 / 6.3         Water (20.0°C):      29.7l              
Pitch rate, ale:   230 billion        Pitch rate, lager:   461 billion        

Yeast:             US-05
Water notes:       

Preboil  volume  : 23.7l (70.0°C)     Measured:                               
Preboil  strength: 13.8°P             Measured:                               
Postboil volume  : 22.6l (100.0°C)    Measured:                               
Postboil strength: 15.0°P             Measured:                               

Kettle loss (est): 1.2l               Fermenter loss (est):1.0l               
Mash eff (conf) :  88.0%              Brewhouse eff (est): 79.1%              

NOTE: keg hops absorb: 0.3l => effective yield: 19.2l
==============================================================================

Fermentables                                      amount     extract  °P tot
==============================================================================
Briess Pale                             4.09 kg ( 82.0%)     2.83 kg  12.4°P
Avangard Vienna                           899 g ( 18.0%)       633 g   2.9°P
==============================================================================
                                        4.99 kg (100.0%)     3.46 kg  15.0°P

Mashing instructions
==============================================================================
66.0°C : add 15.3l of water at 76.4°C (3 ratio)
Mashstep water volume: 15.0l @ 20.0°C
Sparge water volume:   15.2l @ 82.0°C
==============================================================================

Hops                              AA%                time    amount     IBUs
==============================================================================
Citra (pellet)                    14.0%            30 min    10.0 g    11.57
Mosaic (pellet)                   12.4%            30 min    10.0 g    10.24
Citra (pellet)                    14.0%            12 min    10.0 g     6.31
Mosaic (pellet)                   12.4%            12 min    10.0 g     5.59
------------------------------------------------------------------------------
Citra (pellet)                    14.0%    10min @ 90.0°C    10.0 g     0.00
Mosaic (pellet)                   12.4%    10min @ 90.0°C    10.0 g     0.00
------------------------------------------------------------------------------
Mosaic (pellet)                   12.4%     dryhop in keg    25.0 g     0.00
Citra (pellet)                    14.0%     dryhop in keg    25.0 g     0.00
==============================================================================
                                                              110 g    33.71

Speculative apparent attenuation and resulting ABV
==============================================================================
  Str.    Att.  ABV         Str.    Att.  ABV         Str.    Att.  ABV       
 6.2°P    60%   4.8%       4.7°P    70%   5.7%       3.1°P    80%   6.5%      
 5.4°P    65%   5.3%       3.9°P    75%   6.1%       2.3°P    85%   6.9%      
==============================================================================

```

translated with `wbctool -u us -u sg`:
```
==============================================================================
Name:              Beer from IPAnema
Final volume:      5.2gal             Boil:                30 min             
IBU (Tinseth):     33.71              BUGU:                0.55               
Color (EBC / SRM): 12.4 / 6.3         Water (68.0°F):      7.9gal             
Pitch rate, ale:   230 billion        Pitch rate, lager:   461 billion        

Yeast:             US-05
Water notes:       

Preboil  volume  : 6.3gal (158.0°F)   Measured:                               
Preboil  strength: 1.056              Measured:                               
Postboil volume  : 6.0gal (212.0°F)   Measured:                               
Postboil strength: 1.061              Measured:                               

Kettle loss (est): 0.3gal             Fermenter loss (est):0.3gal             
Mash eff (conf) :  88.0%              Brewhouse eff (est): 79.1%              

NOTE: keg hops absorb: 0.1gal => effective yield: 5.1gal
==============================================================================

Fermentables                                      amount     extract  SG tot
==============================================================================
Briess Pale                              9 0 lb ( 82.0%)   6 3/16 lb   1.050
Avangard Vienna                      1 15/16 lb ( 18.0%)    1 3/8 lb   1.011
==============================================================================
                                        11 0 lb (100.0%)    7 5/8 lb   1.061

Mashing instructions
==============================================================================
150.8°F: add 4.1gal of water at 169.6°F (3 ratio)
Mashstep water volume: 4.0gal @ 68.0°F
Sparge water volume:   4.0gal @ 179.6°F
==============================================================================

Hops                              AA%                time    amount     IBUs
==============================================================================
Citra (pellet)                    14.0%            30 min   0.35 oz    11.57
Mosaic (pellet)                   12.4%            30 min   0.35 oz    10.24
Citra (pellet)                    14.0%            12 min   0.35 oz     6.31
Mosaic (pellet)                   12.4%            12 min   0.35 oz     5.59
------------------------------------------------------------------------------
Citra (pellet)                    14.0%   10min @ 194.0°F   0.35 oz     0.00
Mosaic (pellet)                   12.4%   10min @ 194.0°F   0.35 oz     0.00
------------------------------------------------------------------------------
Mosaic (pellet)                   12.4%     dryhop in keg   0.88 oz     0.00
Citra (pellet)                    14.0%     dryhop in keg   0.88 oz     0.00
==============================================================================
                                                            3.88 oz    33.71

Speculative apparent attenuation and resulting ABV
==============================================================================
  Str.    Att.  ABV         Str.    Att.  ABV         Str.    Att.  ABV       
 1.024    60%   4.8%       1.018    70%   5.7%       1.012    80%   6.5%      
 1.021    65%   5.3%       1.015    75%   6.1%       1.009    85%   6.9%      
==============================================================================

```

