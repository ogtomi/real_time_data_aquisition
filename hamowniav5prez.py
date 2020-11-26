import threading
import socket
import datetime
import os
from tkinter import *
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.animation as animation
from matplotlib import style
import matplotlib.pyplot as plt

# saving path
path_main = "F:\dataaq\POMIARY"
path = path_main

# CONNECTION SPECS
UDP_IP = "192.168.0.37"              #IP_PC
UDP_PORT = 1234                      #PORT_PC
UDP_IP_TARGET_1 = "192.168.0.5"      #IP_ENC_1
UDP_PORT_TARGET_1 = 4321             #PORT_ENC_1
# UDP_IP_TARGET_2 = "192.168.1.6"      #IP_ENC_2
# UDP_PORT_TARGET_2 = 3210             #PORT_ENC_2
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

# PLOTS SPEC
matplotlib.use("TkAgg")
style.use('dark_background')
fig = Figure()
ax1 = fig.add_subplot()

# real time measured values
meas_t = 0.0
meas_n = 0.0
meas_T = 0.0
meas_i = 0.0
meas_u = 0.0

plot_t = 20  # visible plot time [s]
plot_dt = 500  # plot refresh period [ms]
plot_data_length = int(1000/plot_dt * plot_t)  # plot max list length

# X AXIS SPec
x_list = [x for x in range(0,plot_t+1, int(plot_t/20)+1)]
x_list_show = [0, plot_t]
a = 0

# plot lists
plot_u_list = []
plot_t_list = []
plot_n_list = []
plot_T_list = []
plot_i_list = []
plot_u_list = []
counter = 0

# ACQUISITION
loop = False
flag = False
clear_plot = False
reading_loop_dt = 0.1       #[s]

def start_akwizycja():
    global loop, counter, clear_plot
    print("start")
    counter = 0
    loop = True
    clear_plot = True
    make_file()
    sock.sendto(bytes("start", "utf-8"), (UDP_IP_TARGET_1, UDP_PORT_TARGET_1))
    reading_loop()

def stop_akwizycja():
    global path, loop, flag
    print("stop")
    sock.sendto(bytes("stop", "utf-8"), (UDP_IP_TARGET_1, UDP_PORT_TARGET_1))
    loop = False
    path = path_main
    flag = False

def make_file():
    global path

    time = datetime.datetime.now()
    if time.day < 10:
        day = "0" + str(time.day)
    else:
        day = str(time.day)
    if time.month < 10:
        month = "0" + str(time.month)
    else:
        month = str(time.month)

    dir_name = day + "_" + month + "_" + str(time.year)

    if time.minute < 10:
        file_name = str(time.hour) + "_0" + str(time.minute) + "_" + str(time.second)
    else:
        file_name = str(time.hour) + "_" + str(time.minute) + "_" + str(time.second)

    if time.hour < 10:
        file_name = "0" + file_name

    path = path + "/{}/{}.txt".format(dir_name, file_name)

    if os.path.exists(os.path.dirname(path)):
        pass
    else:
        os.makedirs(os.path.dirname(path))

    open(path, "w").close()

def reading_loop():
    global meas_t, meas_n, meas_T, meas_i, meas_u, flag

    if loop:
        s1, s2, t = packet_receive()
        if t == 0:
            flag = True
        if flag:
            save_to_file(s1, s2, t)
            meas_t = t/10               #[s]
            meas_n = s1[-1]
            meas_T = s2[-1]
            # meas_i = s3[-1]
            # meas_u = s4[-1]
            meas_i = 100
            meas_u = 200
        timer = threading.Timer(reading_loop_dt, reading_loop)
        timer.start()

def packet_receive():
    packet, addr = sock.recvfrom(1024)
    s1 = []
    s2 = []
    t = ((packet[-2] << 8) | packet[-1])
    for i in range(0, len(packet) - 2, 4):
        s1.append((packet[i] << 8) | packet[i + 1])
        s2.append((packet[i + 2] << 8) | packet[i + 3])
    return s1, s2, t

def save_to_file(s1, s2, t):
    f = open(path, "a")  # saving data to file
    for i in range(len(s1)):
        line = "{} {} {}\n".format(t, s1[i], s2[i])
        f.write(line)
    f.close()

# CREATING PLOT WINDOWS
def plot_data(figure, window):
    canvas = FigureCanvasTkAgg(figure, master=window)
    canvas.draw()
    canvas.get_tk_widget().pack(side=BOTTOM, fill=BOTH, expand=True)
    toolbar = NavigationToolbar2Tk(canvas, window)
    toolbar.update()
    canvas._tkcanvas.pack(side=TOP, fill=BOTH, expand=True)

class ResizingCanvas(Canvas):
    def __init__(self, parent, **kwargs):
        Canvas.__init__(self, parent, **kwargs)
        self.bind("<Configure>", self.on_resize)
        self.height1 = self.winfo_reqheight() - 100
        self.height2 = self.winfo_reqheight()
        self.height3 = self.height2 - self.height1
        self.width = self.winfo_reqwidth()

        # MAIN PLOT WINDOW
        self.plot_window = Frame(self, height=self.height1, width=self.width, bg='black')
        self.plot_window.pack(side=TOP, fill=BOTH, expand=True)

        # BUTTONS WINDOW
        self.button_window = Frame(self, height=self.height3, width=self.width, bg='black')
        self.button_window.pack(side=BOTTOM, fill=BOTH, expand=True)

        self.setTorqueText = StringVar()
        self.setSpeedText = StringVar()
        self.setTorqueLimitText = StringVar()
        self.setSpeedLimitText = StringVar()
        self.calc_acc = 0.0
        self.max_speed = 1500
        self.max_torque = 200
        self.setDAQ_TimeText = StringVar()

        self.meas_torque = 0.0
        self.meas_speed = 0.0
        self.meas_voltage = 0.0
        self.meas_current = 0.0
        self.set_torque = 0.0
        self.set_speed = 0.0

        self.set_speed_text = "Zadana prędkość: %.1f [obr/min]" % 0
        self.set_torque_text = "Zadany moment: %.1f [Nm]" % 0
        self.meas_speed_text = "Pomiar prędkości: %.1f [obr/min]" % 0
        self.meas_torque_text = "Pomiar momentu: %.1f [Nm]" % 0
        self.meas_power_text = "Pomiar mocy: %.3f [kW]" % 0
        self.meas_Current_text = "Pomiar prądu %.1f [A]" % 0
        self.meas_Voltage_text = "Pomiar napiecia %.1f [V]" % 0

        # variables to turn plots on/ off
        self.if_plot_speed = False
        self.if_plot_torque = False
        self.if_plot_voltage = False
        self.if_plot_current = False

        self.Loop = False
        self.init_menu()
        plot_data(fig, self.plot_window)

    def init_menu(self):
        # PLOT CHECKBUTTONS
        self.speed_box = Checkbutton(self, background="black", borderwidth=5, foreground="grey", font="Helvetica 8", command=self.SpeedToggle)
        self.torque_box = Checkbutton(self, background="black", borderwidth=5, foreground="grey", font="Helvetica 8", command=self.TorqueToggle)
        self.current_box = Checkbutton(self, background="black", borderwidth=5, foreground="grey", font="Helvetica 8", command=self.SpeedTorqueToggle)
        self.voltage_box = Checkbutton(self, background="black", borderwidth=5, foreground="grey", font="Helvetica 8", command=self.SpeedTorqueToggle)

        self.mode0 = 0
        self.mode1 = 0
        self.mode2 = 1
        self.mode3 = 0

        # FIRST COLUMN (control testbench, set values)
        self.label0 = Label(self, text="Załącz/Wyłącz", font=("Helvetica", 10), background="black", foreground="grey")
        self.check0 = Checkbutton(self, width=10, text="Wyłącz", background="black", borderwidth=5, foreground="grey", font="Helvetica 10", indicatoron=False, command=self.OnOffToggle)

        self.label1 = Label(self, text="Sterowanie", font=("Helvetica", 10), background="black", foreground="grey")
        self.check1 = Checkbutton(self, width=10, text="prędkością", background="black", borderwidth=5, foreground="grey", font="Helvetica 10", indicatoron=False, command=self.SpeedTorqueToggle)

        self.label2 = Label(self, text="Praca", font=("Helvetica", 10), background="black", foreground="grey")
        self.check2 = Checkbutton(self, width=10, text="silnikowa", background="black", borderwidth=5, foreground="grey", font="Helvetica 10", indicatoron=False, command=self.MotorBreakToggle)

        self.label3 = Label(self, text="Kierunek obrotów", font=("Helvetica", 10), background="black", foreground="grey")
        self.check3 = Checkbutton(self, width=10, text="w prawo", background="black", borderwidth=5, foreground="grey", font="Helvetica 10", indicatoron=False, command=self.RightLeftToggle)
        self.sendCMD = Button(self, width=20, text="Zadaj", command=self.controlCMD, background="black", borderwidth=5, foreground="grey", font="Helvetica 10")

        # SECOND COLUMN (setting values, entries)
        self.label10 = Label(self, text="Prędkość zadana:", font=("Helvetica", 10), background="black", foreground="grey")
        self.entrySpeed = Entry(self, textvariable=self.setSpeedText, width=7, background="black", borderwidth=5, foreground="grey", font="Helvetica 8", justify=RIGHT)
        self.label20 = Label(self, text="[obr/min]", font=("Helvetica", 10), background="black", foreground="grey")

        self.label11 = Label(self, text="Moment zadany:", font=("Helvetica", 10), background="black", foreground="grey")
        self.entryTorque = Entry(self, textvariable=self.setTorqueText, width=7, background="black", borderwidth=5, foreground="grey", font="Helvetica 8", justify=RIGHT)
        self.label21 = Label(self, text="[Nm]", font=("Helvetica", 10), background="black", foreground="grey")

        self.label12 = Label(self, text="Limit prędkości:", font=("Helvetica", 10), background="black", foreground="grey")
        self.entrySpeedLimit = Entry(self, textvariable=self.setSpeedLimitText, width=7, background="black", borderwidth=5, foreground="grey", font="Helvetica 8", justify=RIGHT)
        self.label22 = Label(self, text="[obr/min]", font=("Helvetica", 10), background="black", foreground="grey")

        self.label13 = Label(self, text="Limit momentu:", font=("Helvetica", 10), background="black", foreground="grey")
        self.entryTorqueLimit = Entry(self, textvariable=self.setTorqueLimitText, width=7, background="black", borderwidth=5, foreground="grey", font="Helvetica 8", justify=RIGHT)
        self.label23 = Label(self, text="[Nm]", font=("Helvetica", 10), background="black", foreground="grey")

        self.label14 = Label(self, text="Czas rejestracji:", font=("Helvetica", 10), background="black", foreground="grey")
        self.entryDAQ_Time = Entry(self, textvariable=self.setDAQ_TimeText, width=7, background="black", borderwidth=5, foreground="grey", font="Helvetica 8", justify=RIGHT)
        self.label24 = Label(self, text="[s]", font=("Helvetica", 10), background="black", foreground="grey")

        # THIRD COLUMN (measured values)
        self.label_setSpeed = Label(self, foreground="grey", background="black", font="Helvetica 10")
        self.label_setTorque = Label(self, foreground="grey", background="black", font="Helvetica 10")
        self.label_measCurrent = Label(self, foreground="grey", background="black", font="Helvetica 10")
        self.label_measVoltage = Label(self, foreground="grey", background="black", font="Helvetica 10")
        self.label_measSpeed = Label(self, foreground="grey", background="black", font="Helvetica 10")
        self.label_measTorque = Label(self, foreground="grey", background="black", font="Helvetica 10")
        self.label_measPower = Label(self, foreground="grey", background="black", font="Helvetica 10")

        self.label_deltaTime = Label(self, foreground="grey", background="black", font="Helvetica 6")

        self.startSW = IntVar()
        self.check_startSW = Checkbutton(self, width=7, text="START", variable=self.startSW, background="black", borderwidth=5, foreground="red", font="Helvetica 16", indicatoron=False, command=self.StartToggle)

    # ON/OFF BUTTON CONTROL (testbench)
    def OnOffToggle(self):
        if self.mode0 == 0:
            self.check0.config(text="Włącz")  # zmiana tekstu
            self.mode0 = 1
        else:
            self.check0.config(text="Wyłącz")
            self.mode0 = 0

    # TORQUE/ SPEED CONTROL (testbench)
    def SpeedTorqueToggle(self):
        if self.mode1 == 0:
            self.check1.config(text="momentem")
            self.mode1 = 1
        else:
            self.check1.config(text="prędkością")
            self.mode1 = 0

    # GENERATOR/ ENGINE MODE (testbench)
    def MotorBreakToggle(self):
        if self.mode2 == 1:
            self.check2.config(text="prądnicowa")
            self.mode2 = 0
        else:
            self.check2.config(text="silnikowa")
            self.mode2 = 1

    # LEFT/ RIGHT REVS (testbench)
    def RightLeftToggle(self):
        if self.mode3 == 0:
            self.check3.config(text="w lewo")
            self.mode3 = 1
        else:
            self.check3.config(text="w prawo")
            self.mode3 = 0

    # SETTING VALUES IN ENTRY FIELDS
    def controlCMD(self):
        global registration_time

        # setting up input values in each entry field
        self.set_speed = float(self.entrySpeed.get())
        self.set_torque1 = float(self.entryTorque.get())
        registration_time = int(self.entryMeas_time.get())

    # START REGISTRATION BUTTON FUNC
    def StartToggle(self):
        if self.Loop == True:
            self.Loop = False
            stop_akwizycja()
        else:
            self.Loop = True
            start_akwizycja()

    # FUNCTIONS TO SWITCH PLOTS ON/ OFF
    def SpeedToggle(self):
        if self.if_plot_speed:
            self.if_plot_speed = False
        else:
            self.if_plot_speed = True

    def TorqueToggle(self):
        if self.if_plot_torque:
            self.if_plot_torque = False
        else:
            self.if_plot_torque = True

    def CurrentToggle(self):
        if self.if_plot_current:
            self.if_plot_current = False
        else:
            self.if_plot_current = True

    def VoltageToggle(self):
        if self.if_plot_voltage:
            self.if_plot_voltage = False
        else:
            self.if_plot_voltage = True

    # PLACEMENT
    def on_resize(self, event):
        # determine the ratio of old width/height to new width/height
        wscale = float(event.width) / self.width
        hscale = float(event.height - 200) / self.height1
        self.width = event.width
        self.height1 = event.height - 200
        self.height2 = event.height
        print(event.width)
        print(event.height)
        # resize the canvas
        self.config(width=self.width, height=self.height1)
        # rescale all the objects tagged with the "all" tag
        self.scale("all", 0, 0, wscale, hscale)

        # FIRST COLUMN --> controlling testbench
        self.label0.place(x=100, y=self.height2 - 150, anchor=NE)
        self.label1.place(x=100, y=self.height2 - 120, anchor=NE)
        self.label2.place(x=100, y=self.height2 - 90, anchor=NE)
        self.label3.place(x=100, y=self.height2 - 60, anchor=NE)
        self.check0.place(x=100, y=self.height2 - 150)
        self.check1.place(x=100, y=self.height2 - 120)
        self.check2.place(x=100, y=self.height2 - 90)
        self.check3.place(x=100, y=self.height2 - 60)
        self.sendCMD.place(x=15, y=self.height2 - 30)

        # SECOND COLUMN --> controlling testbench
        self.label10.place(x=320, y=self.height2 - 150, anchor=NE)
        self.label11.place(x=320, y=self.height2 - 120, anchor=NE)
        self.label12.place(x=320, y=self.height2 - 90, anchor=NE)
        self.label13.place(x=320, y=self.height2 - 60, anchor=NE)
        self.label14.place(x=320, y=self.height2 - 30, anchor=NE)
        self.entrySpeed.place(x=320, y=self.height2 - 150)
        self.entryTorque.place(x=320, y=self.height2 - 120)
        self.entrySpeedLimit.place(x=320, y=self.height2 - 90)
        self.entryTorqueLimit.place(x=320, y=self.height2 - 60)
        self.entryDAQ_Time.place(x=320, y=self.height2 - 30)

        # default values
        self.setTorqueText.set("0.0")
        self.setSpeedText.set("0.0")
        self.setTorqueLimitText.set("200")
        self.setSpeedLimitText.set("1500")
        self.setDAQ_TimeText.set("120")

        self.label20.place(x=375, y=self.height2 - 150)
        self.label21.place(x=375, y=self.height2 - 120)
        self.label22.place(x=375, y=self.height2 - 90)
        self.label23.place(x=375, y=self.height2 - 60)
        self.label24.place(x=375, y=self.height2 - 30)

        self.label_measSpeed.place(x=460, y=self.height2 - 150)
        self.label_measTorque.place(x=460, y=self.height2 - 120)
        self.label_measPower.place(x=460, y=self.height2 - 90)
        self.label_setSpeed.place(x=460, y=self.height2 - 60)
        self.label_setTorque.place(x=460, y=self.height2 - 30)

        self.label_measCurrent.place(x=680, y=self.height2 - 150)
        self.label_measVoltage.place(x=680, y=self.height2 - 120)

        # PLOT CHECHBUTTONS
        self.speed_box.place(x=437, y=self.height2 - 155)
        self.torque_box.place(x=437, y=self.height2 - 125)
        self.current_box.place(x=657, y=self.height2 - 155)
        self.voltage_box.place(x=657, y=self.height2 - 125)

        # initializing checkbuttons
        self.speed_box.select()     # selecting checkbutton to start plotting
        self.if_plot_speed = True
        # self.torque_box.select()
        # self.current_box.select()
        # self.voltage_box.select()

        self.check_startSW.place(x=self.width - 150, y=self.height2 - 60)

        self.label_setSpeed.config(text=self.set_speed_text)
        self.label_setTorque.config(text=self.set_torque_text)
        self.label_measCurrent.config(text=self.meas_Current_text)
        self.label_measVoltage.config(text=self.meas_Voltage_text)
        self.label_measSpeed.config(text=self.meas_speed_text)
        self.label_measTorque.config(text=self.meas_torque_text)
        self.label_measPower.config(text=self.meas_power_text)

# PLOT FUNCTION
def animate_all(i):
    global clear_plot
    global plot_t_list, plot_n_list, plot_T_list, plot_i_list, plot_u_list, counter
    global x_list

    # clearing the plot when start button is pressed
    if clear_plot:
        plot_t_list.clear()
        plot_n_list.clear()
        plot_T_list.clear()
        plot_i_list.clear()
        plot_u_list.clear()

        clear_plot = False

    if loop and flag:
        counter = counter + 1
        if counter <= plot_data_length:
            plot_t_list.append(meas_t)
            plot_n_list.append(meas_n)
        else:
            for iterator, value in enumerate(plot_t_list):
                if iterator > 0:
                    plot_t_list[iterator-1] = plot_t_list[iterator]
                    plot_n_list[iterator-1] = plot_n_list[iterator]

                    plot_t_list[iterator] = meas_t
                    plot_n_list[iterator] = meas_n

        ax1.clear()
        ax1.set_xlabel('Czas [s]')

        if plot_t_list[-1] > x_list[-1]:
            for x in range(len(x_list)-1):
                x_list[x] = x_list[x + 1]
            x_list[-1] = x_list[-1] + (x_list[-2]-x_list[-3])

        if win.if_plot_speed:
            ax1.plot(plot_t_list, plot_n_list, label='Prędkość obrotowa [rpm]', color='yellow')
            #ax1.plot(plot_t_list, plot_T_list, label='Moment obrotowy [Nm]', color='blue')
            #ax1.plot(plot_t_list, plot_i_list, label='Prąd [A], color='red')
            #ax1.plot(plot_t_list, plot_u_list, label='Napięcie [V], color='green')

        #ax1.yaxis.set_major_locator(plt.MultipleLocator(100))
        #ax1.yaxis.set_minor_locator(plt.MultipleLocator(25))

        # SETTING UP AXES
        ax1.set_xticks(x_list, minor=False)

        ax1.xaxis.grid(True, linewidth=1, linestyle='dashed')
        ax1.yaxis.grid(True, linewidth=1, linestyle='dashed', which='major')
        ax1.yaxis.grid(True, linewidth=0.5, linestyle='dotted', which='minor')

        ax1.legend(bbox_to_anchor=(0, 1.02, 1, .102), loc=3, ncol=5, borderaxespad=0)

# MAIN FUNCTION
root = Tk()
root.grid_rowconfigure(10, weight=1)
root.grid_columnconfigure(4, weight=1)
mainframe = Frame(root, bg='black', width=1320, height=850)
mainframe.pack(fill=BOTH, expand=YES)
win = ResizingCanvas(mainframe, width=1320, height=850, bg="black", highlightthickness=0)
win.pack(fill=BOTH, expand=YES)
root.title("Projekt zespołowy")
# root.resizable(width=FALSE, height=FALSE)
root.geometry('{}x{}'.format(1300, 820))

ani = animation.FuncAnimation(fig, animate_all, interval=plot_dt) # animating plot function in plot_dt intervals

root.mainloop()
