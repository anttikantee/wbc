WBC Brew-Calculator
===================

_If you need a full-fledged-and-belled-and-whistled brewing software,
look elsewhere._

WBC is homebrew software which takes in a recipe and dumps out a
printable brewday summary, as demonstrated by the [examples](#examples).
The goal of WBC is to replace pen-and-paper calculations.  The goal of
WBC is not to think for the brewer and not to be so sophisticated that
the user experience becomes a matter of outsmarting the software.

The main (and only?) features are:

  * recipe specification is so compact that you can get an idea
    of the beer with a single glance;
    see [example](#example-recipe) [recipes](#example-recipe-1)
  * input and output units configurable to both metric and cryptic,
    also SG and Plato
  * handle fermentable yields and estimated strength / ABV, and
    optionally convert grainbill percentages to masses (per target
    strength and volume)
  * calculate water temperatures and volumes for infusion mashes,
    also multi-step (decoction mass calculations are planned ... some day)
  * calculate IBUs and optionally calculate hop additions based on
    desired IBUs
  * a machine-readable compiled format -- if the recipe is what
    you want to brew, the compiled format is the ingredients you used
    to achieve what you wanted.  This data can be used to track
    ingredient usage, or be fed back into the software to see how the
    ingredients would have turned out with different system parameters
    (e.g. mash efficiency and/or boiloff rate)

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

mashparams: { temperature: 66degC }

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
IBU (Tinseth):     36.00              BUGU:                0.50               
Color (Morey):     10.7 EBC, 5.4 SRM  Water (20.0°C):      33.6l              
Pitch rate, ale:   267 billion        Pitch rate, lager:   535 billion        

Yeast:             WLP833
Water notes:       

Preboil  volume  : 27.1l (70.0°C)     Measured:                               
Preboil  strength: 13.4°P             Measured:                               
Postboil volume  : 22.2l (100.0°C)    Measured:                               
Postboil strength: 16.8°P             Measured:                               

Kettle loss (est): 1.0l               Fermenter loss (est):0.8l               
Mash eff (conf) :  88.0%              Brewhouse eff (est): 84.6%              
==============================================================================

Fermentables                                  amount  ext (100%)   ext (88%)
==============================================================================
Mash
------------------------------------------------------------------------------
Avangard Pilsner                    4.08 kg ( 75.0%)     3.26 kg     2.87 kg
Avangard Vienna                       815 g ( 15.0%)       652 g       574 g
Avangard Munich Light                 544 g ( 10.0%)       438 g       385 g
------------------------------------------------------------------------------
==============================================================================
                                    5.44 kg (100.0%)     4.35 kg     3.83 kg

Mashing instructions (for ambient temperature 20.0°C)
==============================================================================
66.0°C : add 14.0l of water at 78.1°C (2.50 l/kg, mash vol 17.4l)
Mashstep water volume: 13.6l @ 20.0°C
Sparge water volume:   20.5l @ 82.0°C
==============================================================================

Hops                              AA%                time    amount     IBUs
==============================================================================
Northern Brewer (pellet)          9.9%             90 min    25.1 g    28.36
Saaz (leaf)                       3.1%             30 min    20.0 g     4.62
Hallertau (pellet)                3.8%             15 min    15.0 g     3.02
==============================================================================
                                                             60.1 g    36.00

Speculative apparent attenuation and resulting ABV
==============================================================================
  Str.    Att.  ABV         Str.    Att.  ABV         Str.    Att.  ABV       
 7.3°P    60%   5.8%       5.5°P    70%   6.8%       3.7°P    80%   7.8%      
 6.4°P    65%   6.3%       4.6°P    75%   7.3%       2.8°P    85%   8.3%      
==============================================================================

```

translated with `wbctool -u us -u sg`:
```
==============================================================================
Name:              MarBock
Final volume:      5.2gal             Boil:                90 min             
IBU (Tinseth):     36.00              BUGU:                0.50               
Color (Morey):     10.7 EBC, 5.4 SRM  Water (68.0°F):      8.9gal             
Pitch rate, ale:   267 billion        Pitch rate, lager:   535 billion        

Yeast:             WLP833
Water notes:       

Preboil  volume  : 7.2gal (158.0°F)   Measured:                               
Preboil  strength: 1.054              Measured:                               
Postboil volume  : 5.9gal (212.0°F)   Measured:                               
Postboil strength: 1.069              Measured:                               

Kettle loss (est): 0.3gal             Fermenter loss (est):0.2gal             
Mash eff (conf) :  88.0%              Brewhouse eff (est): 84.6%              
==============================================================================

Fermentables                                  amount  ext (100%)   ext (88%)
==============================================================================
Mash
------------------------------------------------------------------------------
Avangard Pilsner                 8 15/16 lb ( 75.0%)   7 3/16 lb   6 5/16 lb
Avangard Vienna                    1 3/4 lb ( 15.0%)   1 7/16 lb    1 1/4 lb
Avangard Munich Light             1 3/16 lb ( 10.0%)    15.44 oz    13.58 oz
------------------------------------------------------------------------------
==============================================================================
                                11 15/16 lb (100.0%)   9 9/16 lb   8 7/16 lb

Mashing instructions (for ambient temperature 68.0°F)
==============================================================================
150.8°F: add 3.7gal of water at 172.5°F (1.20 qt/lb, mash vol 4.6gal)
Mashstep water volume: 3.6gal @ 68.0°F
Sparge water volume:   5.4gal @ 179.6°F
==============================================================================

Hops                              AA%                time    amount     IBUs
==============================================================================
Northern Brewer (pellet)          9.9%             90 min   0.89 oz    28.36
Saaz (leaf)                       3.1%             30 min   0.71 oz     4.62
Hallertau (pellet)                3.8%             15 min   0.53 oz     3.02
==============================================================================
                                                            2.12 oz    36.00

Speculative apparent attenuation and resulting ABV
==============================================================================
  Str.    Att.  ABV         Str.    Att.  ABV         Str.    Att.  ABV       
 1.029    60%   5.8%       1.022    70%   6.8%       1.014    80%   7.8%      
 1.025    65%   6.3%       1.018    75%   7.3%       1.011    85%   8.3%      
==============================================================================

```

Example recipe
---
```
name:   Beer from IPAnema
yeast:  US-05
volume: 19.5l
boil:   30min

mashparams:
        temperature: 66degC
        mashin:      3l/kg

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
IBU (Tinseth):     34.60              BUGU:                0.54               
Color (Morey):     12.4 EBC, 6.3 SRM  Water (20.0°C):      29.4l              
Pitch rate, ale:   238 billion        Pitch rate, lager:   476 billion        

Yeast:             US-05
Water notes:       

Preboil  volume  : 23.5l (70.0°C)     Measured:                               
Preboil  strength: 13.6°P             Measured:                               
Postboil volume  : 22.1l (100.0°C)    Measured:                               
Postboil strength: 15.0°P             Measured:                               

Kettle loss (est): 0.9l               Fermenter loss (est):0.8l               
Mash eff (conf) :  88.0%              Brewhouse eff (est): 84.6%              

NOTE: keg hops absorb: 0.3l => effective yield: 19.2l
==============================================================================

Fermentables                                  amount  ext (100%)   ext (88%)
==============================================================================
Mash
------------------------------------------------------------------------------
Briess Pale                         4.00 kg ( 82.0%)     3.14 kg     2.76 kg
Avangard Vienna                       878 g ( 18.0%)       703 g       618 g
------------------------------------------------------------------------------
==============================================================================
                                    4.88 kg (100.0%)     3.84 kg     3.38 kg

Mashing instructions (for ambient temperature 20.0°C)
==============================================================================
66.0°C : add 15.0l of water at 76.5°C (3.00 l/kg, mash vol 18.1l)
Mashstep water volume: 14.6l @ 20.0°C
Sparge water volume:   15.1l @ 82.0°C
==============================================================================

Hops                              AA%                time    amount     IBUs
==============================================================================
Citra (pellet)                    14.0%            30 min    10.0 g    11.87
Mosaic (pellet)                   12.4%            30 min    10.0 g    10.51
Citra (pellet)                    14.0%            12 min    10.0 g     6.48
Mosaic (pellet)                   12.4%            12 min    10.0 g     5.74
------------------------------------------------------------------------------
Citra (pellet)                    14.0%    10min @ 90.0°C    10.0 g     0.00
Mosaic (pellet)                   12.4%    10min @ 90.0°C    10.0 g     0.00
------------------------------------------------------------------------------
Mosaic (pellet)                   12.4%     dryhop in keg    25.0 g     0.00
Citra (pellet)                    14.0%     dryhop in keg    25.0 g     0.00
==============================================================================
                                                              110 g    34.60

Speculative apparent attenuation and resulting ABV
==============================================================================
  Str.    Att.  ABV         Str.    Att.  ABV         Str.    Att.  ABV       
 6.5°P    60%   5.1%       4.9°P    70%   5.9%       3.3°P    80%   6.8%      
 5.7°P    65%   5.5%       4.1°P    75%   6.4%       2.5°P    85%   7.3%      
==============================================================================

```

translated with `wbctool -u us -u sg`:
```
==============================================================================
Name:              Beer from IPAnema
Final volume:      5.2gal             Boil:                30 min             
IBU (Tinseth):     34.60              BUGU:                0.54               
Color (Morey):     12.4 EBC, 6.3 SRM  Water (68.0°F):      7.8gal             
Pitch rate, ale:   238 billion        Pitch rate, lager:   476 billion        

Yeast:             US-05
Water notes:       

Preboil  volume  : 6.2gal (158.0°F)   Measured:                               
Preboil  strength: 1.055              Measured:                               
Postboil volume  : 5.8gal (212.0°F)   Measured:                               
Postboil strength: 1.061              Measured:                               

Kettle loss (est): 0.3gal             Fermenter loss (est):0.2gal             
Mash eff (conf) :  88.0%              Brewhouse eff (est): 84.6%              

NOTE: keg hops absorb: 0.1gal => effective yield: 5.1gal
==============================================================================

Fermentables                                  amount  ext (100%)   ext (88%)
==============================================================================
Mash
------------------------------------------------------------------------------
Briess Pale                      8 13/16 lb ( 82.0%)    6 7/8 lb   6 1/16 lb
Avangard Vienna                    1 7/8 lb ( 18.0%)    1 1/2 lb   1 5/16 lb
------------------------------------------------------------------------------
==============================================================================
                                  10 3/4 lb (100.0%)   8 7/16 lb   7 7/16 lb

Mashing instructions (for ambient temperature 68.0°F)
==============================================================================
150.8°F: add 4.0gal of water at 169.8°F (1.44 qt/lb, mash vol 4.8gal)
Mashstep water volume: 3.9gal @ 68.0°F
Sparge water volume:   4.0gal @ 179.6°F
==============================================================================

Hops                              AA%                time    amount     IBUs
==============================================================================
Citra (pellet)                    14.0%            30 min   0.35 oz    11.87
Mosaic (pellet)                   12.4%            30 min   0.35 oz    10.51
Citra (pellet)                    14.0%            12 min   0.35 oz     6.48
Mosaic (pellet)                   12.4%            12 min   0.35 oz     5.74
------------------------------------------------------------------------------
Citra (pellet)                    14.0%   10min @ 194.0°F   0.35 oz     0.00
Mosaic (pellet)                   12.4%   10min @ 194.0°F   0.35 oz     0.00
------------------------------------------------------------------------------
Mosaic (pellet)                   12.4%     dryhop in keg   0.88 oz     0.00
Citra (pellet)                    14.0%     dryhop in keg   0.88 oz     0.00
==============================================================================
                                                            3.88 oz    34.60

Speculative apparent attenuation and resulting ABV
==============================================================================
  Str.    Att.  ABV         Str.    Att.  ABV         Str.    Att.  ABV       
 1.026    60%   5.1%       1.019    70%   5.9%       1.013    80%   6.8%      
 1.022    65%   5.5%       1.016    75%   6.4%       1.010    85%   7.3%      
==============================================================================

```

