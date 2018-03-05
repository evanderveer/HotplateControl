from HotplateControl import Hotplate

def main():

    with Hotplate(port_name='COM8', step_size=10,
                  plotfile='plotfile.csv', logfile='hotplate.log') as hp:
        hp.exec_recipe('recipes/recipe1.txt')

if __name__ == "__main__":
    main()
