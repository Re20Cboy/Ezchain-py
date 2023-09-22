from const import *
import random
import time


class Account:
    def __init__(self):
        self.addr = None
        self.prf = []
        self.privateKey = None
        self.publicKey = None
