import win32com.client
import matplotlib.pyplot as plt
import numpy as np
# h = win32com.client.DispatchEx("LeCroy.XStreamDSO.1","192.168.131.45")
scope=win32com.client.Dispatch("LeCroy.ActiveDSOCtrl.1") #creates instance of the ActiveDSO control
scope.MakeConnection("IP:192.168.131.4") 

# scope.WriteString("BUZZ BEEP", 1)

waveform=scope.GetScaledWaveformWithTimes("C1", 1000000, 0) 
time = np.array(waveform[0])
amp = np.array(waveform[1])
# time = time * 1e9
print(f'Sampling rate: {(len(time)-1)/(time[-1]-time[0])}, Number of samples: {len(time)}.')
print(f'Time range:{time[0]} to {time[-1]}; Mean amptitude: {np.mean(amp)}')
fig, ax = plt.subplots()
ax.plot(time, amp)
ax.set_xlabel("time (ns)")
ax.set_ylabel("amplitude (V)")
plt.tight_layout()

plt.show()
# scope.WriteString("C1:VDIV .02",1)
# scope.WriteString("VBS app.Measure.ShowMeasure = true",1) #Automation command to show measurement table
# scope.WriteString("""VBS 'app.Measure.P1.ParamEngine="Mean" ' """,1) #Automation command to change P1 to Mean
# scope.WriteString("VBS? 'return=app.Measure.P1.Out.Result.Value' ",1) #Queries the P1 parameter
# value = scope.ReadString(80)#reads a maximum of 80 bytes
# print (value) #Print value to Interactive Window
scope.Disconnect()
a= 1