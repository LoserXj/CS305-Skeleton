

class Receiver(object):

    def __init__(self,host,port,receive_chunk_hash,output_file,has_chunks):
        self.host = host
        self.port = port
        self.send_addr = None
        self.receive_chunk_hash = receive_chunk_hash    # 下载的块,用于后续concurrent通信区分
        self.output_file = output_file                  # 下载后写入文件
        self.receive_buffer = 200                        # 接收缓存大小,初始值设为14
        self.rwnd = 200                                 # 接收窗口大小,初始值设为14
        self.ack = 0                                    # recv已确认的最大有序数据块编号
        self.last_byte_read = 0                         # 从缓存中读出数据流的个数
        self.last_byte_receive = 0                      # 从网络中到达的数据流的个数
        self.receive_queue = []                         # 接收队列
        self.recv_data = []                             # 采用选择重传策略，用来保存失序的数据
        self.finish_handshaking = False                 # 是否完成三次握手定理
        self.has_chunks = has_chunks                    # 拥有的数据块
