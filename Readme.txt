EXCERCISE 1:

RUN:
./run_ex1_10s.sh MyPaxos 100   for 100 samples
./run_ex1_10s.sh MyPaxos 1000  for 1000 samples
./run_ex1_30s.sh MyPaxos 10000 for 10000 samples

We have 2 different .sh files differing for the waiting time before killing the app. In the former case such a time is set to 10s while in the latter is set to 30s.

The fact is that with 10000 samples, 10 seconds is not long enough time for the learners to learn the whole list of values. 


EXCERCISE 2:

RUN:
./run_ex2.sh MyPaxos 100 

This .sh file differs from ./run_ex1_10s.sh just for having initialised only 2 acceptors instead of 3.

While it would be more formally correct to go in the paxos.py file and change the global variable n_acceptors from 3 to 2, this would not lead to any difference in the results: switching from 3 to 2 acceptors, the quorum Qa does not change.


EXCERCISE 3:

RUN:
./run_ex3.sh MyPaxos 100 

In the sh file, only an acceptor is initialised.

Please notice that you would end up with different results depending on the value set for n_acceptors global variable in the paxos.py file.

If n_acceptors is left to 3 (default value), the learners end up learning nothing. Such a situation is like having 3 acceptors among which 2 are faulty (failing in the very early stages of the process). Meaning that n_acceptors<2f+1 and a quorum can be never be reached, explaining the reason of the termination property violation. 

On the other hand, if n_acceptors in paxos.py is switch to 1, we are simulating a scenario with 1 single no failing acceptor. In this case, the algorithm works perfectly with the learners learning all the required values  



EXCERCISE 4:


RUN:
./run_ex4_loss.sh MyPaxos 100

We run this in a virtual machine mounting linux.
We notice that setting LOSS to 0.0, the algorithm described so far will work correctly since we are simulating a lossless situation. For values rather than 0 for LOSS, the algorithm start failing. Not surprisingly, increasing LOSS rate will lead to a decrease of number of messages correctly learned.

In order to solve this problem he have developed a second version of the Paxos algorithm.
To run this version you first need to rename the file paxos_lossy_channels.py in  paxos.py (renaming the one currently in the folder with some other name to avoid overwriting).

The way we have implemented such a version is described in the report



EXCERCISE 5:

RUN:
./run_ex5_kill_acceptor.sh MyPaxos 1000

In this case you also need to go in paxos.py and set the global variables n_instance_BD and faulty_acceptors.

To kill 1 acceptor set faulty_acceptors=1 and n_instance_BD to any number lower than 1000, say 100.

To kill 2 acceptors set faulty_acceptors=1 and n_instance_BD to any number lower than 1000/2, say 100.

Explanation:
Processes with id lower or equal than faulty_acceptors will eventually die.
For instance setting faulty_acceptors=2 means that eventually acceptor 1 and 2 will die leaving only acceptor 3 alive. 

If n_instance_BD is set to 100, and faulty_acceptors=2 it means that acceptor with id 1 will die when it receives 100 instances while acceptor with id 2 will die when it receives 200 instances.

We decided to simulate the process crashing from python because this approach gives to us a better control on when a process should die. 

In a first implementation, we used to killed the process using a command in the .sh file: 
KILL_AC="kill -9 $APP_PID”
where APP_PID is the ID of the acceptor we wanted to kill, taken when the process is launched through ./acceptor.sh command

However, by doing so we ended up killing the process either too early or too late.

Simulating the scenario in python gives to us a strict control of the situation to check if everything is working as expected.

For instance if you run:
./run_ex5_kill_acceptor.sh MyPaxos 1000

having set: 
faulty_acceptors=2
n_instance_BD=100

we will find that 200 instances out of 1000 will be correctly learned. This is correct since up to 200 instances the condition n_acceptors>=2f+1 is met and the algorithm works correctly.
At the 201th instance, 2 acceptors out of 3 die and termination property cannot be met.

DISCLAIMER: before moving on and run exercise 6, set faulty_acceptors to 0 in paxos.py



EXCERCISE 6:

RUN:
./run_ex6.sh MyPaxos 100

The above will correctly work.
We tried to increase the number of instances but in this case the algorithm fails because the buffer used to send the history list from the acceptors to the recently born learner is too small too contain the whole history  

FINAL NOTE:
In order to implement the leader, we set that the proposer with id == 1 is the current leader of our Paxos.


