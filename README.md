> **⚠ WARNING:**<br>
> The code in this project is no longer maintained.
> Use it with caution and check for vulnerabilities!

# GIANT for DiViCo

The Group Interaction Analysis Toolkit (GIAnT) is a research tool that visualizes interactions of groups of people in front of a large interactive display wall. **Please note: This is a fork ([original GIAnT](https://github.com/imldresden/GIAnT)) that has been modified and extended to better fit the analysis requirements of the research project https://imld.de/mcv-displaywall ([prototype application](https://github.com/imldresden/mcv-displaywall)).** This version of GIAnT has been used in our publication:

> Ricardo Langner, Ulrike Kister and Raimund Dachselt, "Multiple Coordinated Views at Large Displays for Multiple Users: Empirical Findings on User Behavior, Movements, and Distances" in IEEE
Transactions on Visualization and Computer Graphics, vol. 25, no. 1, 2018.
doi: [10.1109/TVCG.2018.2865235](https://doi.org/10.1109/TVCG.2018.2865235)

**Project website**: Further information, photos, and videos can be found at https://imld.de/mcv-displaywall/.

**Questions**: If you have any questions or you want to give feedback, please contact Ricardo Langner ([institutional website](https://imld.de/en/our-group/team/ricardo-langner/)), [GitHub](https://github.com/derric)) or Marc Satkowski ([institutional website](https://imld.de/en/our-group/team/marc-satkowski/), [GitHub](https://github.com/satkowski)).

## Installing GIAnT

This research prototyp only works on **Linux** or **Mac**. We developed this prototyp with Python 2.7. After installing Python you need to install some other dependencies:
+ [libavg](https://www.libavg.de/site/)
+ [PyGLM](https://github.com/imldresden/PyGLM)
+ [HeatMapNode](https://github.com/imldresden/HeatMapNode)
+ numpy (>= 1.13.1)

Further you need to install GIAnT itself. GIAnT uses a small libavg plugin to display the visualizations which is built using CMake:
```bash
$ cd GIAnT/plugin
$ mkdir build && cd build
$ cmake ..
$ make -j5
$ sudo make install
```

## Development

This project is developed by [Marc Satkowski](https://github.com/satkowski), Ulrike Kister and [Ricardo Langner](https://github.com/derric) at the [Interactive Media Lab Dresden](https://imld.de/), Technische Universität Dresden, Germany. Further development information can be found via the [develpoment guide](DEVELOPMENT.md).

## Acknowledgements

The basis for this prototyp was provided by [Ulrich von Zadow](https://github.com/uzadow).
