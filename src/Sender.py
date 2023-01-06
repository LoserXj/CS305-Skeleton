
class Sender (object):
    def __init__(self,host,port,chunk_hash,send_addr,time_out,has_chunks,use_RTT):
        self.host = host
        self.port = port
        self.chunk_hash = chunk_hash
        self.send_addr = send_addr
        self.finish_hand_shake = False       # 是否完成握手定理，如果sender接收到type = 2的数据说明完成握手定理
        self.rwnd = 200                       # 接收端接收窗口大小，初始化为200
        self.window_size = 100                # 发送端窗口大小
        self.cwnd = 14                       # 拥塞窗口大小
        self.send_queue = []                 # 缓存发送数据
        self.base = 1                        # 基序号
        self.next_seq_num = 1                # 下一个序号
        self.ssthresh = 64.0              # 慢启动阈值
        self.dup_ack_count = 0               # 冗余ACK计数
        self.congestion_state = 0            # 0表示处于慢启动，1表示处于快速恢复，2表示处于拥塞避免
        self.use_RTT = use_RTT               # 是否是固定的RTT
        self.estimated_RTT = time_out        # SampleRTT的加权平均值
        self.alpha = 0.125                   # 计算SampleRTT的权重值
        self.dev_RTT = 0                     # RTT偏差
        self.beta = 0.25                     # 计算DevRTT的权重
        self.time_out_interval = time_out    # 重传超时时间间隔
        self.pkg_time = []                   # 定时器，存储每个pkg的发送时间
        self.has_chunks = has_chunks         # 拥有的数据
        self.cwnd_list = []                  # 用来记录cwnd的变化，用来画图