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

#TODO: Implement command line functionality

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
    """Translate a set instruction to a 6-byte code for the hotplate."""

    trans_cmd = [command[0], 'FE']
    if(command[2] == 't'): trans_cmd[1] += 'B2'
    else: trans_cmd[1] += 'B1'
    trans_cmd[1] += str(hex(int(command[3])))[2:].rjust(4,'0')
    trans_cmd[1] += '00'
    checksum = calc_checksum(trans_cmd[1])
    trans_cmd[1] += checksum
    return(trans_cmd)

def monitor(port, plotwriter, start_time):
    """Receive the actual speed and temperature from the hotplate, show it on
    screen and write it to the csv file."""

    send_command(port, 'FEA2000000A2')
    reply = port.read(11)
    set_temp = int.from_bytes(reply[6:8], byteorder='big')
    set_speed = int.from_bytes(reply[2:4], byteorder='big')
    meas_temp = int.from_bytes(reply[8:10], byteorder='big')
    meas_speed = int.from_bytes(reply[4:6], byteorder='big')
    cur_time = time.time() - start_time
    print('Time: ' + str(cur_time)[:6]
        + '; Set temp: ' + str(set_temp)[:-1] + '.' + str(set_temp)[-1]
        + '; Act temp: ' + str(meas_temp)[:-1] + '.' + str(meas_temp)[-1]
        + '; Set speed: ' + str(set_speed)
        + '; Act speed: ' + str(meas_speed)
        + '\r', end='', flush=True)

    send_command(port, 'FEA1000000A1')
    reply = port.read(11)
    heating_on = reply[4]
    plotwriter.writerow([cur_time, set_temp, meas_temp, set_speed, meas_speed, heating_on])

def check_heating_on(port, trans_cmd):
    send_command(port, 'FEA1000000A1')
    reply = port.read(11)
    if reply[4] == 1:
        send_command(port, trans_cmd[1])
        port.read(6)

def exec_recipe(port, recipe, log):
    """Execute a recipe file."""

    #Read commands in recipe
    with open(recipe) as recipe_file:
        command_list = [line.rstrip().split(' ') for line in recipe_file]

    #Send commands at specified times, monitor while not sending
    with open('plotfile.csv', 'w+', newline='') as plotfile:
        plotwriter = csv.writer(plotfile, delimiter='\t', dialect='excel')
        start_time = time.time()
        for command in command_list:
            if command[1] == 'set':
                command_start_time = time.time()
                trans_cmd = trans_set(command)
                send_command(port, trans_cmd[1])
                port.read(6) #Wait for confirmation, discard
                check_heating_on(port, trans_cmd)
                while(time.time()-command_start_time < int(command[0])):
                    monitor(port, plotwriter, start_time)


            if command[1] == 'ramp':
                send_command(port, 'FEA2000000A2')
                reply = port.read(11)
                set_temp = int.from_bytes(reply[6:8], byteorder='big')
                set_speed = int.from_bytes(reply[2:4], byteorder='big')

                num_of_steps = int(int(command[0])/step_size)
                if command[2] == 't':
                    incr_per_step = (int(command[3])-set_temp)/num_of_steps
                    new_value = set_temp + incr_per_step
                else:
                    incr_per_step = (int(command[3])-set_speed)/num_of_steps
                    new_value = set_speed + incr_per_step

                for step in range(num_of_steps):
                    step_start = time.time()
                    new_cmd = [command[0], 'set', 't', str(int(new_value))]
                    trans_cmd = trans_set(new_cmd)
                    send_command(port, trans_cmd[1])
                    port.read(6)
                    new_value += incr_per_step
                    check_heating_on(port, trans_cmd)
                    while(time.time()-step_start < step_size):
                        monitor(port, plotwriter, start_time)


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
        print('Connected')
        log.write('Initialization finished\n')
        port.reset_input_buffer()
        port.reset_output_buffer()
        time.sleep(0.1)

def main():
    with open('controller.log', 'w+') as log:
        log.write('Initialization\n')
        with serial.Serial(portname, timeout=1) as port:
            log.write('Port opened on port ' + portname + '\n')
            init_plate(port, log) #Send initialization commands
            exec_recipe(port, recipe, log) #Execute a recipe
            print('\nRecipe finished', flush=True)

if __name__ == "__main__":
    main()
