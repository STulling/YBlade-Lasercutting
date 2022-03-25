# YBlade (Lasercutting) - QBlade to lasercutting svg

Simple script that takes [QBlade](https://http://www.q-blade.org/) blade description and
constructs the blade as lasercutting paths in svg. It includes tally marks to keep track of the order of the blades (since svg text to paths was being wonky) and vent holes to prevent balooning. It also includes a kerf testing print that will help with figuring out which kerf offset you would want to use for a snug fit.

<img src="./bladeExample2/ribs.svg" style="width:100%;height:600px;">

<img src="./bladeExample2/beam.svg" style="width:100%;height:100px;">

## Usage

First, use QBlade to design your blade. Then export the blade table and profile
data. Then adjust some variables in the script and run it. See the example in [bladeExample2](bladeExample2).
Blades with multiple profiles are supported.

You probably need to do nesting yourself using a tool like [DeepNest](https://deepnest.io/)

//TODO: improve user interaction
