#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

This Python code iteratively tests mining hashrate on Nvidia GPUs with 
different overclocking settings. Settings limits should be set: low limit, high 
limit, and a step. The settings are applied for GPU power, GPU core clock and 
GPU memory clock. If the core clock setting is 500 or lower, it is considered 
as offset, while higher values are absolute clocks. Multiple GPUs can be tested 
sequentally (same limits for all the GPUs). For each GPU, first, power limit 
and core clock is locked and memory settings are tested from low limit to high 
limit. After memory high limit is reached, the core clock is increased by the 
predefined step and memory iteration start from the low limit again etc.

After the GPU test is completed, the best settings are set on the GPU. All the 
results can be saved on a file.

Currently support these miners: t-rex, Phoenixminer, Nbminer

The code will use 'nvidia-smi' and 'nvidia-settings' which should come with 
Nvidia drivers in Linux. Linux ONLY!

# Admin priviledges needed for:
 - Setting GPU power
 - Setting absolute core clock

# No admin needed for:
 - Setting core clock offset
 - Setting memory clock offset
"""

### SETTINGS
miner = 0 # t-rex = 0, phoenixminer = 1, nbminer = 2
gpus = [0] #which Nvidia GPU id (in HW) we will be testing [0,1,2,3,...] comma separated list (square brackets)
miner_gpus = gpus #in miner the gpu id can be different, e.g if running some lower HW id Nvidia GPUs on other miner. Comma separated list (square brackets] Default: miner_gpus=gpus
power_limits = [150,160] #GPU power limits in testing, [low,high]. Testing each power setting from low to high with defined steps. NOTE, if using absolute core clocks this might be better to use just as upper limits (low=high)
power_step = 5 #power to increase in each power step
gpu_mem_limits = [2100, 2300] #memory clock offset limits
mem_step = 100 #memory clock to increase in each step
gpu_core_limits = [1300, 1525] #core clock [low,hig] offset limits. If value is 500 or less, it is considered as offset, otherwise it is absolute value
core_step = 25 #core clock to increase in each step
step_time = 60 #how many seconds we run each setting to allow hashrate convergence
save_file = True #write results to a file named: 'time_miner_powerlimits_corelimits_memlimits.log
result_divider = 1000 #divide the results for readability. 1000 = kh, 1000000 = Mh, do not divide = 1
## Miner API Settings
TREX_API = "http://127.0.0.1:4067/summary" # t-rex API address. Default http://127.0.0.1:4067/summary
PHOENIX_PORT =  3333 #Phoenixminer API port, HiveOS uses 3335? Default port 3333. IP default: 127.0.0.1
NBMINER_API = "http://0.0.0.0:22333/api/v1/status" # nbminer API address. Default http://0.0.0.0:22333/api/v1/status
###

perf_levels = 4 #how many performance levels in gpu, RTX = 4, using as default. This is checked later in this code

import socket
import json
import requests
import subprocess
import time

#query information about GPU
def query_gpu(gpu,query):
    command = "nvidia-smi -i " + str(gpu) + " --query-gpu=\"" + str(query) + "\" --format=csv,noheader,nounits"
    response = subprocess.run(command, shell=True,stdout=subprocess.PIPE,universal_newlines=True)
    if(response.returncode == 0):
        value = float(response.stdout[0:-1]) #remove the \n from the string
        return int(round(value,0))
    else:
        print("Did not receive query " + str(query) + "from nvidia-smi")
        return -1
def get_hash_pow(miner, gpu,miner_gpu,time_step):
    if(miner == 0 or miner == 2): #t-rex or nbminer
        
        if(miner == 0): #address of the t-rex miner API
            API_address = TREX_API
        elif(miner == 2): #nbmier
            API_address = NBMINER_API
        divider_pow = 0
        divider_hash = 0
        pow_sum = 0
        hash_sum = 0
        #idea is to average four power values
        #hashrate averaging default is 60s in t-rex, so no need to average,
        #but nbminer needs averaging
        for i in range(4): 
            time.sleep(time_step/4)
            pow_temp = query_gpu(gpu,"power.draw")
            if(pow_temp > 0):
                pow_sum = pow_sum + pow_temp
                divider_pow = divider_pow + 1
            #get current hashrate, t-rex has long averaging time, use only the last as return value
            try:
                #get full summary from miner
                response = requests.get(API_address)
                if(response.status_code == 200):
                    #if successfull, make the response as a dictionary
                    response_dict = response.json()
                    if(miner == 0): #t-rex 
                        ##extract hashrate, use only the last
                        hash_tmp = response_dict["gpus"][miner_gpu]["hashrate"]
                        hash_sum = hash_tmp
                        divider_hash = 1
                    elif(miner == 2): #nbminer
                        hash_tmp = response_dict["miner"]["devices"][miner_gpu]["hashrate_raw"]
                        hash_sum = hash_sum + hash_tmp
                        divider_hash = divider_hash + 1
                    print(str(round(hash_tmp/result_divider,2)) + "  " + str(pow_temp) + "W")
                    
                else:
                    print(str(pow_temp) + "W")
            except:
                print("Connection to miner API failed, check miner and port")
                print(str(pow_temp) + "W")
        
        #calculate average
        if(divider_hash > 0):
            hashrate = hash_sum / divider_hash
        else:
            hashrate = 0
        gpu_power = pow_sum/divider_pow
            
        return hashrate,gpu_power

    elif(miner==1): #phoenixminer
        ip = "127.0.0.1"
        port = PHOENIX_PORT
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (ip,port)
        try: #connect to miner
            sock.connect(server_address)
        except:
            print("Miner socket " + str(ip) + ':' + str(port) + " has no connection, check miner and port")
        divider_hash = 0
        divider_pow = 0
        pow_sum = 0
        hash_sum = 0
        for i in range(4):
            valid = True
            time.sleep(time_step/4)
            #read power
            pow_temp = query_gpu(gpu,"power.draw")
            pow_sum = pow_sum+pow_temp
            divider_pow = divider_pow+1
            #check hashrate
            request = '{\"id\":0,\"jsonrpc\":\"2.0\",\"method\":\"miner_getstat1\"}\n'
            request = request.encode()    
            try:
                sock.sendall(request)
            except:
                print('Sending data request to miner was aborted')
                valid = False
            try:
                data = sock.recv(512)
            except:
                print('Receiving data was aborted')
                valid = False
            if(valid):
                message = json.loads(data)
                hashrate_tmp = int(message["result"][3].split(";")[miner_gpu])
                hash_sum = hash_sum + hashrate_tmp
                divider_hash = divider_hash+1
                print(str(round(hashrate_tmp/result_divider,2)) + "  " + str(pow_temp) + "W")
            else:
                valid = True #try to connect again
                sock.close()
                try: #connect to miner
                    sock.connect(server_address)
                except:
                    print('Miner socket ' + str(ip) + ':' + str(port) + ' has no connection, check miner and port')
        if(divider_hash > 0):
            hashrate = hash_sum/divider_hash
        else:
            hashrate = 0
        gpu_power = pow_sum/divider_pow
        sock.close()
        return hashrate,gpu_power
        
#reset possible core clock limits to default and offset to zero
#also this checks that do we have admin priviledges, if not any other problem with the command
def init_core_clocks(gpu,perf_levels):
    #set core clock limits to defaults
    command = "nvidia-smi -i " + str(gpu) + " -rgc" #if no other error, this will return 4 if no admin
    output1 = subprocess.run(command, shell=True)
    #set core clock offset to default (0)
    command = "nvidia-settings -a \"[gpu:" + str(gpu) + "]/GPUGraphicsClockOffset[" + str(perf_levels) + "]=0\""
    output2 = subprocess.run(command, shell=True)
    return output1,output2
#check how many performance levels gpu have in nvidia-settings
def check_perf_levels(gpu):
    command = "nvidia-settings -q [gpu:" + str(gpu) + "]/GPUPerfModes"
    response = subprocess.run([command], shell=True, stdout=subprocess.PIPE,universal_newlines=True)
    if(response.returncode == 0): #command executed correctly
        if(str(response.stdout).find("perf=3")): # 4 levels
            return 4
        elif(str(response.stdout).find("perf=2") > -1): # 3 levels
            return 3
        elif(str(response.stdout).find("perf=1") > -1): # 2 levels
            return 2
        elif(str(response.stdout).find("perf=0") > -1): # 1 level only?
            return 1
    return -1 # unknown
#use capture_output=True in subprocess.run() to remove output 
def set_gpu_power(gpu,power,catch_output):
    command = "nvidia-smi -i " + str(gpu) + " -pl " + str(power)
    return subprocess.run(command, shell=True,stdout=subprocess.PIPE,universal_newlines=True)
def set_core_clk(gpu,clock,catch_output,perf_levels):
    if(clock <= 500): #values of 500 or below are considered as offset
        command = "nvidia-settings -a \"[gpu:" + str(gpu) + "]/GPUGraphicsClockOffset[" + str(perf_levels) + "]=" + str(clock) + "\""
        return subprocess.run(command, shell=True,stdout=subprocess.PIPE,universal_newlines=True)
    else:
        command = "nvidia-smi -i " + str(gpu) + " --lock-gpu-clocks=" + str(clock) + "," + str(clock)
        return subprocess.run(command, shell=True,stdout=subprocess.PIPE,universal_newlines=True)
    
def set_mem_clk(gpu,clock,catch_output,perf_levels):
    command = "nvidia-settings -a \"[gpu:" + str(gpu) + "]/GPUMemoryTransferRateOffset[" + str(perf_levels) +"]=" + str(clock) + "\""
    return subprocess.run(command, shell=True,stdout=subprocess.PIPE,universal_newlines=True)

#check that the given power limits are both higher than the real GPU minimum
reported_min_pl = query_gpu(gpus[0],"power.min_limit")
if(reported_min_pl > 0): #check that value is valid
    if(power_limits[0] < reported_min_pl):
        power_limits[0] = reported_min_pl
        print("Reported min gpu power is smaller than requested min limit, adjusting..")
    if(power_limits[1] < reported_min_pl):
        power_limits[1] = reported_min_pl
        print("Reported min gpu power is smaller than requested max limit, adjusting..")
        
#all power values to be tested
power_values = range(power_limits[0], power_limits[1]+power_step,power_step)
#all core values to be tested
core_values = range(gpu_core_limits[0],gpu_core_limits[1]+core_step,core_step)
set_core = True #core clock modifying can be disabled later
#all mem values to be tested
mem_values = range(gpu_mem_limits[0],gpu_mem_limits[1]+mem_step,mem_step)
results_log = [] #store all results in this, currently no used
#check if core clock lower limit is in offset zone and higher limit at absolute zone, 
#we have to reset the offset when changing to absolutes
if(core_values[0] <= 500 and core_values[-1] > 500):
    core_offset2absolute = True
else:
    core_offset2absolute = False
#send first settings to GPU and test that Nvidia commands will 
#return 0, to make sure we can alter the settings
print("Initializing core clock offset and absolutes, please check the output if any errors")

#check how many performance levels gpu has
levels_tmp = check_perf_levels(gpus[0])
if(levels_tmp != -1): #unknown, use default
    perf_levels = levels_tmp

#set core clocks to defaults, nvidia-smi reset the low and high limits and nvidia-settings set clock offset to zero
#nvidia-smi needs admin, if no other errors and no admin returncode is 4
c_absolute_set, c_offset_set = init_core_clocks(gpus[0],perf_levels)
# test also memory setup, set already the lowest memory clock
mem_set = set_mem_clk(gpus[0],gpu_mem_limits[0],False,perf_levels)
#check if there is returncode 4, which means no admin
if(c_absolute_set.returncode == 4):
    print("No admin priviledges, power limit and core absolute clocks can not be set")
    reported_pl = query_gpu(gpus[0],"power.limit") #get current power limit
    power_values = range(reported_pl,reported_pl+1)# use the current limit for our limits
    #check that should absolute clocks be set
    #if low limit is in the offset range <= 500 and high limit is > 500, adjust high to 500 to stay in offset range
    if(core_values[0] <= 500 and core_values[-1] > 500):
        core_values = range(gpu_core_limits[0],500+core_step,core_step)
        #if pure core absolute values were as target those can't be changed so just run the memory iterations
    elif(gpu_core_limits[0] > 500): #
        core_values = range(0,1)
        print("Only memory values are changed, testing the memory values from min to max")
        set_core = False # disable core clock modifying
    if(reported_pl > 0):
        print("Current power limit " + str(reported_pl) + "W is used")

if(c_offset_set.returncode == 0 and mem_set.returncode == 0):
    #open the file   
    if(save_file):
        #use time and date in filename. hh:mm:ss-d.m.y
        timestring = time.strftime("%H:%M:%S_%d.%m.%Y",time.localtime(time.time()))
        filename = "./results_" + str(timestring) + "_miner" + str(miner) + "_p" + str(power_values[0]) + "-" + str(power_values[-1]) + "_c" + str(core_values[0]) + "-" + str(core_values[-1]) + "_m" + str(mem_values[0]) + "-" + str(mem_values[-1]) + ".log"
        with open(filename, 'w') as the_file:
            the_file.write("Hashrate\treported W\tpower\tcore\tmem\tefficiency (hashrate/W)\n")
            
    print("\nInitial settings successfull, testing will start..."); print("Testing iteratively all the combinations:")
    if(len(gpus) == 1):
        print("GPU " + str(gpus[0]))
    else:
        print("GPUs from GPU " + str(gpus[0]) + " to GPU " + str(gpus[-1]))
    print("GPU power from " + str(power_values[0]) + "W to " + str(power_values[-1]) + "W, using step " + str(power_step))
    print("GPU core from " + str(core_values[0]) + " to " + str(core_values[-1]) + ", using step " + str(core_step))
    print("GPU memory from " + str(mem_values[0]) + " to " + str(mem_values[-1]) + ", using step " + str(mem_step))
    #test_time = int((int((gpu_core_limits[1] - gpu_core_limits[0])/core_step + 1) * int((gpu_mem_limits[1] - gpu_mem_limits[0])/mem_step + 1) * int((power_limits[1] - power_limits[0])/power_step + 1) * step_time) / 60)
    test_time = int(len(core_values) * len(mem_values) * len(power_values) * step_time / 60)
    print("Full test time is " + str(test_time) + "min")
    best_rate = -1
    best_efficiency = -1
    previous_core = 0
    for gpu, miner_gpu in zip(gpus,miner_gpus):
        if(save_file):
            with open(filename, 'a') as the_file:
                the_file.write("GPU \n" + str(gpu))

        for power in power_values:
            #set the next power for testing
            set_gpu_power(gpu,power,True)
            for core in core_values: #range(gpu_core_limits[0],gpu_core_limits[1]+core_step,core_step):
                #set core clock
                if(set_core): #change from core offsets to absolutes, offset should be reseted
                    if(core_offset2absolute and previous_core <= 500 and core > 500):
                        init_core_clocks(gpu,perf_levels)
                    previous_core = core #needed above only
                    set_core_clk(gpu,core,True,perf_levels) #set the next core clock
                for mem in mem_values: #range(gpu_mem_limits[0],gpu_mem_limits[1]+mem_step,mem_step):
                    #set next memory clock
                    set_mem_clk(gpu,mem,True,perf_levels)
                    print("Testing GPU " + str(gpu) + ", power limit: " + str(power) + ", core: " + str(core) + ", mem: " + str(mem) + ". Test time: " + str(round(step_time,1)) + "s")
            
                    hashrate,reported_power = get_hash_pow(miner,gpu,miner_gpu,step_time)       
            
                    #convert to requested magnitude
                    hashrate = round(hashrate/result_divider,2)
                    efficiency = round(hashrate/reported_power,3)
                    #Check if this was the best so far
                    if(hashrate > best_rate):
                        best_rate = hashrate
                        best_settings = (power,core,mem, efficiency) #efficiency not really a setting, but save it here also
                    if(efficiency > best_efficiency):
                        best_efficiency = efficiency
                        best_eff_rate = hashrate
                        best_eff_settings = (power,core,mem, efficiency)
                    print("Hashrate: " + str(hashrate) + ", eff.: " + str(efficiency) + "  (best: " + str(best_rate) + ", with " + str(best_settings[0]) + "/" + str(best_settings[1]) + "/" + str(best_settings[2]) + ", eff.: " + str(best_settings[3]) + ")")
                    #save the results
                    results_log.append((power,core,mem,hashrate))
                    if(save_file):
                        with open(filename, 'a') as the_file:
                            the_file.write(str(hashrate) + "\t\t" + str(reported_power) + "\t\t" + str(power) + "\t" + str(core) + "\t" + str(mem) + "\t" + str(efficiency) + "\n")
                    
        #use the best hashrate settings
        print("Test finished")
        #print("Best settings, power: " + str(best_settings[0]) + ", core: " + str(best_settings[1]) + ", mem: " + str(best_settings[2]) + ", hashrate: " + str(best_rate) + "   efficiency: " + str(best_settings[3]))
        print("Best hashrate settings, power: " + str(best_settings[0]) + ", core: " + str(best_settings[1]) + ", mem: " + str(best_settings[2]) + ", hashrate: " + str(best_rate) + "  efficiency: " + str(best_settings[3]))
        print("Best efficiency settings, power: " + str(best_eff_settings[0]) + ", core: " + str(best_eff_settings[1]) + ", mem: " + str(best_eff_settings[2]) + ", hashrate: " + str(best_eff_rate) + "  efficiency: " + str(best_eff_settings[3]))
        print("Writing the best hashrate settings to GPU")
        if(save_file):
            print("Writing results to file " + filename)
            with open(filename, 'a') as the_file:
                the_file.write("Best hash rate settings, power: " + str(best_settings[0]) + ", core: " + str(best_settings[1]) + ", mem: " + str(best_settings[2]) + ", hashrate: " + str(best_rate) + "  efficiency: " + str(best_settings[3]) + "\n")
                the_file.write("Best efficiency settings, power: " + str(best_eff_settings[0]) + ", core: " + str(best_eff_settings[1]) + ", mem: " + str(best_eff_settings[2]) + ", hashrate: " + str(best_eff_rate) + "  efficiency: " + str(best_eff_settings[3]) + "\n")
        #set the best core      
        set_core_clk(gpu,best_settings[1],True,perf_levels)
        #and set the best memory clock
        set_mem_clk(gpu,best_settings[2],True,perf_levels)
        #best power 
        set_gpu_power(gpu,best_settings[3],True)

else:
    print("Error from Nvidia overclocking settings, exiting...")       
