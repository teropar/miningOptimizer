#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Nov  6 15:49:50 2021
@author: tero
"""

# Admin priviledges needed for:
# - Setting GPU power
# - Setting absolute core clock

# No admin needed for:
# - Setting core clock offset
# - Setting memory clock offset

import socket
import json

#sudo nvidia-smi -i 0 --lock-gpu-clocks=1000,1000    #absolute clock
#sudo nvidia-smi -i 0 -rgc     #reset clocks
import requests
import subprocess
import time
### SETTINGS
miner = 0 # t-rex = 0, phoenixminer = 1
gpu = 0 #which GPU we are testing 0,1,2,3, or .. (only one)
power_limits = [130,140] #GPU power limits in testing, [low,high]. Testing each power setting from low to high with defined steps. NOTE, if using absolute core clock this might be better to use just as upper limits (low=high)
power_step = 10 #
gpu_core_limits = [1300, 1400] #core clock [low,hig] offset limits. If value is 500 or less, it is considered as offset, otherwise it is absolute value
core_step = 25 #core offset to increase in each step
gpu_mem_limits = [2100, 2400] #memory clock offset limits
mem_step = 100 #memory clock to increase in each step
step_time = 60 #how many seconds we run each setting
result_divider = 1000000 #1000 to produce KH/s or 1000000 for MH/s
save_file = True #write results to a file: results.log
###

if(miner==0): #in t-rex units are h/s
    result_divider = 1000000
elif(miner==1):#in phoenixminer units are kh/s
    result_divider = 1000
    
#query information about GPU
def query_gpu(gpu,query):
    command = "nvidia-smi -i " + str(gpu) + " --query-gpu=\"" + str(query) + "\" --format=csv,noheader,nounits"
    response = subprocess.run(command, shell=True,capture_output=True,text=True)
    if(response.returncode == 0):
        value = float(response.stdout[0:-1]) #remove the \n from the string
        return int(round(value,0))
    else:
        print("Did not receive query " + str(query) + "from nvidia-smi")
        return -1
def get_hash_pow(miner, gpu,time_step):
    if(miner == 0):
        #address of the t-rex miner API
        API_address = "http://127.0.0.1:4067/summary" 
        divider = 0
        pow_sum = 0
        #idea is to average four power values
        #hashrate averaging default is 60s in t-rex, so no need to average
        for i in range(4): 
            time.sleep(time_step/4)
            pow_temp = query_gpu(gpu,"power.draw")
            if(pow_temp > 0):
                pow_sum = pow_sum + pow_temp
                divider = divider+1
            #get current hashrate, t-rex has long averaging time, use only the lastas return value
            try:
                #get full summary from miner
                response = requests.get(API_address)
            except:
                print("Connection to miner API failed")
            if(response.status_code == 200):
                #if successfull, make the response as a dictionary
                response_dict = response.json()
                #extract gpu stats
                gpu_stats = response_dict["gpus"]
                #extract hashrate
                hashrate = gpu_stats[gpu]["hashrate"]
                print(str(round(hashrate/result_divider,2)) + "  " + str(pow_temp) + "W")
            else:
                hashrate = -1
                print(str(pow_temp) + "W")
                
        gpu_power = pow_sum/divider
            
        return hashrate,gpu_power

    elif(miner==1): #phoenixminer
        ip = "127.0.0.1"
        port = 3333
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (ip,port)
        try: #connect to miner
            sock.connect(server_address)
        except:
            print('Miner socket ' + str(ip) + ':' + str(port) + ' is closed')
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
                print('Sending data was aborted')
                valid = False
            try:
                data = sock.recv(512)
            except:
                print('Recieveing data was aborted')
                valid = False
            message = json.loads(data)
            hashrate_tmp = int(message["result"][3].split(";")[gpu])
            if(valid):
                hash_sum = hash_sum + hashrate_tmp
                divider_hash = divider_hash+1
                print(str(hashrate_tmp/result_divider) + "  " + str(pow_temp) + "W")
            else:
                valid = True #try to connect again
                try: #connect to miner
                    sock.connect(server_address)
                except:
                    print('Miner socket ' + str(ip) + ':' + str(port) + ' is closed')
        hashrate = hash_sum/divider_hash
        gpu_power = pow_sum/divider_pow
        sock.close()
        return hashrate,gpu_power
        
#use capture_output=True in subprocess.run() to remove output 
def set_gpu_power(gpu,power,catch_output):
    command = "nvidia-smi -i " + str(gpu) + " -pl " + str(power)
    return subprocess.run(command, shell=True,capture_output=catch_output)
def set_core_clk(gpu,clock,catch_output):
    if(clock <= 500): #values of 500 or below are considered as offset
        command = "nvidia-settings -a \"[gpu:" + str(gpu) + "]/GPUGraphicsClockOffset[4]=" + str(clock) + "\""
        return subprocess.run(command, shell=True,capture_output=catch_output)
    else:
        command = "nvidia-smi -i " + str(gpu) + " --lock-gpu-clocks=" + str(clock) + "," + str(clock)
        return subprocess.run(command, shell=True,capture_output=catch_output)
    
def set_mem_clk(gpu,clock,catch_output):
    command = "nvidia-settings -a \"[gpu:" + str(gpu) + "]/GPUMemoryTransferRateOffset[4]=" + str(clock) + "\""
    return subprocess.run(command, shell=True,capture_output=catch_output)

#check min power limit of gpu
reported_min_pl = query_gpu(gpu,"power.min_limit")
if(reported_min_pl > 0): #chekc that value is valid
    if(power_limits[0] < reported_min_pl):
        power_limits[0] = reported_min_pl
        print("Reported min gpu power is smaller than requested limits, adjusting..")
    if(power_limits[1] < reported_min_pl):
        power_limits[1] = reported_min_pl
        print("Reported min gpu power is smaller than requested limits, adjusting..")
        
#all power values to be tested
power_values = range(power_limits[0], power_limits[1]+power_step,power_step)
#all core values to be tested
core_values = range(gpu_core_limits[0],gpu_core_limits[1]+core_step,core_step)
#all mem values to be tested
mem_values = range(gpu_mem_limits[0],gpu_mem_limits[1]+mem_step,mem_step)
results_log = [] #store all results in this, currently no used
#open the file   
if(save_file):
    #use time and date in filename. hh:mm:ss-d.m.y
    timestring = time.strftime("%H:%M:%S_%d.%m.%Y",time.localtime(time.time()))
    filename = "./results_" + str(timestring) + "_miner" + str(miner) + "_gpu" + str(gpu) + "_p" + str(power_values[0]) + "-" + str(power_values[-1]) + "_c" + str(core_values[0]) + "-" + str(core_values[-1]) + "_m" + str(mem_values[0]) + "-" + str(mem_values[-1]) + ".log"
    with open(filename, 'w') as the_file:
        the_file.write("Hashrate\treported W\tcore\tmem\tefficiency (hashrate/W)\n")
    
#send first settings to GPU and test that Nvidia commands will 
#return 0, to make sure we can alter the settings
print("Trying to send the first settings to GPU. Response from nvidia drivers enabled here to see possible errors")
#power limit test
output1 = set_gpu_power(gpu,power_limits[0], False)
#check if there is returncode 4, which means no admin
if(output1.returncode == 4):
    print("No admin priviledges, power limit and core absolute clocks can not be set")
    reported_pl = query_gpu(gpu,"power.limit") #get current power limit
    if(reported_pl > 0):
        print("Current power limit " + str(reported_pl) + "W is used")
    power_values = range(reported_pl,reported_pl+1)# use the current limit for our limits
    #check that should absolute clocks be set
    #if low limit is in the offset range <= 500 and high limit is > 500, adjust high to 500 to stay in offset range
    if(gpu_core_limits[0] <= 500 and gpu_core_limits[1] > 500):
        core_values = range(gpu_core_limits[0],500+core_step,core_step)
        #if pure core absolute values were as target those can't be changed so just run the memory iterations
    elif(gpu_core_limits[0] > 500): #
        core_values = range(0,1)
        print("Only memory values are changed, testing the memory values from min to max")
output2 = set_core_clk(gpu,gpu_core_limits[0],False)
#set the lowest memory clock
output3 = set_mem_clk(gpu,gpu_mem_limits[0],False)

if(output2.returncode == 0 and output3.returncode == 0):
    print("\nInitial settings successfull, testing will start..."); print("Testing iteratively all the combinations:")
    print("GPU power from " + str(power_values[0]) + "W to " + str(power_values[-1]) + "W")
    print("GPU core from " + str(core_values[0]) + " to " + str(core_values[-1]))
    print("GPU memory from " + str(mem_values[0]) + " to " + str(mem_values[-1]))
    test_time = int((int((gpu_core_limits[1] - gpu_core_limits[0])/core_step + 1) * int((gpu_mem_limits[1] - gpu_mem_limits[0])/mem_step + 1) * int((power_limits[1] - power_limits[0])/power_step + 1) * step_time) / 60)
    print("Full test time is " + str(test_time) + "min")
    best_rate = 0
    best_efficiency = 0
    
    for power in power_values:
        #set the next power for testing
        set_gpu_power(gpu,power,True)
        for core in range(gpu_core_limits[0],gpu_core_limits[1]+core_step,core_step):
            #set core clock
            set_core_clk(gpu,core,True)
            for mem in range(gpu_mem_limits[0],gpu_mem_limits[1]+mem_step,mem_step):
                #set memory clock
                set_mem_clk(gpu,mem,True)
                print("Testing with power limit: " + str(power) + ", core: " + str(core) + ", mem: " + str(mem) + ". Test time: " + str(round(step_time,1)) + "s")
                #time.sleep(step_time) #wait hashrate to stabilize
                #check the hashrate
                #hashrate = get_hashrate(miner,gpu) #miner_power = gpu power reported by miner
                #miner_power=power #update here the true power read 
                #nvidia-smi --query-gpu="power.draw" --format=csv,noheader,nounits  #read power
        
                hashrate,reported_power = get_hash_pow(miner,gpu,step_time)
        
        
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
                        the_file.write(str(hashrate) + "\t\t" + str(reported_power) + "\t\t" + str(core) + "\t" + str(mem) + "\t" + str(efficiency) + "\n")
                
    #use the best hashrate settings
    print("Test finished")
    #print("Best settings, power: " + str(best_settings[0]) + ", core: " + str(best_settings[1]) + ", mem: " + str(best_settings[2]) + ", hashrate: " + str(best_rate) + "   efficiency: " + str(best_settings[3]))
    print("Best hashrate settings, power: " + str(best_settings[0]) + ", core: " + str(best_settings[1]) + ", mem: " + str(best_settings[2]) + ", hashrate: " + str(best_rate) + "  efficiency: " + str(best_settings[3]))
    print("Best efficiency settings, power: " + str(best_eff_settings[0]) + ", core: " + str(best_eff_settings[1]) + ", mem: " + str(best_eff_settings[2]) + ", hashrate: " + str(best_rate) + "  efficiency: " + str(best_eff_settings[3]))
    print("Writing the best hashrate settings to GPU")
    if(save_file):
        print("Writing results to file " + filename)
        with open(filename, 'a') as the_file:
            the_file.write("Best hash rate settings, power: " + str(best_settings[0]) + ", core: " + str(best_settings[1]) + ", mem: " + str(best_settings[2]) + ", hashrate: " + str(best_rate) + "  efficiency: " + str(best_settings[3]) + "\n")
            the_file.write("Best efficiency settings, power: " + str(best_eff_settings[0]) + ", core: " + str(best_eff_settings[1]) + ", mem: " + str(best_eff_settings[2]) + ", hashrate: " + str(best_eff_rate) + "  efficiency: " + str(best_eff_settings[3]) + "\n")
    #set the best core      
    set_core_clk(gpu,best_settings[1],True)
    #and set the best memory clock
    set_mem_clk(gpu,best_settings[2],True)
    #best power 
    set_gpu_power(gpu,best_settings[3],True)

else:
    print("Error from Nvidia overclocking settings, exiting...")       
