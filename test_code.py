import struct
HEADER_LEN = struct.calcsize("HBBHHII")
print(HEADER_LEN)
print(struct.calcsize("I4s4sHH"))