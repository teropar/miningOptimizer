# miningOptimizer

This code iteratively tests mining hashrate on Nvidia GPUs with different
overclocking settings. GPU power limits can be set, low limit, high limit, and
the step. And similar settings are applied for GPU core clock and memory clock. 
If core clock setting is 500 or lower, it is considered as offset and higher 
values are absolute clocks. Multiple GPUs can be tested sequentally (same 
limits for all the GPUs). After test is completed, the best settings are set
on the tested GPU.

Currently support miners: t-rex, Phoenixminer, Nbminer

The code will use 'nvidia-smi' and 'nvidia-settings' which should come with 
Nvidia drivers in Linux. 

Linux ONLY!

Admin priviledges needed for:
 - Setting GPU power
 - Setting absolute core clock

No admin needed for:
 - Setting core clock offset
 - Setting memory clock offset
