"""
 hotplate_sim.py
 Written by Ewout van der Veer.
 Simulates the serial port behavior of a DragonLab hotplate stirrer.
 First sends 16 6-byte initialization packets, which contain the model name of
 the hotplate, then periodically sends dummy data for the hotplate temperature
 and stirring speed.
"""

import serial
import time

portname = "COM3"
send_meas_data_time = 1

def main():
    with serial.Serial(portname, timeout=10) as port:
        #Send initialization commands
        with open('init_lines.txt') as responsefile:

            #First 16 lines send the model name of the hot plate to the software
            for line in responsefile.readlines():
                port.read(6)
                #Strip newline char, convert to bytes and send
                port.write(bytes.fromhex(line.rstrip()))
            print('Initialization finished')

        while(True):
            software_command = port.read(6)

            if(software_command != b''):
                if software_command[1] == 0xB1:
                    port.write(bytes.fromhex('FDB1000000B1'))
                    print(software_command)
                else:
                    port.write(bytes.fromhex('FDB2000000B2'))
                    print(software_command)


if __name__ == "__main__":
    main()
