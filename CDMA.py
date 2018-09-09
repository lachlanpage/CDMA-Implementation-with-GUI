#Simple CDMA implementaiton
#Created by Lachlan Page Sep 2018
import wx
import numpy as np
import binascii
from scipy.linalg import hadamard
#GLOBALS - Bad practice but makes life easy :-)
CHANNELS = 10
WALSH_CODE_SIZE = 64

input_list = []
checkbox_gen_data_list = []
empty_channel_list = []
decoded_list = []

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

def GetData(event):
        #Get the data from the inputs
        pre_encoded_list = []

        for i in range(0, len(input_list)):
            channel_data = input_list[i]
            generate_random_data = checkbox_gen_data_list[i].GetValue()

            if(generate_random_data == True):
                data = get_random_data(30)
                channel_data.SetValue(data)
            else:
                data = channel_data.GetValue()

            pre_encoded_data = np.array([])
            if(data != ""):
                pre_encoded_data = bin(int(binascii.hexlify(data), 16))

            pre_encoded_data = convert_to_byte_list(pre_encoded_data)
            #Shift Data in range of -1 to 1, makes correlating easier
            pre_encoded_data = [i*2-1 for i in pre_encoded_data]
            pre_encoded_list.append(pre_encoded_data)

        #Increase max length by 3 as we append our end packet frame signature
        max_data_len = max([len(i) for i in pre_encoded_list])+3
        for i in range(0, len(pre_encoded_list)):
            data = pre_encoded_list[i]
            data.append(1)
            data.append(1)
            data.append(1)
            #For consistency want signals to all be same length
            #Append (0) / mean shifted (-1) to shorter signals
            while(len(data)!= max_data_len):
                data.append(-1)

        #Channel 0
        pilot_signal = np.array([np.ones(max_data_len)])
        #Holds shifted mean data [1/-1]
        user_matrix = pilot_signal
        #Holds non shifted mean data [1/0]
        backup_matrix = pilot_signal
        #Data is all the same length, time to concatenate into data matrix :)
        for data in pre_encoded_list:
            data = np.asarray(data)
            data = np.reshape(data, (1 , len(data)))
            backup_matrix = np.concatenate((backup_matrix, data), axis = 0)
            user_matrix = np.concatenate((user_matrix, data), axis = 0)
        codes = hadamard_generator(WALSH_CODE_SIZE)
        #Holds the walsh encoded data for each channel
        spread_matrix = np.empty((0,max_data_len*WALSH_CODE_SIZE), int)
        for channel in range(0, CHANNELS):
            chan_code = codes[:, channel]
            user_data = user_matrix[channel, :]
            spreaded_data = np.array(np.zeros(max_data_len*WALSH_CODE_SIZE))

            count = 0
            for i in range(0, max_data_len):
                for j in range(0, WALSH_CODE_SIZE):
                    spreaded_data[count] = user_data[i]*chan_code[j]
                    count += 1
            spread_matrix = np.concatenate((spread_matrix, [spreaded_data]), axis=0)

        #Second stage of CDMA encoding, sum of walsh encoded data
        signal_to_transmit = sum(spread_matrix)
        #Third stage of CDMA encoding, multiply spreaded sum with PN sequence
        [I,Q] = PN(max_data_len*WALSH_CODE_SIZE)
        pn_sequence = I+Q*1j
        signal_to_transmit = np.multiply(signal_to_transmit, pn_sequence.T)
        #END ENCODING

        #START DECODING
        signal_to_recieve = signal_to_transmit
        #Transposing pn_sequence is not done by value copy, must reset
        pn_sequence = I+Q*1j
        #Multiply recieved signal by complex conjugate transpose of pn_sequence
        signal_to_recieve = np.multiply(signal_to_recieve, np.asmatrix(pn_sequence).H)
        signal_to_recieve = np.ravel(signal_to_recieve)

        #pre allocate decoded data. Rows of matrix correspond to channels
        user_decoded_data = np.empty([CHANNELS,max_data_len])
        block_count = 0
        #Perform correlation for each sample chunk of walsh code size
        for i in range(0, (WALSH_CODE_SIZE*max_data_len)-1, WALSH_CODE_SIZE):
            user_data = np.empty([CHANNELS,max_data_len])
            for channel in range(0,CHANNELS):
                channel_code = codes[:, channel]
                chunk = []
                user_data_count = 0

                #Handling end of data case
                if((i+WALSH_CODE_SIZE) > WALSH_CODE_SIZE*max_data_len):
                    chunk = signal_to_recieve[i:-1]
                else:
                    chunk = signal_to_recieve[i:(i+WALSH_CODE_SIZE)-1]
                #Have chunk of data now do walsh code demuxing
                correlation_factor = 0
                for j in range(0,WALSH_CODE_SIZE-1):
                    correlation_factor = correlation_factor+(chunk[j]*channel_code[j])
                #now have correlation factor, which will determine original data sample
                if(correlation_factor > 0):
                    user_decoded_data[channel][block_count] = 1
                else:
                    user_decoded_data[channel][block_count] = 0

            block_count = block_count+1

        for i in range(0, len(decoded_list)):

            #Need to remove signature from end of packet
            #Signature in form [DATA, 1,1,1, 0....]
            edited_packet = remove_end_packet_frame(user_decoded_data[i])
            conv_str = convert_to_byte_array(edited_packet)
            #Try except for converting empty channels to asii equivalent
            #Would be easier to just check for conv_str length but ehhh
            try:
                d = int(str(conv_str),2)
                d = binascii.unhexlify('%x'% d)
                decoded_list[i].SetValue(d)
                empty_channel_list[i].SetValue(False)

            except ValueError:
                decoded_list[i].SetValue("")
                empty_channel_list[i].SetValue(True)

            #We are at pilot channel
            if(i == 0):
                decoded_list[0].SetValue(convert_to_byte_array(user_decoded_data[0]))
                empty_channel_list[0].SetValue(False)

class TransmitterPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.SetBackgroundColour(wx.WHITE)

        font = wx.Font(18, wx.ROMAN, wx.ITALIC, wx.NORMAL)
        font2 = wx.Font(12, wx.ROMAN, wx.NORMAL, wx.NORMAL)
        font3 = wx.Font(10, wx.ROMAN, wx.NORMAL, wx.FONTWEIGHT_BOLD)

        sizer = wx.BoxSizer(wx.VERTICAL)

        transmitter_text = wx.StaticText(self, label="Transmitter")
        transmitter_text.SetFont(font)
        sizer.Add(transmitter_text,0, wx.ALL | wx.CENTER, 10)

        for i in range(1,CHANNELS):

            row_layout = wx.wx.BoxSizer(wx.HORIZONTAL)
            sizer.Add(row_layout, 0, wx.ALL|wx.CENTER, 10)
            sizer.AddSpacer(10)

            #Static Text Label
            channel_text = wx.StaticText(self,label="Channel: {}".format(i))
            channel_text.SetFont(font3)
            row_layout.Add(channel_text, 0, wx.ALL | wx.CENTER, 10)

            channel_input = wx.TextCtrl(self, wx.EXPAND, style=wx.TE_PROCESS_ENTER)
            channel_input.SetMinSize((300,50))
            channel_input.Bind(wx.EVT_TEXT_ENTER, GetData)
            input_list.append(channel_input)
            row_layout.Add(channel_input, 0, wx.ALL | wx.CENTER, 10)

            gen_data = wx.CheckBox(self, label="Gen Data")
            checkbox_gen_data_list.append(gen_data)
            row_layout.Add(gen_data,0, wx.ALL | wx.CENTER, 10)

        self.SetSizer(sizer)


class RecieverPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.SetBackgroundColour(wx.WHITE)

        font = wx.Font(18, wx.ROMAN, wx.ITALIC, wx.NORMAL)
        font2 = wx.Font(12, wx.ROMAN, wx.NORMAL, wx.NORMAL)
        font3 = wx.Font(10, wx.ROMAN, wx.NORMAL, wx.FONTWEIGHT_BOLD)

        sizer = wx.BoxSizer(wx.VERTICAL)

        reciever_text = wx.StaticText(self, label="Reciever")
        reciever_text.SetFont(font)
        sizer.Add(reciever_text,0, wx.ALL | wx.CENTER, 10)

        for i in range(0, CHANNELS):
            row_layout = wx.wx.BoxSizer(wx.HORIZONTAL)
            sizer.Add(row_layout, 0, wx.ALL|wx.CENTER, 0)
            sizer.AddSpacer(10)
            sizer.AddSpacer(10)

            chan_text = wx.StaticText(self,label="Channel: {}".format(i))
            chan_text.SetFont(font3)
            row_layout.Add(chan_text, 0, wx.ALL | wx.CENTER, 10)

            channel_input = wx.TextCtrl(self, wx.EXPAND, style=wx.TE_PROCESS_ENTER)
            channel_input.SetMinSize((300,50))
            decoded_list.append(channel_input)
            row_layout.Add(channel_input, 0, wx.ALL | wx.CENTER, 10)

            empty_chan = wx.CheckBox(self, label="ch empty")
            empty_channel_list.append(empty_chan)
            row_layout.Add(empty_chan,0, wx.ALL | wx.CENTER, 10)

        self.SetSizer(sizer)

class TopPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.SetBackgroundColour(wx.WHITE)
        #FONTS LIBRARY
        font = wx.Font(18, wx.ROMAN, wx.NORMAL, wx.NORMAL)
        font2 = wx.Font(12, wx.ROMAN, wx.NORMAL, wx.NORMAL)

        parent_sizer = wx.BoxSizer(wx.VERTICAL)
        parent_sizer.AddSpacer(10)

        reciever_text = wx.StaticText(self, label="A simple CDMA implementation")
        reciever_text.SetFont(font)
        parent_sizer.Add(reciever_text,0, wx.ALL | wx.CENTER, 10)

        author_text = wx.StaticText(self, label="Created by Lachlan Page")
        author_text.SetFont(font2)
        parent_sizer.Add(author_text,0, wx.ALL | wx.CENTER, 25)

        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        parent_sizer.Add(main_sizer, 0, wx.EXPAND)
        #Panel on LHS
        transmitter_panel = TransmitterPanel(self)
        main_sizer.Add(transmitter_panel, 1, wx.EXPAND)
        #Panel on RHS
        reciever_panel = RecieverPanel(self)
        main_sizer.Add(reciever_panel, 1, wx.EXPAND)

        self.SetSizer(parent_sizer)

class MainWindow(wx.Frame):
    def __init__(self, parent, id, title):
        #setup
        wx.Frame.__init__(self, parent, wx.ID_ANY, title = title, size = (550,300))

        self.top_panel = TopPanel(self)
        #Send data every timer_interval
        timer_interval = 400
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, GetData, self.timer)
        self.timer.Start(timer_interval)

if __name__ == '__main__':
    app = wx.PySimpleApp(False)
    app.frame = MainWindow(None, wx.ID_ANY, "CDMA Transmitter & Reciever")
    app.frame.Show()
    app.MainLoop()
