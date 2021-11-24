# miningOptimizer v0.5

This Python code iteratively tests mining hashrate on Nvidia GPUs with different overclocking settings. These setting limits should be set: low limit, high limit, and a step. The settings are applied for GPU power, GPU core clock and GPU memory clock. If the core clock setting is 500 or lower, it is considered as offset, while higher values are absolute clocks. Tests will run on predefined GPUs, so that multiple GPUs will be tested sequentally (same limits for all the GPUs). For each GPU, first, power limit and core clock is locked and memory settings are tested from low limit to high limit. After memory high limit is reached, the core clock is increased by the predefined step and memory iteration start from the low limit again and when core high limit is reached, power is increased, and so on.

Current hashrate, efficiency (hash/W) and power consumption are printed continuously on terminal. Program is reading the hashrate using a miner API and GPU power is read using Nvidia API (nvidia-smi). After the GPU test is completed, the best hashrate settings are set on the GPU. All the results can be saved also on a file for careful analysis as the best hashrate settings are not usually with best efficiency.

Currently support these miners: t-rex, Phoenixminer, Nbminer

The code will use 'nvidia-smi' and 'nvidia-settings' which should come with Nvidia drivers in Linux. The 'nvidia-settings' program is Linux only, so this code will run correctly ONLY in Linux!

Admin priviledges needed for:
 - Setting GPU power
 - Setting absolute core clock

No admin needed for:
 - Setting core clock offset
 - Setting memory clock offset

Tested with:
- Ubuntu 20.04, HiveOS 5.0.21-201105
- Python 3.6, Python 3.8
- RTX 3060Ti, RTX3070

Python modules used:
socket, json, requests, subprocess, time

USAGE:
- open the miningOptimizer.py file with some text editor and edit the settings for your needs, save the changes
- on terminal, type "sudo python3 miningOptimizer.py"

ISSUES:

- Currently tested only with RTX3060Ti and RTX3070. Mixing new and old generation 
GPUs in the testing set may or propably will cause problems. 

SUPPORT:
- report bugs or request new features, send email git.teropar@gmail.com
