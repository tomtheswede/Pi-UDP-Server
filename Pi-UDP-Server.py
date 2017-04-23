import socket, os, time, select

#Global variables
PORT=5007
IP=""
sock=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('',PORT))
entryNum=0
resetCalCheck=True

#File presence checks
if os.path.isfile("deviceLog.txt")==0:
    log=open("deviceLog.txt","a") #create if doesn't exist
    log.close()
    print("deviceLog.txt file created.")
if os.path.isfile("calendarOutput.txt")==0:
    log=open("calendarOutput.txt","a") #create if doesn't exist
    log.close()
    print("calendarOutput.txt file created.")
if os.path.isfile("msgLog.txt")==0:
    log=open("msgLog.txt","a") #create if doesn't exist
    log.close()
    print("msgLog.txt file created.")
if os.path.isfile("actionList.txt")==0:
    log=open("actionList.txt","a") #create if doesn't exist
    log.close()
    print("actionList.txt file created.")

def getLocalIP():
    gw = os.popen("ip -4 route show default").read().split()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((gw[2], 0))
    ipAddr = s.getsockname()[0]
    print("Local IP is ",ipAddr)
    return ipAddr;

#First run routine to show last logged items and IP addy
def setupLog():
    global entryNum
    global IP
    print("Initiallizing...")
    IP=getLocalIP()    #Temporary removal for windows use
    regDevice('0','0',IP)
    with open("msgLog.txt") as textFile:
        readLines = [line.split('\n\n')[0] for line in textFile]
    if len(readLines)==1 or len(readLines)==0:
        print("Blank msgLog.txt found.")
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
    print("---- Now receiving on IP " + str(IP) + " at port " + str(PORT) + " ----")

def waitForMessage(): #Primes a message if available
    global sock
    sockReady=select.select([sock],[],[],0.1) #[True,True]
    if sockReady[0]:
        print("")
        print("Socket received data")
        message=getMessage()
    else:
        message=""
    return message;

def getMessage():
    global sock
    data, addr=sock.recvfrom(256) #Receiving the data from the buffer
    addr=str(addr) #convert to string
    pos2=addr.index("'",3)
    devIP=addr[2:pos2] #trim 4 digit port number
    data=str(data) #change to string
    message=data[2:-1]+','+devIP #strip the b character - Used to have the devIP in as well
    print("-- Raw incoming message:",data)
    #print("Output:",message)
    return message;

def scheduledEventGet():
    global resetCalCheck
    global IP
    message=""
    if int(time.strftime('%-S'))%25==0:
        resetCalCheck=True
    if int(time.strftime('%-S'))%26==0 and resetCalCheck==True: #trigger every remainder minutes
        resetCalCheck=False
        cal=open("CalendarOutput.txt",'r')
        lines=cal.readlines()
        cal.close
        for line in lines:
            calSplit=line.split(',')
            if calSplit[0][:-3]==time.strftime('%Y-%m-%d %H:%M'):
                resetCalCheck=True
                lines.remove(line)
                message=IP+','+line[20:-1]
                print("Scheduled message returned:",message)
                break
        cal=open("CalendarOutput.txt",'w')
        for line in lines:
            cal.write(line)
        cal.close()
    return message;

def processMessage(data):
    #Split the message
    msgType=""
    if data.count(',')==0:
        pass
    elif data.count(',')==3: #breaking out the message
        dataSplit=data.split(",") #form at is {IP,type,ID,message}
        msgType=dataSplit[0]
        devID=dataSplit[1]
        msg=dataSplit[2]
        devIP=dataSplit[3]
        logMsg(msgType,devID,msg)
    else:
        print("Invalid message recieved: " + data)
    #Take action on the messages
    if msgType=="0":
        regDevice(devID,msg,devIP)
    elif msgType!="0":
        logRecent(devID,msg,devIP)
        with open("actionList.txt") as textFile:
            lines = [line.split('\n\n')[0] for line in textFile]
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
                        sendUdp(to[0],to[1])
                    else:
                        print('- Rule number',actionSplit[0],'triggered with multiple actions.')
                        actions=actionSplit[3].split(';')
                        for j in range(0,len(actions)):
                            to=actions[j].split(',')
                            sendUdp(to[0],to[1])
        

def sendUdp(toID,msg):
    global sock
    #print(toID)
    toIP=getIpFromId(toID)
    if toIP=="":
        print("No IP available for sending to",toID)
    else:
        sendData=toID + "," + msg
        sendthis=sendData.encode('utf-8') #Changing type
        #print(toIP,PORT)
        sock.sendto(sendthis,(toIP,PORT))
        print("-- Sent message:", sendData)
        logMsg("5",toID,msg)
        
def getLastValue(devID):
    output="Empty"
    with open("deviceLog.txt") as textFile:
        lines = [line.split('\n\n')[0][:-1] for line in textFile]
    for line in lines:
        logSplit=line.split(",")
        #print("Getting last value: ",logSplit[0],devID)
        if logSplit[0]==devID:
            output=logSplit[4];
    return output;

def getLastValueTime(devID):
    output="Empty"
    with open("deviceLog.txt") as textFile:
        lines = [line.split('\n\n')[0][:-1] for line in textFile]
    for line in lines:
        logSplit=line.split(",")
        if logSplit[0]==devID:
            output=logSplit[6];
    return output;

def getIpFromId(devID):
    with open("deviceLog.txt") as textFile:
        lines = [line.split('\n\n')[0][:-1] for line in textFile]
    #print(lines)
    outIP = "" #No IP by default
    for line in lines:
        #print("Finding IP for this dev:",devID,line.split(',')[0])
        if line.split(',')[0]==devID:
            outIP=line.split(",")[2]
            break
    return outIP;

def logMsg(msgType,devID,msg):
    global entryNum
    entryNum = entryNum + 1
    logData=str(entryNum) + "," + time.strftime("%Y-%m-%d")+" "+time.strftime("%H:%M:%S") + "," + msgType + "," + devID + "," + msg + "\n"
    log=open("msgLog.txt","a")
    log.write(logData)
    log.close()
    print("--- Message logged: " + logData[:-1])

def logRecent(devID,msg,devIP):
    with open("deviceLog.txt") as textFile:
        lines = [line.split('\n\n')[0] for line in textFile]
    for i in range(0,len(lines)):
        logSplit=lines[i].split(",")
        if logSplit[0]==devID:
            lines[i]=logSplit[0]+','+logSplit[1]+','+devIP+','+logSplit[3]+','+msg+','+'online'+','+time.strftime("%Y-%m-%d")+' '+time.strftime("%H:%M:%S") + ',' + logSplit[7]
            print("Updated a registered device's recent state:", logSplit[0])
            if logSplit[5]=='offline':
                print("Offline device has returned to the network with ID: ", devID)
            if logSplit[2]!=devIP:
                print(logSplit[2],"  ",devIP)
                print("IP address has changed for the device with ID: ", devID)
    log=open("deviceLog.txt","w")
    for line in lines:
        log.write(line)
    log.close()

def regDevice(devID,msg,devIP):
    with open("deviceLog.txt") as textFile:
        lines = [line.split('\n\n')[0] for line in textFile]
    noMatch = True
    for i in range(0,len(lines)):
        logSplit=lines[i].split(",")
        if logSplit[0]==devID:
            if logSplit[2]==devIP and logSplit[5]=='online':
                print("Registration logged as existing device for this device:",devID)
                #More can be put here to distinguish the difference between new devices and existing devices. also on/offline statuses
            else:
                print("Logged this new or rarely seen device's registration state:", logSplit[0])
            lines[i]=devID+','+msg+','+devIP+','+'No mac'+','+msg+','+'online'+','+time.strftime("%Y-%m-%d")+' '+time.strftime("%H:%M:%S") + ',' + logSplit[7]
            noMatch = False
    log=open("deviceLog.txt","w")
    for line in lines:
        log.write(line)
    if noMatch:
        log.write(devID+','+msg+','+devIP+','+'No mac'+','+msg+','+'online'+','+time.strftime("%Y-%m-%d")+' '+time.strftime("%H:%M:%S")+','+'Un-named device'+'\n')
        print("Logged a new unique device with devID:", devID)
    log.close()


#Log what is read and occasionally respond
setupLog()
while True:
    msgData=waitForMessage()
    #if msgData=="":
    #    msgData=scheduledEventGet()

    #process data when available
    if msgData!="":
        processMessage(msgData)

