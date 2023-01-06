import math
import sys
import os
import time
from random import random
import matplotlib.pyplot as plt
from Data import Data
from Receiver import Receiver
from Sender import Sender
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import select
import util.simsocket as simsocket
import struct
import socket
import util.bt_utils as bt_utils
import hashlib
import argparse
import pickle


"""
This is CS305 project skeleton code.
Please refer to the example files - example/dumpreceiver.py and example/dumpsender.py - to learn how to play with this skeleton.
"""

BUF_SIZE = 1400
CHUCK_DATA_SIZE = 512 * 1024
HEADER_LEN = struct.calcsize("HBBHHII")
MAX_PAYLOAD = 1024

config = None
ex_output_file = None
ex_sending_chunkhash = ""
ex_received_chunk = dict()
ex_downloading_chunkhash = ""
recv = None   # 接收端
send = None   # 发送端

def process_download(sock, chunkfile, outputfile):
    '''
    if DOWNLOAD is used, the peer will keep getting files until it is done
    '''
    global ex_output_file
    global ex_received_chunk
    global ex_downloading_chunkhash
    global recv

    ex_output_file = outputfile
    download_hash = bytes()
    recv_download_hash = ''
    with open(chunkfile, "r") as cf:
        index, datahash_str = cf.readline().strip().split(" ")
        recv_download_hash = datahash_str
        ex_received_chunk[datahash_str] = bytes()
        ex_downloading_chunkhash = datahash_str

        datahash = bytes.fromhex(datahash_str)
        download_hash = download_hash + datahash

    update_rwnd = 0  # 后续更改
    if recv != None:
        print("receiver object has existed")
    else :
        print("initial receiver object")
        recv = Receiver(config.ip,config.port,recv_download_hash,outputfile,config.haschunks)
        print(f"initial receiver object success, receiver host : {recv.host} , receiver port : {recv.port} , receiver downloads chunk hash : {recv.receive_chunk_hash}")
    whohas_header = struct.pack("HBBHHII", socket.htons(recv.rwnd), 0, 0,
                                socket.htons(HEADER_LEN),
                                socket.htons(HEADER_LEN + len(
                                    download_hash)), socket.htonl(0), socket.ntohl(0))
    whohas_pkt = whohas_header + download_hash
    peer_list = config.peers
    for p in peer_list:
        if int(p[0]) != config.identity:
            sock.sendto(whohas_pkt, (p[1], int(p[2])))

def sender_get_type_zero(sock,data,from_addr,update_rwnd,rwnd):
    global config
    global ex_sending_chunkhash
    global send

    whohas_chunk_hash = data[:20]
    chunkhash_str = bytes.hex(whohas_chunk_hash)
    ex_sending_chunkhash = chunkhash_str
    print(f"whohas: {chunkhash_str}, has: {list(config.haschunks.keys())}")
    if chunkhash_str in config.haschunks:
        # team需要特殊化
        #  def __init__(self,host,port,chunk_hash,send_addr,time_out):
        if send == None:
            print("initial sender object")
            use_RTT= True
            if config.timeout==0:
                use_RTT = False
                config.timeout = 30
            send = Sender(config.ip, config.port, chunkhash_str, from_addr, config.timeout,config.haschunks,use_RTT)
            send.rwnd = rwnd
            print(
                f"initial sender object success, sender host : {send.host} , sender port : {send.port} , sender sends chunk hash : {send.chunk_hash} , "
                f"send has rwnd : {send.rwnd}")
        else:
            print("sender object has existed")
        ihave_header = struct.pack("HBBHHII", send.rwnd, 0, 1, socket.htons(HEADER_LEN),
                                   socket.htons(HEADER_LEN + len(whohas_chunk_hash)), socket.htonl(0),
                                   socket.htonl(0))
        ihave_pkt = ihave_header + whohas_chunk_hash
        sock.sendto(ihave_pkt, from_addr)

def receiver_get_type_one(sock,data,from_addr,update_rwnd):
    global config
    global ex_sending_chunkhash
    global recv
    get_chunk_hash = data[:20]
    recv.send_addr = from_addr
    recv.finish_handshaking = True
    print(f"receiver finishes shaking hand and the server address is {recv.send_addr}")
    get_header = struct.pack("HBBHHII", socket.htons(recv.rwnd), 0, 2, socket.htons(HEADER_LEN),
                             socket.htons(HEADER_LEN + len(get_chunk_hash)), socket.htonl(0), socket.htonl(0))
    get_pkt = get_header + get_chunk_hash
    sock.sendto(get_pkt, from_addr)

def sender_get_type_two(sock,from_addr,update_rwnd,rwnd):
    global config
    global ex_sending_chunkhash
    global send
    global recv
    # send = Sender(config.ip, config.port, '', from_addr, config.timeout, config.haschunks)
      # 获得需要get的pkt
    send.rwnd = rwnd
    if send.send_addr!=from_addr:
        print("the sender's send_addr is not the same with addr getted from socket")
        return
    send.finish_hand_shake = True
    # 发送窗口中数据小于最大容量时，尝试添加新数据
    send_size = min(int(send.rwnd),int(send.cwnd))
    for i in range(send_size):
        if send.base >= 512:
            break
        # 大于或者等于base+window_size的数据是不能使用的
        if send.next_seq_num+1>send.base+send.window_size:
            # print("data seq is larger than base + window_size , we should drop it out")
            break
        # 发送队列缓存数据个数不能超过拥塞窗口数量
        if send.next_seq_num + 1 - send.base > send_size:
            # print("data in send_queue is full")
            break
        # 封装数据进Data类
        seq = send.next_seq_num
        msg = config.haschunks[ex_sending_chunkhash][(seq-1)*MAX_PAYLOAD:seq*MAX_PAYLOAD]
        data = Data(msg,seq,1)
        send.send_queue.append(data)
        data_header = struct.pack("HBBHHII", socket.htons(send.rwnd), 0, 3, socket.htons(HEADER_LEN),
                                  socket.htons(HEADER_LEN), socket.htonl(seq), socket.htonl(0))
        send.next_seq_num += 1
        # 定时器开始计时,记录每个包发送的时间
        send.pkg_time.append(time.time())
        sock.sendto(data_header + msg, send.send_addr)
        print(f"send :{seq} , send base : {send.base} , send next_seq_num ; {send.next_seq_num} , send cwnd : {send.cwnd} send queue length : {len(send.send_queue)}")

def receiver_get_type_three(sock,data,update_rwnd,seq):
    global recv
    global config
    # 首先计算接收窗口rwnd的值，如果rwnd=0，则舍弃该数据
    recv.rwnd = recv.receive_buffer - (recv.last_byte_receive - recv.last_byte_read)

    if recv.rwnd == 0:
        print("rwnd is full")
        return
    # sender需要receiver更新rwnd
    if update_rwnd == 1:
        print(f"receiver tells sender to update rwnd, receiver rwnd is {recv.rwnd}")
        update_rwnd_header = struct.pack("HBBHHII", socket.htons(recv.rwnd), 1, 4, socket.htons(HEADER_LEN),
                              socket.htons(HEADER_LEN), socket.htonl(0), socket.htonl(recv.ack))
        sock.sendto(update_rwnd_header,recv.send_addr)
        return

    # receiver 接收到来自sender的数据块
    # 如果seq小于ack则说明发送的是不需要的数据
    if seq <= recv.ack:
        print(f"dupAck ack : {recv.ack} , seq : {seq}")
        ack_header = struct.pack("HBBHHII", socket.htons(recv.rwnd), 0, 4, socket.htons(HEADER_LEN),
                              socket.htons(HEADER_LEN), socket.htonl(0), socket.htonl(recv.ack))
        sock.sendto(ack_header,recv.send_addr)
    elif seq > recv.ack and seq <= recv.receive_buffer + recv.ack:
        # if random()<0.05:
        #     print(f"loss packet seq is {seq}")
        #     return
        # 读入数据流个数加1
        recv.last_byte_receive+=1
        # 用于记录接收到的失序数据
        recvData = Data(data,seq,0)
        # 将数据插入到接收缓存队列中
        recv.receive_queue.append((seq,recvData))
        recv.receive_queue = sorted(recv.receive_queue,key=lambda tup:tup[0])
        # 如果接收到的序号位于窗口第一个,意味着有部分数据是有序的,则接收窗口移动
        if seq == recv.ack+1:
            receive_queue_len = len(recv.receive_queue)
            for index in range(receive_queue_len):
                if recv.receive_queue[0][1].seq!=recv.last_byte_read+1:
                    break
                # 已读数据+1
                recv.last_byte_read+=1
                # 已确认的最小有序ack+1
                recv.ack+=1
                recv.recv_data.append(recv.receive_queue[0][1].msg)
                del recv.receive_queue[0]

        recv.rwnd = recv.receive_buffer - (recv.last_byte_receive - recv.last_byte_read)
        print(f"response : {seq} , receiver ack : {recv.ack} , receive queue length : {len(recv.receive_queue)} , receiver rwnd : {recv.rwnd}")
        ack_header = struct.pack("HBBHHII", socket.htons(recv.rwnd), 0, 4, socket.htons(HEADER_LEN),
                                 socket.htons(HEADER_LEN), socket.htonl(0),socket.htonl(seq))
        sock.sendto(ack_header, recv.send_addr)

def sender_get_type_four(sock,update_rwnd,ack,rwnd):
    global config
    global ex_sending_chunkhash
    global send
    global recv
    # send = Sender(config.ip, config.port, '', '', config.timeout, config.haschunks)
    # receiver告诉sender去更新rwnd
    if update_rwnd==1:
        send.rwnd = rwnd
        return
    # 设置接收到ack的时间，用于更新超时时间间隔
    time_recv = time.time()
    #接收到的ack小于base，收到已经确认过的ack
    if ack < send.base:
        get_dup_ack(sock,update_rwnd)
        send.cwnd_list.append(int(send.cwnd))
        return
    is_valid_ack = False

    # 判断接收到的ack序号是否是有效的,ack序号位于发送缓存队列中，则说明是有效的，反之是无效的ack
    for data in send.send_queue:
        if data.seq == ack and data.state != 2:
            is_valid_ack = True
            break
    # 如果不是有效的ack，则说明是冗余的
    if not is_valid_ack:
        print(f"response ack: {ack}")
        get_dup_ack(sock,update_rwnd)
        send.cwnd_list.append(int(send.cwnd))
        return

    # 获得有效的ack，更新冗余ACK = 0，根据sender处于不同的拥塞状态执行不同的操作
    send.dup_ack_count = 0
    # 处于慢启动状态
    if send.congestion_state == 0:
        # 更新cwnd和ssthresh
        # print(f"sender congestion state : {send.congestion_state}")
        get_new_ack(ack,time_recv)
        if send.cwnd<send.ssthresh:
            send.cwnd = min(send.cwnd+1,send.ssthresh)
        # cwnd大于等于ssthresh，进入拥塞避免状态
        else:
            send.cwnd = send.ssthresh
            print(f"sender changes congestion state from {send.congestion_state} into {1}")
            send.congestion_state = 1
        send.cwnd_list.append(int(send.cwnd))
        # print(f"sender cwnd : {send.cwnd} , sender ssthresh : {send.ssthresh}")
    # 处于拥塞避免状态
    elif send.congestion_state == 1:
        # print(f"sender congestion state : {send.congestion_state}")
        get_new_ack(ack,time_recv)
        send.cwnd += 1/int(send.cwnd)
        send.cwnd_list.append(int(send.cwnd))
        # print(f"sender cwnd : {send.cwnd} , sender ssthresh : {send.ssthresh}")
    # 处于快速恢复状态
    else:
        # print(f"sender congestion state : {send.congestion_state}")
        get_new_ack(ack,time_recv)
        # 快速恢复状态获得新的ack，则进入拥塞避免状态
        print(f"sender changes congestion state from {send.congestion_state} into {1}")
        send.cwnd = send.ssthresh
        send.cwnd_list.append(int(send.cwnd))
        send.congestion_state = 1
        # print(f"sender cwnd : {send.cwnd} , sender ssthresh : {send.ssthresh}")

def get_new_ack(ack,time_recv):
    global send
    # send = Sender(config.ip, config.port, '', '', config.timeout, config.haschunks)
    # 更新发送缓存队列中数据的状态

    for i in range(len(send.send_queue)):
        data = send.send_queue[i]
        if data.seq == ack:
            print(f"get ACK : {ack} send base : {send.base} send next seq num : {send.next_seq_num} sender cwnd : {send.cwnd} , sender ssthresh : {send.ssthresh} "
                  f"")
            data.state = 2
            #没有被重传的数据，更新超时时间间隔
            if not data.is_resend and not data.is_cal :
                send.time_out_interval = cal_time_out_interval(estimated_RTT=send.estimated_RTT,alpha=send.alpha,dev_RTT=send.dev_RTT,beta=send.beta,
                                                               time_send=send.pkg_time[i],time_rece=time_recv)

                data.is_cal = True
            send.send_queue[i] = data
            break
    # 如果接收到base的ack，移动拥塞控制窗口
    if ack == send.base:
        slide_len = 0
        for data in send.send_queue:
            if data.state ==2:
                slide_len+=1
            else:
                break
        # 滑动拥塞控制窗口和计时器窗口
        send.send_queue=send.send_queue[slide_len:]
        send.pkg_time=send.pkg_time[slide_len:]
        # 更新base的值
        send.base+=slide_len

def cal_time_out_interval(estimated_RTT,alpha,dev_RTT,beta,time_send,time_rece):
    global send

    sample_RTT = time_rece - time_send
    estimated_RTT = (1-alpha) * estimated_RTT + alpha * sample_RTT
    dev_RTT = (1-beta) * dev_RTT + abs(sample_RTT - estimated_RTT) * beta
    if not send.use_RTT:
        return estimated_RTT + 4 * dev_RTT
    else:
        return send.time_out_interval

def get_dup_ack(sock,update_rwnd):
    global send
    # send = Sender(config.ip, config.port, '', '', config.timeout, config.haschunks)
    print(f"get dupACK: {send.dup_ack_count+1}")
    send.dup_ack_count+=1
    # 如果冗余ACK数=3，则进入快速恢复状态，我们在sender类中规定，0表示处于慢启动，1表示处于快速恢复，2表示处于拥塞避免
    if send.dup_ack_count==3:
        # sender 进入快速恢复状态
        # print(f"sender changes congestion state from {send.congestion_state} into {2}")
        send.congestion_state = 2
        # print(f"sender cwnd : {send.cwnd} , sender ssthresh : {send.ssthresh}")
        # print("The retransmission operation is performed")
        re_send(sock,update_rwnd,"")

def re_send(sock,update_rwnd,data_resend):
    global send
    # send = Sender(config.ip, config.port, '', '', config.timeout, config.haschunks)

    # 接收到超过三个冗余ACK进入重传，更新cwnd和ssthresh的值
    if send.congestion_state == 2:
        # 重传所有未确认的ack包
        for i in range(len(send.send_queue)):
            data = send.send_queue[i]
            # 如果data.state!=2,说明还未被确认，需要重传,同时更新计时器,更新data的is_resend值
            if data.state != 2:
                print(f"resend seq : {data.seq} sender changes congestion state from {send.congestion_state} into {2} "
                      f"sender cwnd : {send.cwnd} , sender ssthresh : {send.ssthresh} ")
                send.pkg_time[i] = time.time()
                data.is_resend = True
                send.send_queue[i] = data
                data_header = struct.pack("HBBHHII", socket.htons(send.rwnd), update_rwnd, 3, socket.htons(HEADER_LEN),
                                          socket.htons(HEADER_LEN), socket.htonl(data.seq), socket.htonl(0))
                sock.sendto(data_header + data.msg, send.send_addr)
        if send.cwnd<=2:
            send.ssthresh = 1.0
        if send.cwnd > 2:
            send.ssthresh = send.cwnd/2
        send.cwnd =send.ssthresh + 3

    # 超时执行重传,更新cwnd和ssthresh的值同时进入慢启动状态
    else:

        data_header = struct.pack("HBBHHII", socket.htons(send.rwnd), update_rwnd, 3, socket.htons(HEADER_LEN),
                                  socket.htons(HEADER_LEN), socket.htonl(data_resend.seq), socket.htonl(0))
        sock.sendto(data_header + data_resend.msg, send.send_addr)
        send.congestion_state = 0
        if send.cwnd<=2:
            send.ssthresh = 1.0
        if send.cwnd > 2:
            send.ssthresh = send.cwnd/2
        send.cwnd = 1.0
        print(
            f"time out resend seq {data_resend.seq} sender changes congestion state from {send.congestion_state} into {0} "
            f"sender cwnd : {send.cwnd} , sender ssthresh : {send.ssthresh} send base : {send.base}")

def process_inbound_udp(sock):
    global config
    global ex_sending_chunkhash
    global send
    global recv
    # recv = Receiver(config.ip, config.port, '', '', '')
    # send = Sender(config.ip, config.port, '', '', config.timeout, config.haschunks)
    # Receive pkt
    pkt, from_addr = sock.recvfrom(BUF_SIZE)
    rwnd_hton, update_rwnd_hton, Type_hton, hlen_hton, plen_hton, Seq_hton, Ack_hton = struct.unpack("HBBHHII", pkt[:HEADER_LEN])
    rwnd, update_rwnd, type, hlen, plen, seq, ack =  socket.ntohs(rwnd_hton), update_rwnd_hton, Type_hton, socket.ntohs(hlen_hton), socket.ntohs(plen_hton), socket.ntohl(Seq_hton), socket.ntohl(Ack_hton)
    data = pkt[HEADER_LEN:]

    if type == 0:
        sender_get_type_zero(sock=sock,data=data,from_addr=from_addr,update_rwnd=update_rwnd,rwnd=rwnd)
    elif type == 1:
        receiver_get_type_one(sock=sock,data=data,from_addr=from_addr,update_rwnd=update_rwnd)
    elif type == 2:
         # 获得需要get的pkt
        sender_get_type_two(sock=sock, from_addr=from_addr, update_rwnd=update_rwnd,rwnd=rwnd)
    elif type == 3:
        receiver_get_type_three(sock, data, update_rwnd, seq)

        # 如果recviver接收到所有的数据，则写入到相应的文件中

        if len(recv.recv_data) == 512:
            for i in range(512):
                ex_received_chunk[ex_downloading_chunkhash]+=recv.recv_data[i]
        if len(ex_received_chunk[ex_downloading_chunkhash]) == CHUCK_DATA_SIZE:
            with open(ex_output_file, "wb") as wf:
                pickle.dump(ex_received_chunk, wf)

            config.haschunks[ex_downloading_chunkhash] = ex_received_chunk[ex_downloading_chunkhash]

            print(f"GOT {ex_output_file}")
            sha1 = hashlib.sha1()
            sha1.update(ex_received_chunk[ex_downloading_chunkhash])
            received_chunkhash_str = sha1.hexdigest()
            print(f"Expected chunkhash: {ex_downloading_chunkhash}")
            print(f"Received chunkhash: {received_chunkhash_str}")
            success = ex_downloading_chunkhash == received_chunkhash_str
            print(f"Successful received: {success}")
            if success:
                print("Congrats! You have completed the example!")
            else:
                print("Example fails. Please check the example files carefully.")

    elif type == 4:

        if  send is not None and send.base * MAX_PAYLOAD > CHUCK_DATA_SIZE:

            print(len(send.cwnd_list))
            # print(x)
            print(send.cwnd_list)
            plt.plot( send.cwnd_list)
            plt.savefig("congestionControlAnalysis.png")

            print(f"finished sending {ex_sending_chunkhash}")
            send = None
            pass
        else:
            sender_get_type_four(sock=sock,update_rwnd=update_rwnd,ack=ack,rwnd=rwnd)

        # else:
        #     left = ack_num * MAX_PAYLOAD
        #     right = min((ack_num + 1) * MAX_PAYLOAD, CHUCK_DATA_SIZE)
        #     next_data = config.haschunks[ex_sending_chunkhash][left:right]
        #     # 后期应该加上max_number，可能返回denied
        #     data_header = struct.pack("HBBHHII", socket.htons(52305), update_rwnd, 3, socket.htons(HEADER_LEN),
        #                               socket.htons(HEADER_LEN + len(next_data)), socket.htonl(ack_num + 1), 0)
        #     sock.sendto(data_header + next_data, from_addr)

def process_user_input(sock):
    command, chunkf, outf = input().split(' ')
    if command == 'DOWNLOAD':
        process_download(sock ,chunkf, outf)
    else:
        pass

def peer_run(config):
    addr = (config.ip, config.port)
    sock = simsocket.SimSocket(config.identity, addr, verbose=config.verbose)
    # send = Sender(config.ip, config.port, '', '', config.timeout, config.haschunks)
    try:
        while True:
            # 定时器需要一直运行,sender需要一直尝试给receiver发送数据,所以放在主循环
            if send!=None:
                if send.finish_hand_shake:
                    send_size = min(int(send.rwnd),int(send.cwnd))
                    # sender需要更新rwnd
                    if send_size == 0:
                        update_rwnd_header = struct.pack("HBBHHII", socket.htons(send.rwnd), 1, 3, socket.htons(HEADER_LEN),
                                  socket.htons(HEADER_LEN), socket.htonl(0), socket.htonl(0))
                        sock.sendto(update_rwnd_header,send.send_addr)
                    for i in range(send_size):
                        # 如何数据发送完了则不用在发送
                        if send.base>=512:
                            break
                        # 大于或者等于base+window_size的数据是不能使用的
                        if send.next_seq_num + 1 > send.base + send.window_size:
                            # print("data seq is larger than base + window_size , we should drop it out")
                            break
                        # 发送队列缓存数据个数不能超过拥塞窗口数量
                        if send.next_seq_num + 1 - send.base > send_size:
                            # print("data in send_queue is full")
                            break
                        # 封装数据进Data类
                        seq = send.next_seq_num
                        msg = config.haschunks[ex_sending_chunkhash][(seq - 1) * MAX_PAYLOAD:seq * MAX_PAYLOAD]
                        data = Data(msg, seq, 1)
                        send.send_queue.append(data)
                        data_header = struct.pack("HBBHHII", socket.htons(send.rwnd), 0, 3, socket.htons(HEADER_LEN),
                                                  socket.htons(HEADER_LEN), socket.htonl(seq), socket.htonl(0))
                        send.next_seq_num += 1
                        # 定时器开始计时,记录每个包发送的时间
                        send.pkg_time.append(time.time())
                        sock.sendto(data_header + msg, send.send_addr)
                        print(
                            f"send :{seq} , send base : {send.base} , send next_seq_num ; {send.next_seq_num} , send cwnd : {send.cwnd} send queue length : {len(send.send_queue)}")

                    # 计时器运转，判断是否超时
                    for i in range(len(send.pkg_time)):
                        # 没有收到确认的数据需要判断是否超时
                        data_resend = send.send_queue[i]
                        if send.send_queue[i].state!=2:
                            time_now = time.time()
                            if time_now - send.pkg_time[i] > send.time_out_interval:
                                # print(f"time_out_seq : {data_resend.seq} ")
                                re_send(sock=sock,update_rwnd=0,data_resend=data_resend)
                                data_resend.re_send=True
                                send.send_queue[i]=data_resend

            ready = select.select([sock, sys.stdin],[],[], 0.1)
            read_ready = ready[0]
            if len(read_ready) > 0:
                if sock in read_ready:
                    process_inbound_udp(sock)
                if sys.stdin in read_ready:
                    process_user_input(sock)
            else:
                # No pkt nor input arrives during this period 
                pass
    except KeyboardInterrupt:
        pass
    finally:
        sock.close()


if __name__ == '__main__':
    """
    -p: Peer list file, it will be in the form "*.map" like nodes.map.
    -c: Chunkfile, a dictionary dumped by pickle. It will be loaded automatically in bt_utils. The loaded dictionary has the form: {chunkhash: chunkdata}
    -m: The max number of peer that you can send chunk to concurrently. If more peers ask you for chunks, you should reply "DENIED"
    -i: ID, it is the index in nodes.map
    -v: verbose level for printing logs to stdout, 0 for no verbose, 1 for WARNING level, 2 for INFO, 3 for DEBUG.
    -t: pre-defined timeout. If it is not set, you should estimate timeout via RTT. If it is set, you should not change this time out.
        The timeout will be set when running test scripts. PLEASE do not change timeout if it set.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', type=str, help='<peerfile>     The list of all peers', default='nodes.map')
    parser.add_argument('-c', type=str, help='<chunkfile>    Pickle dumped dictionary {chunkhash: chunkdata}')
    parser.add_argument('-m', type=int, help='<maxconn>      Max # of concurrent sending')
    parser.add_argument('-i', type=int, help='<identity>     Which peer # am I?')
    parser.add_argument('-v', type=int, help='verbose level', default=0)
    parser.add_argument('-t', type=int, help="pre-defined timeout", default=0)
    args = parser.parse_args()

    config = bt_utils.BtConfig(args)
    peer_run(config)
