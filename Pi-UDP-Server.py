import socket, os, time, select
from datetime import datetime

#Global variables
PORT=5007
IP=""
MAC=""
entryNum=0
devicelog=[]
currentTime=0
dayTime=0
lastScheduleCheckTime=0

def refreshLocalIP():
    global IP, MAC
    gw = os.popen("ip -4 route show default").read().split() #Some work here required to track network accessibility status
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((gw[2], 0))
    ipAddr = s.getsockname()[0]
    IP=ipAddr
    try:
        MACstring=open('/sys/class/net/eth0/address').read() #Device selected here - may also want wlan0 instead of eth0
    except:
        MACstring='00:00:00:00:00:00'
    MAC=MACstring[0:17]
    print("Local IP is",IP," with MAC of" + MAC)

def appraiseDeviceLog():
    global deviceLog, IP, MAC
    nowTime=str(currentTime)
    if os.path.isfile("deviceLog.txt")==0:
        log=open("deviceLog.txt","a") #create if doesn't exist
        registerLines='0,0,'+IP+','+MAC+',1,1,'+nowTime+',Main Server\n'\
            '1,1,'+IP+','+MAC+','+nowTime+',1,'+nowTime+',Date time\n'\
            '2,2,'+IP+','+MAC+','+str(dayTime)+',1,'+nowTime+',Day time\n'\
            '3,3,'+IP+','+MAC+','+'1'+',1,'+nowTime+',Network access\n'\
            '4,4,'+IP+','+MAC+','+'1'+',1,'+nowTime+',Internet access\n'\
            '5,5,'+IP+','+MAC+','+str(123)+',1,'+nowTime+',Solar azimuth\n'\
            '6,6,'+IP+','+MAC+','+str(23)+',1,'+nowTime+',Solar altitude\n'\
            '7,7,'+IP+','+MAC+','+str(3)+',1,'+nowTime+',Lunar azimuth\n'\
            '8,8,'+IP+','+MAC+','+str(13)+',1,'+nowTime+',Lunar altitude\n'\
            '9,9,'+IP+','+MAC+','+str(9)+',1,'+nowTime+',Sun rise/set\n'
        log.write(registerLines)
        log.close()
        print("deviceLog.txt file created.")
    with open("deviceLog.txt") as textFile:
        deviceLog = [line.split('\n')[0] for line in textFile]
    #print (deviceLog)
    

#First run routine to show last logged items and IP addy
def appraiseMsgLog():
    global entryNum
    if os.path.isfile("msgLog.txt")==0:
        log=open("msgLog.txt","a") #create if doesn't exist
        log.close()
        print("New msgLog.txt file created.")    
    with open("msgLog.txt") as textFile:
        readLines = [line.split('\n')[0] for line in textFile]
    if len(readLines)==1 or len(readLines)==0:  #Could be reviewed for accuracy------------------
        entryNum=0
    else:
        if len(readLines)==2:
            #print("1 line")
            lastLine=readLines[0][:-1]
            firstLine=readLines[0][:-1]
        elif len(readLines)==3:
            #print("2 lines")
            lastLine=readLines[1][:-1]
            firstLine=readLines[0][:-1]
        else:
            #print("more lines")
            lastLine=readLines[-1][:-1]
            firstLine=readLines[0][:-1]
        print("First line stored: " + firstLine)
        print("Last line stored: " + lastLine)
        entryNum=int(lastLine.split(',')[0])
    

def checkForMessage(): #Primes a message if available
    global sock
    sockReady=select.select([sock],[],[],0.1) #[True,True]
    if sockReady[0]:
        print("")
        #print("Socket received data")
        data, addr=sock.recvfrom(256) #Receiving the data from the buffer
        addr=str(addr) #convert to string
        pos2=addr.index("'",3)
        devIP=addr[2:pos2] #trim 4 digit port number
        data=str(data) #change to string
        print("-- Raw incoming message:",data)
        message=data[2:-1]+','+devIP #strip the b character - Used to have the devIP in as well
        processMessage(message)
        

def processMessage(data):
    #Split the message
    if data.count(',')==0:
        print("No commas in received message: " + data)
        return #exits the function
    elif data.count(',')==3: #breaking out the message
        msgType,devID,msg,devIP=data.split(",") #form at is {IP,type,ID,message}
        logMsg(msgType,devID,msg)
    else:
        print("Invalid message recieved: " + data)
        return #exits the function
    #Take action on the messages
    if msgType=="0": #Register
        regDevice(devID,msg,devIP,'Newly regisered device')
    elif msgType=="12": #Scheduled message without
        actionListComparison(devID)
    else:
        if getIpFromId(devID)=="Empty IP":
            print("Message not processed since device ID",devID,"is not registered.")
        else:
            logRecent(devID,msg,devIP)
            actionListComparision(devID)
        

def actionListComparision(devID):
    with open("actionList.txt") as textFile:
        lines = [line.split('\n')[0] for line in textFile]
    for i in range(0,len(lines)):
        #print(lines[i][:-1])
        actionSplit=lines[i][:-1].split(":")
        #print(actionSplit)
        #print(actionSplit[1].split(",")[0])
        if devID==actionSplit[1].split(",")[0]:
            conditionSplit=actionSplit[2].split(";")
            #print(conditionSplit)
            meetsCondition=True
            for condition in conditionSplit:
                condElements=condition.split(",")
                lastValue=getLastValue(condElements[1])
                #if condition[0]=="0" #Match anything doesn't need logic because always true
                if condition[0]=="1": #Equals
                    #print("equal triggered",condElements[2],getLastValue(condElements[1]))
                    if not condElements[2]==lastValue:
                        meetsCondition=False
                elif condition[0]=="2": #Not equal
                    #print("equal triggered",condElements[2],getLastValue(condElements[1]))
                    if condElements[2]==lastValue:
                        meetsCondition=False
                elif condition[0]=="3": #less than
                    if lastValue.isdigit():
                        if condElements[2].isdigit():
                            #print(int(lastValue),int(condElements[2]))
                            if not int(lastValue)<int(condElements[2]):
                                meetsCondition=False
                        else:
                            meetsCondition=False
                            print("Action list item",actionSplit[0],"does not have a valid int for less than comparison")
                    else:
                        meetsCondition=False
                        print("Last value for device",condElements[1],"is not a valid int for less than comparison")
                elif condition[0]=="4": #less than or equal
                    if lastValue.isdigit():
                        if condElements[2].isdigit():
                            #print(int(lastValue),int(condElements[2]))
                            if not int(lastValue)<=int(condElements[2]):
                                meetsCondition=False
                        else:
                            meetsCondition=False
                            print("Action list item",actionSplit[0],"does not have a valid int for less than or equal to comparison")
                    else:
                        meetsCondition=False
                        print("Last value for device",condElements[1],"is not a valid int for less than or equal to comparison")
                elif condition[0]=="5": #greater than
                    if lastValue.isdigit():
                        if condElements[2].isdigit():
                            #print(int(lastValue),int(condElements[2]))
                            if not int(lastValue)>int(condElements[2]):
                                meetsCondition=False
                        else:
                            meetsCondition=False
                            print("Action list item",actionSplit[0],"does not have a valid int for greater than comparison")
                    else:
                        meetsCondition=False
                        print("Last value for device",condElements[1],"is not a valid int for greater than comparison")
                elif condition[0]=="6": #greater than or equal
                    if lastValue.isdigit():
                        if condElements[2].isdigit():
                            #print(int(lastValue),int(condElements[2]))
                            if not int(lastValue)>=int(condElements[2]):
                                meetsCondition=False
                        else:
                            meetsCondition=False
                            print("Action list item",actionSplit[0],"does not have a valid int for greater than or equal to comparison")
                    else:
                        meetsCondition=False
                        print("Last value for device",condElements[1],"is not a valid int for greater than or equal to comparison")
            if meetsCondition:
                if actionSplit[3].count(';')==0:
                    print('- Rule number',actionSplit[0],'triggered with a single action.')
                    to=actionSplit[3].split(',')
                    sendUdp('11',to[0],to[1])
                else:
                    print('- Rule number',actionSplit[0],'triggered with multiple actions.')
                    actions=actionSplit[3].split(';')
                    for j in range(0,len(actions)):
                        to=actions[j].split(',')
                        sendUdp('11',to[0],to[1])

def sendUdp(msgType,toID,msg):
    global sock
    #print(toID)
    toIP=getIpFromId(toID)
    if toIP=="Empty IP":
        print("No IP available for sending UDP to",toID)
    else:
        sendData=toID + "," + msg
        sendthis=sendData.encode('utf-8') #Changing type
        #print(toIP,PORT)
        sock.sendto(sendthis,(toIP,PORT))
        print("-- Sent UDP message:", sendData)
        logMsg(msgType,toID,msg)

def getIpFromId(devID):
    global deviceLog
    outIP = "Empty IP" #No IP by default
    for line in deviceLog:
        #print("Finding IP for this dev:",devID,line.split(',')[0])
        if line.split(',')[0]==devID:
            outIP=line.split(",")[2]
            break
    #print('Returned this IP from input ID:',devID,outIP)
    return outIP;

def getMacFromIP(devIP):
    global deviceLog
    outMAC = "Empty Mac" #No IP by default
    for line in deviceLog:
        #print("Finding IP for this dev:",devID,line.split(',')[0])
        if line.split(',')[2]==devIP:
            outMAC=line.split(",")[3]
            break
    #print('Returned this MAC from input IP:',devIP,outMAC)
    return outMAC;

def getLastValue(devID):
    global deviceLog
    output="Empty value"
    for line in deviceLog:
        logSplit=line.split(",")
        #print("Getting last value: ",logSplit[0],devID)
        if logSplit[0]==devID:
            output=logSplit[4];
    #print('Returned this Value from input ID:',devID,output)
    return output;

def logMsg(msgType,devID,msg):
    global entryNum
    entryNum = entryNum + 1
    logData=str(entryNum) + "," + str(currentTime) + "," + msgType + "," + devID + "," + msg + "\n"
    log=open("msgLog.txt","a")
    log.write(logData)
    log.close()
    print("--- Message logged: " + logData[:-1])

def logRecent(devID,msg,devIP):
    global deviceLog
    for i in range(0,len(deviceLog)):
        logSplit=deviceLog[i].split(",")
        if logSplit[0]==devID:
            deviceLog[i]=logSplit[0]+','+logSplit[1]+','+devIP+','+logSplit[3]+','+msg+','+'1'+','+str(currentTime)+ ',' + logSplit[7]
            print("Updated a registered device's recent state:", logSplit[0])
            if logSplit[5]=='0':
                print("Offline device has returned to the network with ID: ", devID)
            if logSplit[2]!=devIP:
                #print(logSplit[2],"  ",devIP)
                print("IP address has changed for the device with ID: ", devID)
    log=open("deviceLog.txt","w")
    for line in deviceLog:
        log.write(line + '\n')
    log.close()
    #print('Full device log:',deviceLog)

def regDevice(devID,msg,devIP,devName):
    global deviceLog
    noMatch = True
    for i in range(0,len(deviceLog)):
        logSplit=deviceLog[i].split(",")
        if logSplit[0]==devID:
            if logSplit[2]==devIP:
                print("Registration logged as existing device for this device:",devID)
                deviceLog[i]=devID+','+msg+','+devIP+','+logSplit[3]+','+msg+','+'1'+','+str(currentTime) + ',' + logSplit[7]
                #More can be put here to distinguish the difference between new devices and existing devices. also on/offline statuses
            else:
                print("Logged this device with a new IP:", devID)
                deviceLog[i]=devID+','+msg+','+devIP+','+'No mac yet'+','+msg+','+'1'+','+str(currentTime) + ',' + devName
            noMatch = False
    if noMatch:
        deviceLog.append(devID+','+msg+','+devIP+','+'No mac yet'+','+msg+','+'1'+','+str(currentTime) + ',' + devName)
        print("Logged a new unique device with devID:", devID)
    log=open("deviceLog.txt","w")
    for line in deviceLog:
        log.write(line + '\n')
    log.close()

def setTimes():
    global currentTime, dayTime
    curTime=datetime.now()
    dayTime=int((curTime-curTime.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())
    currentTime=int(time.time())
    

def checkScheduledEvents():
    global currentTime,lastScheduleCheckTime
    if currentTime>lastScheduleCheckTime:
        with open("scheduledActions.txt") as textFile:
            readLines = [line.split('\n')[0] for line in textFile]
        i=0
        deleteFlag=False
        while i <len(readLines):
            scheduleTime,msgType,devID,msg=readLines[i].split(',')
            if int(scheduleTime)==currentTime: #Execute an event if the time is right
                print("")
                print("-- Scheduled action triggered:",readLines[i])
                combined=msgType+','+devID+','+msg+','+IP                
                processMessage(combined)
                del readLines[i]
                deleteFlag=True
            elif int(scheduleTime)<currentTime: #if an old event was added to list
                del readLines[i]
                deleteFlag=True
            else:
                i=i+1
        if deleteFlag:
            cal=open("scheduledActions.txt",'w')
            for line in readLines:
                cal.write(line+'\n')
        lastScheduleCheckTime=currentTime
        


#NO MORE MODULES BELOW HERE ----------- SETUP --------------------------------------

#Setup lines 
setTimes()
refreshLocalIP()

#File presence checks
if os.path.isfile("scheduledActions.txt")==0:
    log=open("scheduledActions.txt","a") #create if doesn't exist
    log.close()
    print("scheduledActions.txt file created.")
if os.path.isfile("actionList.txt")==0:
    log=open("actionList.txt","a") #create if doesn't exist
    log.close()
    print("actionList.txt file created.")
appraiseDeviceLog()
appraiseMsgLog()
logMsg('0','0','0') #To log when a reset hapens

#General UDP setup
sock=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('',PORT))
print("---- Now receiving on IP " + str(IP) + " at port " + str(PORT) + " ----")
#log msg to show server is online


#Log what is read and occasionally respond
while True:
    
    checkForMessage()
    setTimes()
    checkScheduledEvents()

