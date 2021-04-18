WBC Brew-Calculator
===================

WBC is suite of homebrew software performing various calculation tasks.
The main utility turns recipes into a brewday summary, while supporting
utilities provide information about the beer.  The recipe utility is
discussed below.  The other utilties are:

  * `wbcabv`: calculate ABV, ABW and residual extract (w/v) from
    original and final strength
  * `wbccool`: calculate cooling efficiency, water usage or ice usage
    required to cool wort of given strength from a starting temperature
    to a desired temperature
  * `wbcadjust`: calculate the aggregate solution [and optionally a predicted
    final strength] when adjusting extract/water in a given wort/must/wash,
    e.g. adding priming sugar to already fermented beer, or boiling off
    a certain volume
  * `wbckegp`: takes two of {pressure, temperature, dissolved CO2} and
    calculates the missing value, along with headspace CO2 required to
    push the beer out

`wbcrecipe`
-----------

The `wbcrecipe` utility takes in a recipe and dumps out a
printable brewday summary, as demonstrated by the [examples](#examples).
The goal of `wbcrecipe` is to replace pen-and-paper calculations.  The goal of
`wbcrecipe` is not to think for the brewer and not to be so sophisticated that
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
  * calculate water temperatures and volumes for multi-step infusion
    mashes.  calculate decoction sizes.
  * calculate IBUs and optionally calculate hop additions based on
    desired IBUs
  * scales recipes to desired final volume
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
boil:   60min
volume: 19l

mashparams:
    temperatures: [ 30min @ 63degC, 45min @ 70degC ]

fermentables:
    strength: 16.8 degP

    mash:
        Avangard Pilsner:       rest
        Avangard Vienna:        8.8%
        Weyermann Munich I:     8.8%
        Weyermann Melanoidin:   2.8%

hops:
    - [ [ Magnum,    12.7%, ], 0.42 Recipe BUGU, boiltime ]
    - [ [ Tettnanger, 3.7%, ], 1 g/l,              30 min ]
    - [ [ Tettnanger, 3.7%, ], 1 g/l,              15 min ]
```
translated with `wbcrecipe -P units_output=metric -P strength_output=plato`:
```
===============================================================================
Name:               MarBock
Aggregate strength: TBD                Package volume: 19.0l                    
Total fermentables: 5.75 kg            Total hops:     54.4 g                   
IBU (Tinseth):      31.14              BUGU:           0.42                     
Boil:               60min              Yeast:          WLP833                   
Water (20.0°C):     32.1l              Color (Morey):  12.1 EBC, 6.2 SRM        

Preboil  volume  :  25.3l (70.0°C)     Measured:                                
Preboil  strength:  14.6°P             Measured:                                
Postboil volume  :  22.2l (100.0°C)    Measured:                                
Postboil strength:  16.8°P             Measured:                                

Kettle loss (est):  1.5l               Fermenter loss (est): 8.0dl              
Mash eff (conf) :   88.0%              Brewhouse eff (est):  85.5%              

Pitch rate, ale:    267 billion        Pitch rate, lager:    534 billion        
===============================================================================
bo:3.5l|fl:0.8l|ga:1.1l/kg|kl:1.2l|me:88%|mh:1.5|ml:1l|mr:50%|mt:transfer
|so:plato|st:82degC|ta:20degC|tb:100degC|tp:70degC|uo:metric
===============================================================================

Fermentables                                    amount  ext (100%)   ext (88%)
===============================================================================
Mash
Avangard Pilsner                      4.58 kg ( 79.6%)     3.47 kg     3.05 kg
Weyermann Munich I                      506 g (  8.8%)       386 g       339 g
Avangard Vienna                         506 g (  8.8%)       379 g       333 g
Weyermann Melanoidin                    161 g (  2.8%)       116 g       102 g
                                      5.75 kg (100.0%)     4.35 kg     3.83 kg
===============================================================================
                                      5.75 kg (100.0%)     4.35 kg     3.83 kg

Mashstep          Time                Adjustment           Ratio        Volume
===============================================================================
63.0°C          30 min           15.0l @  73.8°C       2.55 l/kg         18.7l
70.0°C          45 min            4.8l @ 100.0°C       3.35 l/kg         23.3l
-------------------------------------------------------------------------------
Mashstep water:     19.2l @ 20.0°C (1st runnings: ~11.9l)
Sparge water:       13.3l @ 82.0°C
1st wort (conv. %): 15.7°P (85%), 16.6°P (90%), 17.5°P (95%), 18.4°P (100%)
===============================================================================

Additions & Hops                   AA%  IBUs      amount    timespec     timer
===============================================================================
Magnum (pellet)                  12.7%  21.8      16.4 g      @ boil    30 min
Tettnanger (pellet)               3.7%   5.7      19.0 g      30 min    15 min
Tettnanger (pellet)               3.7%   3.7      19.0 g      15 min    15 min
===============================================================================

Speculative apparent attenuation and resulting ABV
===============================================================================
  Str.    Att.  ABV         Str.    Att.  ABV         Str.    Att.  ABV       
 7.5°P    60%   5.8%       5.6°P    70%   6.8%       3.8°P    80%   7.9%      
 6.6°P    65%   6.3%       4.7°P    75%   7.3%       2.8°P    85%   8.4%      
===============================================================================

```

translated with `wbcrecipe -P units_output=us -P strength_output=sg`:
```
===============================================================================
Name:               MarBock
Aggregate strength: TBD                Package volume: 5.0gal                   
Total fermentables: 12 5/8 lb          Total hops:     1.92 oz                  
IBU (Tinseth):      31.14              BUGU:           0.42                     
Boil:               60min              Yeast:          WLP833                   
Water (68.0°F):     8.5gal             Color (Morey):  12.1 EBC, 6.2 SRM        

Preboil  volume  :  6.7gal (158.0°F)   Measured:                                
Preboil  strength:  1.059              Measured:                                
Postboil volume  :  5.9gal (212.0°F)   Measured:                                
Postboil strength:  1.069              Measured:                                

Kettle loss (est):  1.6qt              Fermenter loss (est): 0.8qt              
Mash eff (conf) :   88.0%              Brewhouse eff (est):  85.5%              

Pitch rate, ale:    267 billion        Pitch rate, lager:    534 billion        
===============================================================================
bo:3.5l|fl:0.8l|ga:1.1l/kg|kl:1.2l|me:88%|mh:1.5|ml:1l|mr:50%|mt:transfer
|so:sg|st:82degC|ta:20degC|tb:100degC|tp:70degC|uo:us
===============================================================================

Fermentables                                    amount  ext (100%)   ext (88%)
===============================================================================
Mash
Avangard Pilsner                   10 1/16 lb ( 79.6%)    7 5/8 lb  6 11/16 lb
Weyermann Munich I                  1 1/16 lb (  8.8%)    13.61 oz    11.97 oz
Avangard Vienna                     1 1/16 lb (  8.8%)    13.36 oz    11.76 oz
Weyermann Melanoidin                  5.68 oz (  2.8%)     4.10 oz     3.60 oz
                                    12 5/8 lb (100.0%)   9 9/16 lb   8 7/16 lb
===============================================================================
                                    12 5/8 lb (100.0%)   9 9/16 lb   8 7/16 lb

Mashstep          Time                Adjustment           Ratio        Volume
===============================================================================
145.4°F         30 min          4.0gal @ 164.9°F      5.32 qt/lb        4.9gal
158.0°F         45 min          1.3gal @ 212.0°F      6.98 qt/lb        6.1gal
-------------------------------------------------------------------------------
Mashstep water:     5.1gal @ 68.0°F (1st runnings: ~3.1gal)
Sparge water:       3.5gal @ 179.6°F
1st wort (conv. %): 1.064 (85%), 1.068 (90%), 1.072 (95%), 1.076 (100%)
===============================================================================

Additions & Hops                   AA%  IBUs      amount    timespec     timer
===============================================================================
Magnum (pellet)                  12.7%  21.8     0.58 oz      @ boil    30 min
Tettnanger (pellet)               3.7%   5.7     0.67 oz      30 min    15 min
Tettnanger (pellet)               3.7%   3.7     0.67 oz      15 min    15 min
===============================================================================

Speculative apparent attenuation and resulting ABV
===============================================================================
  Str.    Att.  ABV         Str.    Att.  ABV         Str.    Att.  ABV       
 1.030    60%   5.8%       1.022    70%   6.8%       1.015    80%   7.9%      
 1.026    65%   6.3%       1.019    75%   7.3%       1.011    85%   8.4%      
===============================================================================

```

Example recipe
---
```
name:   Return to IPAnema
yeast:  WLP095
volume: 19.5l
boil:   20min

mashparams:
        temperature: 66degC

fermentables:
        strength: 16degP

        mash:
                Briess Pale:     rest
                Avangard Vienna:  18%
                flaked oats:      10%

        ferment:
                table sugar:       5%

defs:
        - [ &mosaic [ Mosaic,    12.4%,  pellet ] ]
        - [ &citra  [ Citra,     14.0%,  pellet ] ]

hops:
        - [ *citra,      10g, 20 min ]
        - [ *mosaic,     10g, 20 min ]
        - [ *citra,      10g,  2 min ]
        - [ *mosaic,     10g,  2 min ]

        - [ *citra,      15g, 10min @ 85degC ]
        - [ *mosaic,     15g, 10min @ 85degC ]

        - [ *citra,      11g, 3 day -> 0 day ]
        - [ *mosaic,     11g, 3 day -> 0 day ]
        - [ *citra,      52g, package ]
        - [ *mosaic,     52g, package ]
```
translated with `wbcrecipe -P units_output=metric -P strength_output=plato`:
```
===============================================================================
Name:               Return to IPAnema
Aggregate strength: TBD                Package volume: 19.5l                    
Total fermentables: 5.61 kg            Total hops:     196 g                    
IBU (Tinseth):      19.33              BUGU:           0.27                     
Boil:               20min              Yeast:          WLP095                   
Water (20.0°C):     30.1l              Color (Morey):  12.2 EBC, 6.2 SRM        

Preboil  volume  :  23.7l (70.0°C)     Measured:                                
Preboil  strength:  14.2°P             Measured:                                
Postboil volume  :  23.0l (100.0°C)    Measured:                                
Postboil strength:  14.9°P             Measured:                                

Kettle loss (est):  1.6l               Fermenter loss (est): 9.3dl              
Mash eff (conf) :   88.0%              Brewhouse eff (est):  85.7%              

Pitch rate, ale:    263 billion        Pitch rate, lager:    526 billion        

NOTE: package hops absorb: 6.2dl => effective yield: 18.9l
NOTE: package hop volume: ~2.1dl => packaged volume: 19.7l
===============================================================================
bo:3.5l|fl:0.8l|ga:1.1l/kg|kl:1.2l|me:88%|mh:1.5|ml:1l|mr:50%|mt:transfer
|so:plato|st:82degC|ta:20degC|tb:100degC|tp:70degC|uo:metric
===============================================================================

Fermentables                                    amount  ext (100%)   ext (88%)
===============================================================================
Mash
Briess Pale                           3.76 kg ( 67.0%)     2.83 kg     2.49 kg
Avangard Vienna                       1.01 kg ( 18.0%)       757 g       666 g
flaked oats                             561 g ( 10.0%)       362 g       318 g
                                      5.33 kg ( 95.0%)     3.95 kg     3.48 kg
-------------------------------------------------------------------------------
Ferment
table sugar                             281 g (  5.0%)       281 g       281 g
===============================================================================
                                      5.61 kg (100.0%)     4.23 kg     3.76 kg

Mashstep          Time                Adjustment           Ratio        Volume
===============================================================================
66.0°C             UNS           18.4l @  75.0°C       3.37 l/kg         21.7l
-------------------------------------------------------------------------------
Mashstep water:     18.0l @ 20.0°C (1st runnings: ~11.1l)
Sparge water:       12.4l @ 82.0°C
1st wort (conv. %): 15.3°P (85%), 16.2°P (90%), 17.1°P (95%), 18.0°P (100%)
===============================================================================

Additions & Hops                   AA%  IBUs      amount    timespec     timer
===============================================================================
Citra (pellet)                   14.0%   9.0      10.0 g      @ boil        ==
Mosaic (pellet)                  12.4%   8.0      10.0 g      @ boil    18 min
Citra (pellet)                   14.0%   1.3      10.0 g       2 min        ==
Mosaic (pellet)                  12.4%   1.1      10.0 g       2 min     2 min
-------------------------------------------------------------------------------
Citra (pellet)                   14.0%   0.0      15.0 g    @ 85.0°C        ==
Mosaic (pellet)                  12.4%   0.0      15.0 g    @ 85.0°C    10 min
-------------------------------------------------------------------------------
Citra (pellet)                   14.0%   0.0      11.0 g   fermentor  3d -> 0d
Mosaic (pellet)                  12.4%   0.0      11.0 g   fermentor  3d -> 0d
-------------------------------------------------------------------------------
Citra (pellet)                   14.0%   0.0      52.0 g     package   package
Mosaic (pellet)                  12.4%   0.0      52.0 g     package   package
===============================================================================

Speculative apparent attenuation and resulting ABV
===============================================================================
  Str.    Att.  ABV         Str.    Att.  ABV         Str.    Att.  ABV       
 7.1°P    60%   5.5%       5.4°P    70%   6.5%       3.6°P    80%   7.5%      
 6.3°P    65%   6.0%       4.5°P    75%   7.0%       2.7°P    85%   8.0%      
===============================================================================

```

translated with `wbcrecipe -P units_output=us -P strength_output=sg`:
```
===============================================================================
Name:               Return to IPAnema
Aggregate strength: TBD                Package volume: 5.2gal                   
Total fermentables: 12 3/8 lb          Total hops:     6.91 oz                  
IBU (Tinseth):      19.33              BUGU:           0.27                     
Boil:               20min              Yeast:          WLP095                   
Water (68.0°F):     7.9gal             Color (Morey):  12.2 EBC, 6.2 SRM        

Preboil  volume  :  6.3gal (158.0°F)   Measured:                                
Preboil  strength:  1.058              Measured:                                
Postboil volume  :  6.1gal (212.0°F)   Measured:                                
Postboil strength:  1.061              Measured:                                

Kettle loss (est):  1.7qt              Fermenter loss (est): 1.0qt              
Mash eff (conf) :   88.0%              Brewhouse eff (est):  85.7%              

Pitch rate, ale:    263 billion        Pitch rate, lager:    526 billion        

NOTE: package hops absorb: 0.7qt => effective yield: 5.0gal
NOTE: package hop volume: ~0.2qt => packaged volume: 5.2gal
===============================================================================
bo:3.5l|fl:0.8l|ga:1.1l/kg|kl:1.2l|me:88%|mh:1.5|ml:1l|mr:50%|mt:transfer
|so:sg|st:82degC|ta:20degC|tb:100degC|tp:70degC|uo:us
===============================================================================

Fermentables                                    amount  ext (100%)   ext (88%)
===============================================================================
Mash
Briess Pale                          8 1/4 lb ( 67.0%)   6 3/16 lb   5 7/16 lb
Avangard Vienna                     2 3/16 lb ( 18.0%)    1 5/8 lb   1 7/16 lb
flaked oats                         1 3/16 lb ( 10.0%)    12.75 oz    11.22 oz
                                    11 3/4 lb ( 95.0%)  8 11/16 lb    7 5/8 lb
-------------------------------------------------------------------------------
Ferment
table sugar                           9.90 oz (  5.0%)     9.90 oz     9.90 oz
===============================================================================
                                    12 3/8 lb (100.0%)   9 5/16 lb    8 1/4 lb

Mashstep          Time                Adjustment           Ratio        Volume
===============================================================================
150.8°F            UNS          4.9gal @ 167.0°F      7.03 qt/lb        5.7gal
-------------------------------------------------------------------------------
Mashstep water:     4.7gal @ 68.0°F (1st runnings: ~2.9gal)
Sparge water:       3.3gal @ 179.6°F
1st wort (conv. %): 1.062 (85%), 1.066 (90%), 1.070 (95%), 1.074 (100%)
===============================================================================

Additions & Hops                   AA%  IBUs      amount    timespec     timer
===============================================================================
Citra (pellet)                   14.0%   9.0     0.35 oz      @ boil        ==
Mosaic (pellet)                  12.4%   8.0     0.35 oz      @ boil    18 min
Citra (pellet)                   14.0%   1.3     0.35 oz       2 min        ==
Mosaic (pellet)                  12.4%   1.1     0.35 oz       2 min     2 min
-------------------------------------------------------------------------------
Citra (pellet)                   14.0%   0.0     0.53 oz   @ 185.0°F        ==
Mosaic (pellet)                  12.4%   0.0     0.53 oz   @ 185.0°F    10 min
-------------------------------------------------------------------------------
Citra (pellet)                   14.0%   0.0     0.39 oz   fermentor  3d -> 0d
Mosaic (pellet)                  12.4%   0.0     0.39 oz   fermentor  3d -> 0d
-------------------------------------------------------------------------------
Citra (pellet)                   14.0%   0.0     1.83 oz     package   package
Mosaic (pellet)                  12.4%   0.0     1.83 oz     package   package
===============================================================================

Speculative apparent attenuation and resulting ABV
===============================================================================
  Str.    Att.  ABV         Str.    Att.  ABV         Str.    Att.  ABV       
 1.028    60%   5.5%       1.021    70%   6.5%       1.014    80%   7.5%      
 1.025    65%   6.0%       1.018    75%   7.0%       1.011    85%   8.0%      
===============================================================================

```

