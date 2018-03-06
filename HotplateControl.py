import csv
import serial
import time
import os

def make_cmd_file(cmds, filename):
    with open('./cmd_files/' + filename, 'w+') as cmdfile:
        cmdfile.write(cmds.strip('\n'))

def delete_cmd_file(filename):
    os.remove('./cmd_files/' + filename)

def list_cmd_files():
    return(os.listdir('./cmd_files'))

def plot_hp_file(temperature=True, speed=True):
    pass

class Hotplate():

    def __init__(self, port_name, step_size, plotfile, logfile):
        self.port_name = port_name
        self.step_size = step_size
        self.plotfile = './plotfiles/' + plotfile
        self.logfile = logfile

    def __enter__(self):
        try:
            self.port = serial.Serial(self.port_name, timeout=1)
        except:
            raise FileNotFoundError('Hotplate not connected or switched on')
        self.log = open(self.logfile, 'w+')
        self.initialize()
        return(self)

    def __exit__(self, exc_type, exc_value, traceback):
        self.port.close()
        self.log.close()
        print('\nConnection closed')

    def initialize(self):
        """Initialize the hotplate using a predefined set of 16 6-byte packets, log
        the response, which contains the hotplate model."""

        self.log.write('Initialization\n')
        with open('init_lines_controller.txt') as initfile:
            self.log.write('Response received from hotplate:\n')
            print('Connecting', end='', flush=True)
            #First 16 lines send the model name of the hot plate to the software
            for i, line in enumerate(initfile):
                self.send_command(line)
                res = self.port.read(6) #Wait for confirmation
                self.log.write(str(i) + ' ' + str(res) + '\n')
                print('.', end='', flush=True)
                #Hotplate may crash if packets are sent too quickly (~50 ms)
            print('Connected')
            self.log.write('Initialization finished\n')
            self.port.reset_input_buffer()
            self.port.reset_output_buffer()
            time.sleep(0.1)

    def send_command(self, line):
        """Send the command to the hotplate and wait 50ms"""

        for byte in range(0, len(line.rstrip()), 2):
            self.port.write(bytes.fromhex(line[byte]+line[byte+1]))
            time.sleep(0.05)

    def check_heating_on(self, trans_cmd):
        """Check that the heating is on, if not then turn it on"""
        self.send_command('FEA1000000A1')
        reply = self.port.read(11)
        if reply[4] == 1:
            self.send_command(trans_cmd[1])
            self.port.read(6)

    def exec_cmd_file(self, cmd_file):
        """Execute a commands file."""

        #Read commands in commands file
        with open('./cmd_files/' + cmd_file) as cmd_file:
            command_list = [line.rstrip().split(' ') for line in cmd_file]

        #Send commands at specified times, monitor while not sending
        with open(self.plotfile, 'w+', newline='') as plotfile:
            plotwriter = csv.writer(plotfile, delimiter='\t', quoting=csv.QUOTE_NONE)
            start_time = time.time()
            for command in command_list:

                if command[1] == 'set':
                    command_start_time = time.time()
                    trans_cmd = Hotplate.translate_cmd(command)
                    self.send_command(trans_cmd[1])
                    self.port.read(6) #Wait for confirmation, discard
                    self.check_heating_on(trans_cmd)
                    while(time.time()-command_start_time < int(command[0])):
                        self.get_hp_data(plotwriter, start_time)


                if command[1] == 'ramp':
                    self.send_command('FEA2000000A2')
                    reply = self.port.read(11)
                    set_temp = int.from_bytes(reply[6:8], byteorder='big')
                    set_speed = int.from_bytes(reply[2:4], byteorder='big')

                    num_of_steps = int(int(command[0])/self.step_size)
                    if command[2] == 't':
                        incr_per_step = (int(command[3])-set_temp)/num_of_steps
                        new_value = set_temp + incr_per_step
                    else:
                        incr_per_step = (int(command[3])-set_speed)/num_of_steps
                        new_value = set_speed + incr_per_step

                    for step in range(num_of_steps):
                        step_start = time.time()
                        new_cmd = [command[0], 'set', 't', str(int(new_value))]
                        trans_cmd = Hotplate.translate_cmd(new_cmd)
                        self.send_command(trans_cmd[1])
                        self.port.read(6)
                        new_value += incr_per_step
                        self.check_heating_on(trans_cmd)
                        while(time.time()-step_start < self.step_size):
                            self.get_hp_data(plotwriter, start_time)
        print('\nProcedure finished')

    def get_hp_data(self, plotwriter, start_time):
        """Receive the actual speed and temperature from the hotplate, show it
        on screen and write it to the csv file."""

        self.send_command('FEA2000000A2')
        reply = self.port.read(11)
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

        self.send_command('FEA1000000A1')
        reply = self.port.read(11)
        heating_on = reply[4]
        plotwriter.writerow([cur_time, set_temp, meas_temp, set_speed,
                            meas_speed, heating_on])

    def monitor(self, max_time=None):
        with open(self.plotfile, 'w+', newline='') as plotfile:
            plotwriter = csv.writer(plotfile, delimiter='\t', quoting=csv.QUOTE_NONE)
            start_time = time.time()
            try:
                while(True):
                    self.get_hp_data(plotwriter, start_time)
                    time.sleep(0.5)
                    if max_time and time.time()-start_time > max_time:
                        break
            except KeyboardInterrupt:
                pass


    @staticmethod
    def translate_cmd(command):
        """Translate a set instruction to a 6-byte code for the hotplate."""

        trans_cmd = [command[0], 'FE']
        if(command[2] == 't'): trans_cmd[1] += 'B2'
        else: trans_cmd[1] += 'B1'
        trans_cmd[1] += str(hex(int(command[3])))[2:].rjust(4,'0')
        trans_cmd[1] += '00'
        checksum = Hotplate.calc_checksum(trans_cmd[1])
        trans_cmd[1] += checksum
        return(trans_cmd)

    @staticmethod
    def calc_checksum(command):
        """Find the checksum, which is the least significant byte of the sum of
        previous bytes"""
        sum_of_bytes = 0
        for byte in range(2, len(command), 2):
            sum_of_bytes += int(command[byte]+command[byte+1], 16)
        lsb = str(hex(sum_of_bytes))[-2:] # Find the least significant byte
        return(lsb)
