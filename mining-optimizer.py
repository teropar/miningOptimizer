#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Nov  6 15:49:50 2021

@author: tero
"""
# core/mem 70/1000   26.59
# core/mem 80/1000   26.74
# core/mem 90/1100   26.72

#sudo nvidia-smi -i 0 --lock-gpu-clocks=1000,1000    #absolute clock
#sudo nvidia-smi -i 0 -rgc     #reset

import requests
import subprocess
import time

### SETTINGS
API_address = "http://127.0.0.1:4067/summary" #address of the miner API
gpu = 0 #which GPU we are testing 0,1,2,3, or .. (only one)
power_limits = [160,160] #GPU power limits in testing, [low,high]. Testing each power setting from low to high with defined steps. NOTE, if using absolute core clock this might be better to use just as upper limits (low=high)
power_step = 10 #
gpu_core_limits = [1400, 1500] #core clock [low,hig] offset limits. If value is 500 or less, it is considered as offset, otherwise it is absolute value
core_step = 25 #core offset to increase in each step
gpu_mem_limits = [2000, 2400] #memory clock offset limits
mem_step = 100 #memory clock to increase in each step
step_time = 120 #how many seconds we run each setting
result_divider = 1000000 #1000 to produce KH/s or 1000000 for MH/s
save_file = True #write results to a file: results.log
###

def get_hashrate(gpu, API_addr):
    try:
        #get full summary from miner
        response = requests.get(API_addr)
    except:
        print("Connection to miner API failed")
        return -1,-1
    if(response.status_code == 200):
        #if successfull, make the response as a dictionary
        response_dict = response.json()
        #extract gpu stats
        gpu_stats = response_dict["gpus"]
        try:
            #extract hashrate
            hashrate = gpu_stats[gpu]["hashrate"]
            miner_power = gpu_stats[gpu]["power_avr"]
        except:
            print("Reading hashrate of gpu" + str(gpu) + " failed")
            return -1,-1
        return hashrate,miner_power
    else:
        return -1,-1
    
#use capture_output=True in subprocess.run() to remove output 
def set_gpu_power(gpu,power,no_output):
    command = "nvidia-smi -i " + str(gpu) + " -pl " + str(power)
    return subprocess.run([command], shell=True,capture_output=no_output)

def set_core_clk(gpu,clock,no_output):
    if(clock <= 500): #values of 500 or below are considered as offset
        command = "nvidia-settings -a \"[gpu:" + str(gpu) + "]/GPUGraphicsClockOffset[4]=" + str(clock) + "\""
        return subprocess.run([command], shell=True,capture_output=no_output)
    else:
        command = "nvidia-smi -i " + str(gpu) + " --lock-gpu-clocks=" + str(clock) + "," + str(clock)
        return subprocess.run([command], shell=True,capture_output=no_output)
    
def set_mem_clk(gpu,clock,no_output):
    command = "nvidia-settings -a \"[gpu:" + str(gpu) + "]/GPUMemoryTransferRateOffset[4]=" + str(clock) + "\""
    return subprocess.run([command], shell=True,capture_output=no_output)

#clear the results file if already exists    
with open("./results_gpu" + str(gpu) + ".log", 'w') as the_file:
    the_file.write("Hashrate\treported W\tcore\tmem\tefficiency (hashrate/W)\n")

results_log = [] #store all results in this, currently no used
#send first settings to GPU and test that Nvidia commands will 
#return 0, to make sure we can alter the settings
print("Trying to send the first settings to GPU. Response from nvidia drivers enabled here to see possible errors")
output1 = set_core_clk(gpu,gpu_core_limits[0],False)
#set the lowest memory clock
output2 = set_mem_clk(gpu,gpu_mem_limits[0],False)
#power limit test
output3 = set_gpu_power(gpu,power_limits[0], False)

if(output1.returncode == 0 and output2.returncode == 0):
    print("Initial settings successfull, testing will start...")
    test_time = int((int((gpu_core_limits[1] - gpu_core_limits[0])/core_step + 1) * int((gpu_mem_limits[1] - gpu_mem_limits[0])/mem_step + 1) * int((power_limits[1] - power_limits[0])/power_step + 1) * step_time) / 60)
    print("Full test time is " + str(test_time) + "min")
    best_rate = 0
    best_efficiency = 0
    
    for power in  range(power_limits[0], power_limits[1]+power_step,power_step):
        #set the next power for testing
        set_gpu_power(gpu,power,True)
        for core in range(gpu_core_limits[0],gpu_core_limits[1]+core_step,core_step):
            #set core clock
            set_core_clk(gpu,core,True)
            for mem in range(gpu_mem_limits[0],gpu_mem_limits[1]+mem_step,mem_step):
                #set memory clock
                set_mem_clk(gpu,mem,True)
                print("Testing with power limit: " + str(power) + ", core: " + str(core) + ", mem: " + str(mem) + ". Test time: " + str(round(step_time,1)) + "s")
                time.sleep(step_time) #wait hashrate to stabilize
                #check the hashrate
                hashrate,miner_power = get_hashrate(gpu,API_address) #miner_power = gpu power reported by miner
        
                #convert to requested magnitude
                hashrate = round(hashrate/result_divider,2)
                efficiency = round(hashrate/miner_power,3)
                #Check if this was the best so far
                if(hashrate > best_rate):
                    best_rate = hashrate
                    best_settings = (power,core,mem, efficiency) #efficiency not really a setting, but save it here also
                if(efficiency > best_efficiency):
                    best_efficiency = efficiency
                    best_eff_settings = (power,core,mem, efficiency)
                print("Hashrate: " + str(hashrate) + ", efficiency: " + str(efficiency) + "  (best: " + str(best_rate) + ", with " + str(best_settings[0]) + "/" + str(best_settings[1]) + "/" + str(best_settings[2]) + ", eff: " + str(best_settings[3]) + ")")
                #save the results
                results_log.append((power,core,mem,hashrate))
                if(save_file):
                    with open("./results_gpu" + str(gpu) + ".log", 'a') as the_file:
                        the_file.write(str(hashrate) + "\t\t" + str(miner_power) + "\t\t" + str(core) + "\t" + str(mem) + "\t" + str(efficiency) + "\n")
                
    #use the best hashrate settings
    print("Test finished")
    #print("Best settings, power: " + str(best_settings[0]) + ", core: " + str(best_settings[1]) + ", mem: " + str(best_settings[2]) + ", hashrate: " + str(best_rate) + "   efficiency: " + str(best_settings[3]))
    print("Best hash rate settings, power: " + str(best_settings[0]) + ", core: " + str(best_settings[1]) + ", mem: " + str(best_settings[2]) + ", hashrate: " + str(best_rate) + "  efficiency: " + str(best_settings[3]))
    print("Best efficiency settings, power: " + str(best_eff_settings[0]) + ", core: " + str(best_eff_settings[1]) + ", mem: " + str(best_eff_settings[2]) + ", hashrate: " + str(best_rate) + "  efficiency: " + str(best_eff_settings[3]))
    print("Writing the best settings to GPU")
    if(save_file):
        print("Writing results to file results_gpu" + str(gpu) + ".log")
        with open("./results_gpu" + str(gpu) + ".log", 'a') as the_file:
            the_file.write("Best hash rate settings, power: " + str(best_settings[0]) + ", core: " + str(best_settings[1]) + ", mem: " + str(best_settings[2]) + ", hashrate: " + str(best_rate) + "  efficiency: " + str(best_settings[3]) + "\n")
            the_file.write("Best efficiency settings, power: " + str(best_eff_settings[0]) + ", core: " + str(best_eff_settings[1]) + ", mem: " + str(best_eff_settings[2]) + ", hashrate: " + str(best_rate) + "  efficiency: " + str(best_eff_settings[3]) + "\n")
    #set the best core      
    set_core_clk(gpu,best_settings[1],True)
    #and set the best memory clock
    set_mem_clk(gpu,best_settings[2],True)
    #best power 
    set_gpu_power(gpu,best_settings[3],True)

else:
    print("Error from Nvidia overclocking settings, exiting...")        
        