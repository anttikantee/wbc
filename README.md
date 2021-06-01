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
  * `wbcsolve`: takes two of {volume, extract, strength} and
    calculates the missing value, making it for example possible to
    "play with" simple sugar recipes, or calculate "ppg" from
    the extract percentage commonly found on a nutrition labels

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

    package:
        table sugar:            5g/l

hops:
    - [ [ Magnum,    12.7%, ], 0.42 Recipe BUGU, boiltime ]
    - [ [ Tettnanger, 3.7%, ], 1 g/l,              30 min ]
    - [ [ Tettnanger, 3.7%, ], 1 g/l,              15 min ]
```
translated with `wbcrecipe -P units_output=metric -P strength_output=plato`:
```
===============================================================================
Name:               MarBock
Aggregate strength: 16.8°P             Package volume: 19.0L                    
Total fermentables: 5.72 kg            Total hops:     52.4 g                   
Tinseth IBU / BUGU: 29  / 0.42         Color (Morey):  11.2 EBC, 5.7 SRM        
Loss (v/e) Kettle:  1.5L / 265 g       Fermentor:      8.0dL / 140 g            
Boil:               60 min             Yeast:          WLP833                   
Water (20.0°C):     31.6L              Brewhouse eff:  78.9%                    

Preboil  volume  :  25.8L (100.0°C)    Measured:                                
Preboil  strength:  14.2°P             Measured:                                
Postboil volume  :  22.2L (100.0°C)    Measured:                                
Postboil strength:  16.4°P             Measured:                                

Pitch rate, ale:    242 billion        Pitch rate, lager:    485 billion        
===============================================================================
Ta=20degC|Tb=100degC|Tp=100degC|Ts=82degC|bo=3.5l|fl=0.8l|ga=1.50L/kg|kl=1.2l
|me=88%|mh=1.5|ml=1l|mr=50%|mt=transfer|so=plato|uo=metric
===============================================================================

Fermentables                                    amount  ext (100%)   ext (pkg)
===============================================================================
Mash
Avangard Pilsner                      4.46 kg ( 77.9%)     3.36 kg     2.63 kg
Weyermann Munich I                      503 g (  8.8%)       382 g       300 g
Avangard Vienna                         503 g (  8.8%)       374 g       294 g
Weyermann Melanoidin                    160 g (  2.8%)       115 g      90.0 g
                                      5.62 kg ( 98.3%)     4.23 kg     3.32 kg
-------------------------------------------------------------------------------
Package
table sugar                            95.0 g (  1.7%)      95.0 g      95.0 g
===============================================================================
                                      5.72 kg (100.0%)     4.32 kg     3.41 kg

Mashstep          Time                Adjustment           Ratio        Volume
===============================================================================
63.0°C          30 min           15.7L @  73.2°C       2.72 L/kg         19.6L
70.0°C          45 min            4.9L @ 100.0°C       3.56 L/kg         24.8L
-------------------------------------------------------------------------------
Mashstep water:     20.0L @ 20.0°C (1st runnings: ~13.2L @ 70.0°C)
Sparge water:       11.9L @ 82.0°C (11.6L @ 20.0°C)
1st wort (conv. %): 15.2°P (85%), 16.0°P (90%), 16.7°P (95%), 17.4°P (100%)
===============================================================================

Additions & Hops                        IBUs      amount    timespec     timer
===============================================================================
Magnum                    [T90  12.7%]  19.4      14.3 g      @ boil    30 min
Tettnanger                [T90   3.7%]   5.8      19.0 g      30 min    15 min
Tettnanger                [T90   3.7%]   3.7      19.0 g      15 min    15 min
===============================================================================

Speculative apparent attenuation and resulting ABV
===============================================================================
  Str.    Att.  ABV         Str.    Att.  ABV         Str.    Att.  ABV       
 7.0°P    60%   5.3%       4.4°P    75%   6.8%       1.8°P    90%   8.3%      
 6.1°P    65%   5.8%       3.5°P    80%   7.3%       0.9°P    95%   8.8%      
 5.2°P    70%   6.3%       2.6°P    85%   7.8%       0.0°P    100%  9.3%      
===============================================================================

```

translated with `wbcrecipe -P units_output=us -P strength_output=sg`:
```
===============================================================================
Name:               MarBock
Aggregate strength: 1.069              Package volume: 5.0gal                   
Total fermentables: 12 9/16 lb         Total hops:     1.85 oz                  
Tinseth IBU / BUGU: 29  / 0.42         Color (Morey):  11.2 EBC, 5.7 SRM        
Loss (v/e) Kettle:  1.6qt / 9.35 oz    Fermentor:      3.4cup / 4.94 oz         
Boil:               60 min             Yeast:          WLP833                   
Water (68.0°F):     8.3gal             Brewhouse eff:  78.9%                    

Preboil  volume  :  6.8gal (212.0°F)   Measured:                                
Preboil  strength:  1.058              Measured:                                
Postboil volume  :  5.9gal (212.0°F)   Measured:                                
Postboil strength:  1.067              Measured:                                

Pitch rate, ale:    242 billion        Pitch rate, lager:    485 billion        
===============================================================================
Ta=20degC|Tb=100degC|Tp=100degC|Ts=82degC|bo=3.5l|fl=0.8l|ga=1.50L/kg|kl=1.2l
|me=88%|mh=1.5|ml=1l|mr=50%|mt=transfer|so=sg|uo=us
===============================================================================

Fermentables                                    amount  ext (100%)   ext (pkg)
===============================================================================
Mash
Avangard Pilsner                   9 13/16 lb ( 77.9%)    7 3/8 lb    5 3/4 lb
Weyermann Munich I                  1 1/16 lb (  8.8%)    13.47 oz    10.57 oz
Avangard Vienna                     1 1/16 lb (  8.8%)    13.21 oz    10.36 oz
Weyermann Melanoidin                  5.65 oz (  2.8%)     4.05 oz     3.18 oz
                                    12 3/8 lb ( 98.3%)   9 5/16 lb    7 1/4 lb
-------------------------------------------------------------------------------
Package
table sugar                           3.35 oz (  1.7%)     3.35 oz     3.35 oz
===============================================================================
                                   12 9/16 lb (100.0%)    9 1/2 lb    7 1/2 lb

Mashstep          Time                Adjustment           Ratio        Volume
===============================================================================
145.4°F         30 min          4.1gal @ 163.8°F      5.67 qt/lb        5.2gal
158.0°F         45 min          1.3gal @ 212.0°F      7.42 qt/lb        6.6gal
-------------------------------------------------------------------------------
Mashstep water:     5.3gal @ 68.0°F (1st runnings: ~3.5gal @ 158.0°F)
Sparge water:       3.1gal @ 179.6°F (3.1gal @ 68.0°F)
1st wort (conv. %): 1.062 (85%), 1.065 (90%), 1.069 (95%), 1.072 (100%)
===============================================================================

Additions & Hops                        IBUs      amount    timespec     timer
===============================================================================
Magnum                    [T90  12.7%]  19.4     0.51 oz      @ boil    30 min
Tettnanger                [T90   3.7%]   5.8     0.67 oz      30 min    15 min
Tettnanger                [T90   3.7%]   3.7     0.67 oz      15 min    15 min
===============================================================================

Speculative apparent attenuation and resulting ABV
===============================================================================
  Str.    Att.  ABV         Str.    Att.  ABV         Str.    Att.  ABV       
 1.028    60%   5.3%       1.017    75%   6.8%       1.007    90%   8.3%      
 1.024    65%   5.8%       1.014    80%   7.3%       1.003    95%   8.8%      
 1.021    70%   6.3%       1.010    85%   7.8%       1.000    100%  9.3%      
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

        fermentor:
                table sugar:       5%

defs:
        - [ &mosaic [ Mosaic,    12.4%,  T90 ] ]
        - [ &citra  [ Citra,     14.0%,  T90 ] ]

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
Aggregate strength: 16.0°P             Package volume: 19.5L                    
Total fermentables: 5.59 kg            Total hops:     196 g                    
Tinseth IBU / BUGU: 19  / 0.30         Color (Morey):  11.2 EBC, 5.7 SRM        
Loss (v/e) Kettle:  1.6L / 256 g       Fermentor:      9.3dL / 159 g            
Boil:               20 min             Yeast:          WLP095                   
Water (20.0°C):     29.6L              Brewhouse eff:  78.9%                    

Preboil  volume  :  24.0L (100.0°C)    Measured:                                
Preboil  strength:  14.2°P             Measured:                                
Postboil volume  :  22.8L (100.0°C)    Measured:                                
Postboil strength:  14.9°P             Measured:                                

Pitch rate, ale:    245 billion        Pitch rate, lager:    490 billion        

NOTE: package hops absorb: 6.2dL => effective yield: 18.9L
NOTE: package hop volume: ~2.1dL => packaged volume: 19.7L
===============================================================================
Ta=20degC|Tb=100degC|Tp=100degC|Ts=82degC|bo=3.5l|fl=0.8l|ga=1.50L/kg|kl=1.2l
|me=88%|mh=1.5|ml=1l|mr=50%|mt=transfer|so=plato|uo=metric
===============================================================================

Fermentables                                    amount  ext (100%)   ext (pkg)
===============================================================================
Mash
Briess Pale                           3.75 kg ( 67.0%)     2.82 kg     2.20 kg
Avangard Vienna                       1.01 kg ( 18.0%)       749 g       582 g
flaked oats                             559 g ( 10.0%)       360 g       280 g
                                      5.31 kg ( 95.0%)     3.93 kg     3.06 kg
-------------------------------------------------------------------------------
Ferment
table sugar                             280 g (  5.0%)       280 g       267 g
===============================================================================
                                      5.59 kg (100.0%)     4.21 kg     3.32 kg

Mashstep          Time                Adjustment           Ratio        Volume
===============================================================================
66.0°C             UNS           19.3L @  74.6°C       3.54 L/kg         23.0L
-------------------------------------------------------------------------------
Mashstep water:     18.8L @ 20.0°C (1st runnings: ~12.2L @ 66.0°C)
Sparge water:       11.1L @ 82.0°C (10.8L @ 20.0°C)
1st wort (conv. %): 15.1°P (85%), 15.9°P (90%), 16.6°P (95%), 17.3°P (100%)
===============================================================================

Additions & Hops                        IBUs      amount    timespec     timer
===============================================================================
Citra                     [T90  14.0%]   9.1      10.0 g      @ boil        ==
Mosaic                    [T90  12.4%]   8.0      10.0 g      @ boil    18 min
Citra                     [T90  14.0%]   1.3      10.0 g       2 min        ==
Mosaic                    [T90  12.4%]   1.1      10.0 g       2 min     2 min
-------------------------------------------------------------------------------
Citra                     [T90  14.0%]   0.0      15.0 g    @ 85.0°C        ==
Mosaic                    [T90  12.4%]   0.0      15.0 g    @ 85.0°C    10 min
-------------------------------------------------------------------------------
Citra                     [T90  14.0%]   0.0      11.0 g   fermentor  3d -> 0d
Mosaic                    [T90  12.4%]   0.0      11.0 g   fermentor  3d -> 0d
-------------------------------------------------------------------------------
Citra                     [T90  14.0%]   0.0      52.0 g     package   package
Mosaic                    [T90  12.4%]   0.0      52.0 g     package   package
===============================================================================

Speculative apparent attenuation and resulting ABV
===============================================================================
  Str.    Att.  ABV         Str.    Att.  ABV         Str.    Att.  ABV       
 6.6°P    60%   5.1%       4.2°P    75%   6.4%       1.7°P    90%   7.9%      
 5.8°P    65%   5.5%       3.3°P    80%   6.9%       0.8°P    95%   8.3%      
 5.0°P    70%   6.0%       2.5°P    85%   7.4%       0.0°P    100%  8.8%      
===============================================================================

```

translated with `wbcrecipe -P units_output=us -P strength_output=sg`:
```
===============================================================================
Name:               Return to IPAnema
Aggregate strength: 1.065              Package volume: 5.2gal                   
Total fermentables: 12 5/16 lb         Total hops:     6.91 oz                  
Tinseth IBU / BUGU: 19  / 0.30         Color (Morey):  11.2 EBC, 5.7 SRM        
Loss (v/e) Kettle:  1.7qt / 9.04 oz    Fermentor:      3.9cup / 5.60 oz         
Boil:               20 min             Yeast:          WLP095                   
Water (68.0°F):     7.8gal             Brewhouse eff:  78.9%                    

Preboil  volume  :  6.4gal (212.0°F)   Measured:                                
Preboil  strength:  1.058              Measured:                                
Postboil volume  :  6.0gal (212.0°F)   Measured:                                
Postboil strength:  1.061              Measured:                                

Pitch rate, ale:    245 billion        Pitch rate, lager:    490 billion        

NOTE: package hops absorb: 2.6cup => effective yield: 5.0gal
NOTE: package hop volume: ~42.2tsp => packaged volume: 5.2gal
===============================================================================
Ta=20degC|Tb=100degC|Tp=100degC|Ts=82degC|bo=3.5l|fl=0.8l|ga=1.50L/kg|kl=1.2l
|me=88%|mh=1.5|ml=1l|mr=50%|mt=transfer|so=sg|uo=us
===============================================================================

Fermentables                                    amount  ext (100%)   ext (pkg)
===============================================================================
Mash
Briess Pale                          8 1/4 lb ( 67.0%)   6 3/16 lb  4 13/16 lb
Avangard Vienna                     2 3/16 lb ( 18.0%)    1 5/8 lb    1 1/4 lb
flaked oats                         1 3/16 lb ( 10.0%)    12.70 oz     9.88 oz
                                  11 11/16 lb ( 95.0%)    8 5/8 lb  6 11/16 lb
-------------------------------------------------------------------------------
Ferment
table sugar                           9.86 oz (  5.0%)     9.86 oz     9.41 oz
===============================================================================
                                   12 5/16 lb (100.0%)    9 1/4 lb   7 5/16 lb

Mashstep          Time                Adjustment           Ratio        Volume
===============================================================================
150.8°F            UNS          5.1gal @ 166.3°F      7.38 qt/lb        6.1gal
-------------------------------------------------------------------------------
Mashstep water:     5.0gal @ 68.0°F (1st runnings: ~3.2gal @ 150.8°F)
Sparge water:       2.9gal @ 179.6°F (2.9gal @ 68.0°F)
1st wort (conv. %): 1.062 (85%), 1.065 (90%), 1.068 (95%), 1.071 (100%)
===============================================================================

Additions & Hops                        IBUs      amount    timespec     timer
===============================================================================
Citra                     [T90  14.0%]   9.1     0.35 oz      @ boil        ==
Mosaic                    [T90  12.4%]   8.0     0.35 oz      @ boil    18 min
Citra                     [T90  14.0%]   1.3     0.35 oz       2 min        ==
Mosaic                    [T90  12.4%]   1.1     0.35 oz       2 min     2 min
-------------------------------------------------------------------------------
Citra                     [T90  14.0%]   0.0     0.53 oz   @ 185.0°F        ==
Mosaic                    [T90  12.4%]   0.0     0.53 oz   @ 185.0°F    10 min
-------------------------------------------------------------------------------
Citra                     [T90  14.0%]   0.0     0.39 oz   fermentor  3d -> 0d
Mosaic                    [T90  12.4%]   0.0     0.39 oz   fermentor  3d -> 0d
-------------------------------------------------------------------------------
Citra                     [T90  14.0%]   0.0     1.83 oz     package   package
Mosaic                    [T90  12.4%]   0.0     1.83 oz     package   package
===============================================================================

Speculative apparent attenuation and resulting ABV
===============================================================================
  Str.    Att.  ABV         Str.    Att.  ABV         Str.    Att.  ABV       
 1.026    60%   5.1%       1.016    75%   6.4%       1.007    90%   7.9%      
 1.023    65%   5.5%       1.013    80%   6.9%       1.003    95%   8.3%      
 1.020    70%   6.0%       1.010    85%   7.4%       1.000    100%  8.8%      
===============================================================================

```

