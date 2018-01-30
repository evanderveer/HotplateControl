"""
 controller.py
 Written by Ewout van der Veer.
 Controls and monitors the stirring speed and temperature of a DragonLab
 hotplate stirrer.
"""
import csv
import serial
import time

portname = 'COM8'
recipe = 'recipes/recipe1.txt'
step_size = 10

def send_command(port, line):
    """Send the command to the hotplate and wait 50ms"""

    for byte in range(0, len(line.rstrip()), 2):
        port.write(bytes.fromhex(line[byte]+line[byte+1]))
        time.sleep(0.05)

def calc_checksum(command):
    """Find the checksum, which is the least significant byte of the sum of
    previous bytes"""

    hex_list = [int(command[byte]+command[byte+1], 16) for byte in range(2, len(command), 2)]
    lsb = str(hex(sum(hex_list)))[-2:] # Find the least significant byte
    return(lsb)

def trans_set(command):
    trans_cmd = [command[0], 'FE']

    if(command[2] == 't'): trans_cmd[1] += 'B2'
    else: trans_cmd[1] += 'B1'

    trans_cmd[1] += str(hex(int(command[3])))[2:].rjust(4,'0')
    trans_cmd[1] += '00'
    checksum = calc_checksum(trans_cmd[1])
    trans_cmd[1] += checksum

    return(trans_cmd)

def monitor(port, plotwriter):
    pass

def exec_recipe(port, recipe, log):
    """Execute a recipe file."""

    #Read commands in recipe
    with open(recipe) as recipe_file:
        command_list = [line.rstrip().split(' ') for line in recipe_file]

    #Send commands at specified times
    with open('plotfile.csv') as plotfile:
        plotwriter = csv.writer(plotfile, delimiter=',', dialect='excel')
        start_time = time.time()
        for command in command_list:
            if command[1] == 'set':
                command_start_time = time.time()
                while(time.time()-command_start_time < int(command[0])):
                    monitor(port, plotwriter)
                trans_cmd = trans_set(command)
                send_command(port, trans_cmd[1])
                port.read(6) #Wait for confirmation, discard

            if command[1] == 'ramp':
                send_command(port, 'FEA2000000A2')
                reply = port.read(11)
                set_temp = reply[7:8]
                set_speed = reply[3:4]

                num_of_steps = command[0]/step_size
                if command[2] == 't':
                    incr_per_step = (command[3]-set_temp)/num_of_steps
                    new_value = set_temp + incr_per_step
                else:
                    incr_per_step = (command[3]-set_speed)/num_of_steps
                    new_value = set_speed + incr_per_step

                for step in range(num_of_steps):
                    step_start = time.time()
                    new_cmd = command[0] + ' set ' + command[2] + ' ' + str(new_value)
                    trans_cmd = trans_set(new_cmd)
                    send_command(port, trans_cmd[1])
                    new_value += incr_per_step
                    while(time.time()-step_start < step_size):
                        monitor(port, plotwriter)


def init_plate(port, log):
    """Initialize the hotplate using a predefined set of 16 6-byte packets, log
    the response, which contains the hotplate model."""

    with open('init_lines_controller.txt') as initfile:
        log.write('Response received from hotplate:\n')
        print('Connecting', end='', flush=True)
        #First 16 lines send the model name of the hot plate to the software
        for i, line in enumerate(initfile):
            send_command(port, line)
            res = port.read(6) #Wait for confirmation
            log.write(str(i) + ' ' + str(res) + '\n')
            print('.', end='', flush=True)
            #Hotplate may crash if packets are sent too quickly (~50 ms)
            time.sleep(0.05)
        print('Connected')
        log.write('Initialization finished\n')
        time.sleep(0.1)

def main():
    with open('controller.log', 'w+') as log:
        log.write('Initialization\n')
        with serial.Serial(portname, timeout=1) as port:
            log.write('Port opened on port ' + portname + '\n')
            init_plate(port, log) #Send initialization commands
            exec_recipe(port, recipe, log) #Execute a recipe
            print('Recipe finished')

if __name__ == "__main__":
    main()
