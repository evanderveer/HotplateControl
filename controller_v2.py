import HotplateControl

def main():

    with HotplateControl.Hotplate(port_name='COM8',
                                  recipe='recipes/recipe1.txt',
                                  step_size=10,
                                  plotfile='plotfile.csv',
                                  logfile='hotplate.log') as hp:
        hp.exec_recipe()

if __name__ == "__main__":
    main()
