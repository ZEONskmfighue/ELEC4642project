# ELEC4642project
# This project is created by Qiong, Dong, Yang and Zeng, through this project you can achieve the function of switch traffic capture and corresponding front end interfaces. The code files are used for reference only. We are happy our codes can help you or enlighten you, even if these codes are not good.
# Where to start: first of all you need a Linux environment, installed with ryu. You can check what module is need by openning the files. 

# We developed two sets of ryu controller and topology: 1, topo_star.py and ryu_control.py; 2, topo.py and ryucontroller.py. Both of them can work, but you need right start command, and each set needs three terminals to start. We suggest you use pycharm to run these codes which is what we use to develop.

# When you are starting the first set of files, first, you should key in "ryu-manager ryu_control.py" to start the ryu controller first in the first terminal window. And then, you should type in "sudo python3 topo_star.py" in the second terminal to start the topology, and you will open a mininet CLI that you can talk to. You can type in commands like "net" or "pingall" in the mininet CLI to check if the topo and the ryu is working correctly.

# When you are starting the second set of files, first you should type in "ryu-manager ryucontroller.py" to start the ryu controller in the first terminal. Then you should type in "sudo mn --custom topo.py --topo simpletopo --controller=remote,ip=127.0.0.1,port=6633" to start the topology in the second terminal. 

# Warning: you should check the file path of yours and add them correctly into the command.

# Now, y
