# LCSCtoEAGLE
Easily convert a part from the LCSC cataloge to a EAGLE/Fusion 360 Electronics custom parts library.

## What is this?
A quick project that I made to convert parts from the LCSC or JLC PCB catalogue into a EAGLE/Fusion 360 Electronics library which will allow you to use the parts in your PCB designs.

## Use
It is not very user friendly but edit the runConvert.py file and edit what part numbers you want in your library. Then after running runConvert.py you will get a library at library.lbr which you can load into Fusion.

## No Guarantee
There are likely many errors in this program like incorrect sizing and missing types of elements. This is a very bare-bones implementation. So please keep in mind that you should double-check against the manufacturer datasheet and make sure that sizes are the same. Let me know if you find any issues!
