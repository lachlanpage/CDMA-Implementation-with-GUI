# Simple Implementation of CDMA in Python
# Created by Lachlan Page September 2018
import wx
import numpy as np
import binascii
from scipy.linalg import hadamard


def hadamard_generator(size):
    return hadamard(size, dtype=int)

def PN(size):
    if(size < 17):
        size = 17
    I = np.zeros([size,1])
    Q = np.zeros([size,1])
    I[15] = 1
    Q[15] = 1

    for n in range(16, size):
        I[n]=np.mod(I[n-15]+I[n-10]+I[n-8]+I[n-7]+I[n-6]+I[n-2],2)
        Q[n]=np.mod(Q[n-15]+Q[n-13]+Q[n-11]+Q[n-10]+Q[n-9]+Q[n-5]+Q[n-4]+Q[n-3],2)
    return [I,Q]

def convert_to_byte_list(b_string):
    ret_list = []
    x = b_string[2:]
    for value in x:
        ret_list.append(int(value))
    return ret_list

def convert_to_byte_array(b_array):
    str_ar = ""
    for digit in b_array:
        str_ar += str(int(digit))
    return str_ar

def remove_end_packet_frame(data_list):

    while(data_list[len(data_list)-3:].tolist() != [1,1,1]):
        data_list = data_list.tolist()
        data_list.pop(-1)
        data_list = np.asarray(data_list)
    data_list = data_list.tolist()
    data_list.pop(-1)
    data_list.pop(-1)
    data_list.pop(-1)
    data_list = np.asarray(data_list)
    return data_list

def get_random_data(length):
    rand_data = np.random.randint(2, size=length)
    rand_data = convert_to_byte_array(rand_data.tolist())
    return rand_data

class HelloFrame(wx.Frame):

    def __init__(self, *args, **kw):
        #Ensure parents init is called
        super(HelloFrame, self).__init__(*args, **kw)

        self.pnl = wx.Panel(self)

        self.btn_list = []
        self.checkbox_list = []
        self.input_list = []
        self.empty_channel_list = []
        self.sizer = wx.wx.BoxSizer(wx.VERTICAL)
        self.sizer.AddSpacer(10)

        font = wx.Font(18, wx.ROMAN, wx.ITALIC, wx.NORMAL)
        font2 = wx.Font(12, wx.ROMAN, wx.NORMAL, wx.NORMAL)
        font3 = wx.Font(10, wx.ROMAN, wx.NORMAL, wx.FONTWEIGHT_BOLD)

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.GetData, self.timer)
        self.timer.Start(400)


        transmitter_text = wx.StaticText(self.pnl, label="CDMA TRANSMITTER")
        transmitter_text.SetFont(font)
        self.sizer.Add(transmitter_text,0, wx.ALL | wx.CENTER, 10)
        author_text = wx.StaticText(self.pnl, label="Created by Lachlan Page")
        author_text.SetFont(font2)
        self.sizer.Add(author_text,0, wx.ALL | wx.CENTER, 25)
        info_text = wx.StaticText(self.pnl, label="Press ENTER to send entered data!")
        self.sizer.Add(info_text,0, wx.ALL | wx.CENTER, 10)
        self.decoded_list = []

        self.WALSH_CODE_SIZE = 64
        self.codes = hadamard_generator(self.WALSH_CODE_SIZE)
        self.CHANNELS = 5

        #Set Up Transmitter Data
        for i in range(1,self.CHANNELS):

            row_layout = wx.wx.BoxSizer(wx.HORIZONTAL)
            self.sizer.Add(row_layout, 0, wx.ALL|wx.CENTER, 10)
            self.sizer.AddSpacer(10)

            #Static Text Label
            channel_text = wx.StaticText(self.pnl,label="Channel: {}".format(i))
            channel_text.SetFont(font3)
            row_layout.Add(channel_text, 0, wx.ALL | wx.CENTER, 10)

            channel_input = wx.TextCtrl(self.pnl, wx.EXPAND, style=wx.TE_PROCESS_ENTER)
            channel_input.SetMinSize((300,50))
            channel_input.Bind(wx.EVT_TEXT_ENTER, self.GetData)
            self.input_list.append(channel_input)
            row_layout.Add(channel_input, 0, wx.ALL | wx.CENTER, 10)

            not_alpha = wx.CheckBox(self.pnl, label="gen Rdata")
            self.checkbox_list.append(not_alpha)
            row_layout.Add(not_alpha,0, wx.ALL | wx.CENTER, 10)

        self.sizer.Add(wx.StaticText(self.pnl, label=""),0, wx.ALL | wx.CENTER, 100)
        #Set Up Recieve GUI
        reciever_text = wx.StaticText(self.pnl, label="CDMA Reciever")
        reciever_text.SetFont(font)
        self.sizer.Add(reciever_text,0, wx.ALL | wx.CENTER, 10)

        info_text2 = wx.StaticText(self.pnl, label="Decoded data will be displayed below")
        info_text2.SetFont(font2)
        self.sizer.Add(info_text2,0, wx.ALL | wx.CENTER, 10)

        for i in range(1, self.CHANNELS+1):
            row_layout = wx.wx.BoxSizer(wx.HORIZONTAL)
            self.sizer.Add(row_layout, 0, wx.ALL|wx.CENTER, 0)
            self.sizer.AddSpacer(10)

            chan_text = wx.StaticText(self.pnl,label="Channel: {}".format(i-1))
            chan_text.SetFont(font3)
            row_layout.Add(chan_text, 0, wx.ALL | wx.CENTER, 10)

            channel_input = wx.TextCtrl(self.pnl, wx.EXPAND, style=wx.TE_PROCESS_ENTER)
            channel_input.SetMinSize((300,50))
            self.decoded_list.append(channel_input)
            row_layout.Add(channel_input, 0, wx.ALL | wx.CENTER, 10)

            empty_chan = wx.CheckBox(self.pnl, label="ch empty")
            self.empty_channel_list.append(empty_chan)
            row_layout.Add(empty_chan,0, wx.ALL | wx.CENTER, 10)

        self.pnl.SetSizer(self.sizer)

    def GetData(self, event):
        #Get the data from the inputs
        pre_encoded_list = []

        for i in range(0, len(self.input_list)):
            channel_data = self.input_list[i]
            generate_random_data = self.checkbox_list[i].GetValue()
            if(generate_random_data == True):
                data = get_random_data(30)
                channel_data.SetValue(data)
            else:
                data = channel_data.GetValue()

            pre_encoded_data = np.array([])
            if(data != ""):
                pre_encoded_data = bin(int(binascii.hexlify(data), 16))

            pre_encoded_data = convert_to_byte_list(pre_encoded_data)
            #Shift Data in range of -1 to 1
            pre_encoded_data = [i*2-1 for i in pre_encoded_data]
            pre_encoded_list.append(pre_encoded_data)

        #Now want to fix arry length mismatch
        max_data_len = max([len(i) for i in pre_encoded_list])+3
        for i in range(0, len(pre_encoded_list)):
            data = pre_encoded_list[i]
            data.append(1)
            data.append(1)
            data.append(1)
            while(len(data)!= max_data_len):
                #append zeros until we get to right length
                data.append(-1)

        #Data is all the same length, time to concatenate into data matrix
        pilot_signal = np.array([np.ones(max_data_len)])

        user_matrix = pilot_signal
        backup_matrix = pilot_signal

        for data in pre_encoded_list:
            data = np.asarray(data)
            data = np.reshape(data, (1 , len(data)))
            backup_matrix = np.concatenate((backup_matrix, data), axis = 0)
            user_matrix = np.concatenate((user_matrix, data), axis = 0)

        codes = hadamard_generator(self.WALSH_CODE_SIZE)

        spread_matrix = np.empty((0,max_data_len*self.WALSH_CODE_SIZE), int)
        for channel in range(0, self.CHANNELS):
            chan_code = codes[:, channel]
            user_data = user_matrix[channel, :]
            spreaded_data = np.array(np.zeros(max_data_len*self.WALSH_CODE_SIZE))
            #spreaded_data = np.array([])
            count = 0
            for i in range(0, max_data_len):
                for j in range(0, self.WALSH_CODE_SIZE):
                    spreaded_data[count] = user_data[i]*chan_code[j]
                    count += 1
            #spread_matrix = np.append(spread_matrix, spreaded_data)
            spread_matrix = np.concatenate((spread_matrix, [spreaded_data]), axis=0)
            #pread_matrix = np.insert(())

        signal_to_transmit = sum(spread_matrix)

        #signal_to_recieve = signal_to_transmit
        #A = signal_to_transmit
        [I,Q] = PN(max_data_len*self.WALSH_CODE_SIZE)
        pn_sequence = I+Q*1j
        signal_to_transmit = np.multiply(signal_to_transmit, pn_sequence.T)

        #print("Encoded Data Packet: ")
        #print(signal_to_transmit.tolist())
        #print("Encoded Data Packet Size: ", signal_to_transmit.shape)
        #print(signal_to_transmit.shape)
        #print(signal_to_transmit)


        #Now lets decode the signal and set text box to value just to check :)
        signal_to_recieve = signal_to_transmit
        pn_sequence = I+Q*1j
        signal_to_recieve = np.multiply(signal_to_recieve, np.asmatrix(pn_sequence).H)
        signal_to_recieve = np.ravel(signal_to_recieve)
        #print("After PN DECODING:")
        #print(signal_to_recieve)
        #print("\n")

        #print("Is PN Decoding equal to walsh encoding?")
        #print(sum(spread_matrix) == signal_to_recieve)
        user_decoded_data = np.empty([self.CHANNELS,max_data_len])
        block_count = 0
        for i in range(0, (self.WALSH_CODE_SIZE*max_data_len)-1, self.WALSH_CODE_SIZE):
            user_data = np.empty([self.CHANNELS,max_data_len])
            for channel in range(0,self.CHANNELS):
                channel_code = codes[:, channel]
                chunk = []
                user_data_count = 0

                if((i+self.WALSH_CODE_SIZE) > self.WALSH_CODE_SIZE*max_data_len):
                    chunk = signal_to_recieve[i:-1]
                else:
                    chunk = signal_to_recieve[i:(i+self.WALSH_CODE_SIZE)-1]
                #Have chunk of data now do walsh code muxing
                correlation_factor = 0
                for j in range(0,self.WALSH_CODE_SIZE-1):
                    correlation_factor = correlation_factor+(chunk[j]*channel_code[j])
                if(correlation_factor > 0):
                    user_decoded_data[channel][block_count] = 1
                else:
                    user_decoded_data[channel][block_count] = 0
                #print(channel, block_count)
            block_count = block_count+1

        #print(user_decoded_data[1])
        #self.decoded_list[0].SetValue("111111111")
        for i in range(0, len(self.decoded_list)):
            #print("DECODED DATA PACKET:")
            #print(user_decoded_data[i].tolist())
            edited_packet = remove_end_packet_frame(user_decoded_data[i])
            #print("EDITED PACKET")
            #print(edited_packet)
            #print("\n")

            conv_str = convert_to_byte_array(edited_packet)
            #print(conv_str)
            #conv_str = conv_str[:len(conv_str)-3]
            #print(conv_str)
            #print("\n")
            try:
                d = int(str(conv_str),2)
                d = binascii.unhexlify('%x'% d)
                self.decoded_list[i].SetValue(d)
                self.empty_channel_list[i].SetValue(False)
                #print("Converting binary array to ascii: ")
                #print("Channel {}: {}".format(i,d))

            except ValueError:
                #print("Channel {}: is EMPTY!".format(i))
                self.decoded_list[i].SetValue("")
                self.empty_channel_list[i].SetValue(True)
            #print("\n\n")



if __name__ == '__main__':
    app = wx.App()
    frm = HelloFrame(None, title="CDMA RECIEVER/TRANSMITTER")
    frm.Show()
    app.MainLoop()
