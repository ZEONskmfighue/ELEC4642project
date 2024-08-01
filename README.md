# ELEC4642project
This project is created by Qiong, Dong, Yang and Zeng, through this project you can achieve the function of switch traffic capture and corresponding front end interfaces. The code files are used for reference only. We are happy our codes can help you or enlighten you, even if these codes are not good.
Where to start: first of all you need a Linux environment, installed with ryu. You can check what module is need by openning the files. 

We developed two sets of ryu controller and topology: 1, topo_star.py and ryu_control.py; 2, topo.py and ryucontroller.py. Both of them can work, but you need right start command, and each set needs three terminals to start. We suggest you use pycharm to run these codes which is what we use to develop.

When you are starting the first set of files, first, you should key in "ryu-manager ryu_control.py" to start the ryu controller first in the first terminal window. And then, you should type in "sudo python3 topo_star.py" in the second terminal to start the topology, and you will open a mininet CLI that you can talk to. You can type in commands like "net" or "pingall" in the mininet CLI to check if the topo and the ryu is working correctly.

When you are starting the second set of files, first you should type in "ryu-manager ryucontroller.py" to start the ryu controller in the first terminal. Then you should type in "sudo mn --custom topo.py --topo simpletopo --controller=remote,ip=127.0.0.1,port=6633" to start the topology in the second terminal. 

Warning: you should check the file path of yours and add them correctly into the command.

Now, you have correctly start your ryu controller and topology! You can test, edit the topology as you want. When you finish your exploring, we will teach you how to capture the traffic information stored inside the switch you have just created.



Welcome back! Now you have learned the basic rules of ryu and mininet. The next step is to capture————nonono, before we want to capture the traffic information we must generate some traffic, or what we found is some dead numbers doesn't change at all after the default generation of traffic when you type in those commands.

So how to generate traffic? There are a lot of methods to do that, and the method or command we use is "iperf". Turn to your second ternimal, and type in :


h1 iperf -s &
h2 iperf -c h1 -w 1k -t 600


The specific rule of iperf will not be given in this simple introduction. After that your host1 and host2 will start to send packages to each other throught the switch s0 for 600 seconds. 
Now we have traffic. Next step, open the flaskapp.py file and run it. Now we need your third ternimal window, in which you need to type in:


curl 







