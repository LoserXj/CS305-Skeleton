
class Data (object):

    def __init__(self,msg,seq,state):
        self.msg = msg          # 发送的数据
        self.seq = seq          # 发送的数据序号
        self.state = state      # 在sender中，0表示未发送，1表示已发送，2表示已接收到ACK确认
        self.is_resend = False  # 用于记录该数据是否重传，在计算超时时间间隔时不考虑重传的包
        self.is_cal = False     # 用于记录该数据是否已经计算过超时时间间隔