# miningOptimizer

This Python code iteratively tests mining hashrate on Nvidia GPUs with different overclocking settings. Settings limits should be set: low limit, high limit, and a step. The settings are applied for GPU power, GPU core clock and GPU memory clock. If the core clock setting is 500 or lower, it is considered as offset, while higher values are absolute clocks. Multiple GPUs can be tested sequentally (same limits for all the GPUs). For each GPU, first, power limit and core clock is locked and memory settings are tested from low limit to high limit. After memory high limit is reached, the core clock is increased by the predefined step and memory iteration start from the low limit again etc.

After the GPU test is completed, the best settings are set on the GPU. All the results can be saved on a file.

Currently support these miners: t-rex, Phoenixminer, Nbminer

The code will use 'nvidia-smi' and 'nvidia-settings' which should come with Nvidia drivers in Linux. Linux ONLY!

Admin priviledges needed for:
 - Setting GPU power
 - Setting absolute core clock

No admin needed for:
 - Setting core clock offset
 - Setting memory clock offset

Tested with:
- Ubuntu 20.04, HiveOS 5.0.21-201105
- Python 3.6, Python 3.8
- RTX 3060Ti

Python modules:
socket, json, requests, subprocess, time
