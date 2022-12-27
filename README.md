## 改动说明
Magic和Team字段是无效字段，我将Magic改成rwnd，因为拥塞控制sender需要实时更新receiver的rwnd。Team改成update_rwnd,update_rwnd=1时意味着sender向receiver请求rwnd。因为当rwnd=0时，sender不会像receiver发送数据，具体参考计网参考教材3.5.5。
对于可靠数据传输使用的是SR选择重选策略，拥塞控制实现了慢启动，快速恢复，拥塞避免，具体参考3.7中图3-51 TCP拥塞控制的FSM描述。超时时间间隔参考计网中文书3.5.3，其中对于每个已确认并且未重传的数据包计算SampleRTT。

# Set up your repo
First, clone the repo from github and change the git remote tag::
```
git clone https://github.com/SUSTech-CS305-Fall22/CS305-Project-Skeleton.git
cd CS305-Project-Skeleton
git remote rename origin staff
```
After doing so you can use the following command to get the latest update like newly-released checkpoints or so.
```
git pull staff
```
Then create a private repo your own on github, you will have the link <YOUR_URL> of your new repo.

Return to the local repo, run
```
git remote add group <YOUR_URL>
git push group -u
```
After this, you will be synchronize changes of your code to your own repo by
```
git push group
```
or simply
```
git push
```

In short, run 
```
git push
git pull group
```
when synchronizing to your repo,

Run
```
git pull staff
```
when fetching updates from the staff repo.


# How to run the example
This will be short version of the example described in the document.

In our example, a file will be divived into 4 chunks, and peer1 will have chunk1 and chunk2,
while peer2 will have chunk3 and chunk4. Peer1 will be invoked to download chunk3 from peer2.

## Step 1: Generate chunk data for peer and peer2:
First generate fragment that peer1 and peer2 have at the beginning
```
python3 util/make_data.py example/ex_file.tar ./example/data1.fragment 4 1,2
python3 util/make_data.py example/ex_file.tar ./example/data2.fragment 4 3,4
```
Then generate chunkhash data for peer1 to be downloaded:
```
sed -n "3p" master.chunkhash > example/download.chunkhash
```

## Step 2: Run the simulator:
```
perl util/hupsim.pl -m example/ex_topo.map -n example/ex_nodes_map -p 52305 -v 2
```

## Step 3: Start Peers
You need to start each peer in theri own shells.
### Start the sender:
```
export SIMULATOR="127.0.0.1: 52305"
python3 example/dumbsender.py -p example/ex_nodes_map -c example/data2.fragment -m 1 -i 2 -v 3
```

### Start the receiver:
```
export SIMULATOR="127.0.0.1: 52305"
python3 example/dumbreceiver.py -p example/ex_nodes_map -c example/data1.fragment -m 1 -i 1 -v 3
```

## Step 4:  Start downloading
Enter this message in the receiver's stdin
```
DOWNLOAD example/download.chunkhash example/test.fragment
```

## Finish downloading
After downloading successfully, you will see
```
GOT example/test.fragment
Expected chunkhash: 3b68110847941b84e8d05417a5b2609122a56314
Received chunkhash: 3b68110847941b84e8d05417a5b2609122a56314
Successful received: True
Congrats! You have completed the example!
```
