from HotplateControl import Hotplate

def main():

    with Hotplate(port_name='COM8', step_size=10,
                  plotfile='plotfile.csv', logfile='hotplate.log') as hp:
        hp.exec_cmd_file('cmd_files/test.txt')

if __name__ == "__main__":
    main()
