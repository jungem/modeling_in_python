import os
import random
import pandas as pd
import pickle
import numpy as np
import time
import copy
import itertools
# the following are .py files
import fileRelated as flr
import statfile
import visualize as vs
import modifyDf as mod_df
import schedule_students
import schedule_faculty
# for speed tests/debug
import functools
import cProfile

def clock(func): # from version 2, page 203 - 205 of Fluent Python by Luciano Ramalho
    @functools.wraps(func)
    def clocked(*args, **kwargs):
        t0 = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - t0
        arg_lst = [] #name = func.__name__
        if args:
            arg_lst.append(', '.join(repr(arg) for arg in args))
        if kwargs:
            pairs = ["%s=%r" % (k,w) for k, w in sorted(kwargs.items())]
            arg_lst.append(", ".join(pairs))
        arg_str = ", ".join(arg_lst)
        print("[%0.8fs] %s(%s) -> %r " % (elapsed, func.__name__, arg_str, result))
        return result
    return clocked

def convertToMin(timeStr):
    """convert time represnted in the following forms to minutes in a day, 
        this function is used to decode the schedule in terms of minutes
        1.) military time, xx:xx
        2.) time with Meridiem Indicator (AM/PM), xx:xxAM or xx:xxPM
    """
    meridiemIndicator = timeStr[-2:]
    if meridiemIndicator in ["AM", "PM"]: # check if Meridiem Indicator is included
        timeStr = timeStr[:-2]
    hours, minutes = [int(a) for a in timeStr.strip().split(":")]
    if meridiemIndicator == "PM": # if the period is PM, then add 12 hours to the time
            minutes += 60*12
    minutes+= hours*60
    return minutes

def findInTuple(val, itemList, index):
    """ iterate over the item_list and returns the first tuple with the same value"""
    for tup in itemList:
        if tup[index] == val: return tup
    return None

# change runtime to durration, change simulationN to iteration if its an available term
def runSimulation(pickleName, simulationN= 10, runtime = 200, debug=False):
    print(f"starting {simulationN} simulation for {runtime} steps")
    infA, infAF = "infected Asymptomatic", "infected Asymptomatic Fixed"
    infSM, infSS, rec = "infected Symptomatic Mild", "infected Symptomatic Severe", "recovered"
    infectedNumbers, massInfectionMoments, Istar, IstarTime  = [], [], [], []
    for _ in range(simulationN):
        model = flr.loadUsingDill(pickleName)
        print("loaded pickled object successfully")
        model.configureDebug(debug)
        model.startInfectionAndSchedule()
        model.initializeStoringParameter([infA, infAF, infSM, infSS, rec], steps=1)
        model.updateSteps(runtime)
        # end of simulation
        
        # get the time series data and store data "when 10% of the population is infected"
        dataDict = model.returnStoredInfo()
        massInfectionMoments.append(model.returnMassInfectionTime())
        model.final_check()
        # look at total infected over time, 
        infectedCount = np.zeros(len(dataDict["infected Asymptomatic"]))
        for state in [infA, infAF, infSM, infSS, rec]:
            print(str(state), dataDict[state])
            # get the last entry
            infectedCount+=np.array(dataDict[state])
        infectedNumbers.append(infectedCount[-1])
        temp_arr = infectedCount-np.array(rec)
        max_val = max(temp_arr)
        Istar.append(max_val)
        IstarTime.append(list(temp_arr).index(max_val))
    return (infectedNumbers, massInfectionMoments, Istar, IstarTime)

def simulateAndPlot(pickleNames, simulationN=10, runtime=200,labels=[], title="default title", debug=False, additionalName=""):
    massInfectionCounts, massInfectionTime, Istars, IstarsTime = [], [], [], []
    totalcases = len(pickleNames)
    t0 = time.time()
    for i, name in enumerate(pickleNames):
        print("*"*20)
        print(f"{(i)/totalcases*100}% cases finished")
        output = runSimulation(name,simulationN, runtime, debug=debug)
        massInfectionCounts.append(output[0])
        massInfectionTime.append(output[1])
        Istars.append(output[2])
        IstarsTime.append(output[3])
        print("infected numbers, mean", statfile.analyzeData(output[0])[0])
        print(output[1])
        print("time to 10% infected, mean", statfile.analyzeData(output[1])[0])

        print((f"took {time.time()-t0} time to finish{(i+1)/totalcases*100}%"))
    print(f"took {time.time()-t0} time to run {totalcases*simulationN} simulations")
    statfile.boxplot(massInfectionCounts, savePlt=True, saveName=additionalName+"totalNumberOfAgentsInfected.png",pltTitle=title, xlabel="model ver", ylabel="total number of infected agents", labels=labels)
    statfile.boxplot(massInfectionTime, savePlt=True, saveName=additionalName+"timeWhen10percentIsInfected.png", pltTitle=title, xlabel="model ver", ylabel="time when 10% was infected", labels=labels)
    statfile.boxplot(Istars, savePlt=True, saveName=additionalName+"Istar.png", pltTitle=title, xlabel="model ver", ylabel="max # in the infected stage at some time t", labels=labels)
    statfile.boxplot(IstarsTime, savePlt=True, saveName=additionalName+"IstarTime.png", pltTitle=title, xlabel="model ver", ylabel="t when max # was achieved", labels=labels)


def initializeSimulations(simulationControls, modelConfig, debug=True, pickleBaseName="pickleModel_"):
    """
        create the initialized model for each controlled experiment
    """
    createdNames = []
    for i, independentVariables in enumerate(simulationControls):
        pickleName = pickleBaseName+str(i)
        pickleName = flr.fullPath(pickleName+".pkl", "picklefile")
        if independentVariables[0][0] == None: # base model
            model = createModel(modelConfig, debug)
        else: # modify the data
            # the following copy of the model config is a shallow copy, 
            # if you want to modify a dict in the config, then use deep copy 
            configCopy = dict(modelConfig)
            for variableTup in independentVariables:
                configCopy[variableTup[0]] = variableTup[1]
            model = createModel(configCopy, debug)
        flr.saveUsingDill(pickleName, model)
        createdNames.append(pickleName)
    print("copy the following list and put in in as a parameter")
    print(createdNames)
    return createdNames

def createModel(modelConfig, debug=False):
    """
        calls the required function(s) to properly initialize the model and returns it

        Parameters:
        - modelConfig: a dictionary with  the attribute/property name and the value associated with it
    """
    model = AgentBasedModel()
    model.addKeys(modelConfig)
    model.loadBuilder("newBuilding.csv")
    model.loadAgent("newAgent.csv")
    model.generateAgentFromDf()
    model.initializeWorld()
    model.initializeAgents()
    model.startLog()
    model.configureDebug(debug)
    return model

def simpleCheck(modelConfig, days=100, visuals=True, name="default"):
    """
        runs one simulatons with the given config and showcase the number of infection and the graph
    """
    loadDill, saveDill = False, False
    pickleName = flr.fullPath("coronaModel.pkl", "picklefile")
    if not loadDill:
        model = createModel(modelConfig)
        if saveDill:
            flr.saveUsingDill(pickleName, model)
            # save an instance for faster loading
            return 0
    else:
        model = flr.loadUsingDill(pickleName)
        print("loaded pickled object successfully")
    model.configureDebug(False)
    # make schedules for each agents, outside of pickle for testing and for randomization
    model.startInfectionAndSchedule()
    model.initializeStoringParameter(
        ["susceptible","exposed", "infected Asymptomatic", 
        "infected Asymptomatic Fixed" ,"infected Symptomatic Mild", "infected Symptomatic Severe", "recovered", "quarantined"], 
                                        steps=1)
    model.printRelevantInfo()
    for _ in range(days):
        model.updateSteps(24)
        model.printRelevantInfo()
    model.final_check()
    model.printLog()
    tup = model.findDoubleTime()
    for description, tupVal in zip(("doublingTime", "doublingInterval", "doublingValue"), tup):
        print(description, tupVal)
    if visuals:
        fileformat = ".png"
        model.visualOverTime(False, True, name+fileformat)
        name+="_total"
        model.visualOverTime(True, True, name+fileformat)
    #model.visualizeBuildings()

def R0_simulation(modelConfig, R0Control, simulationN=10, debug=False, visual=False):
    sus, exp = "susceptible", "exposed"
    infA, infAF = "infected Asymptomatic", "infected Asymptomatic Fixed"
    infSM, infSS, rec = "infected Symptomatic Mild","infected Symptomatic Severe", "recovered"
    R0Values = []
    
    configCopy = dict(modelConfig)
    for variableTup in R0Control:
        configCopy[variableTup[0]] = variableTup[1]
    # base model
    model = createModel(configCopy)
    model.configureDebug(debug)
    if debug:
        model.startLog()
        max_limits = dict()
    
    days =4
    t1 = time.time()
    for i in range(simulationN):
        print("*"*20, "starting model")
        new_model = copy.deepcopy(model)    
        new_model.startInfectionAndSchedule()
        new_model.initializeR0()
        new_model.initializeStoringParameter([sus, exp, infA, infAF, infSM, infSS, rec], steps=1)
        for _ in range(days):
            new_model.printRelevantInfo()
            new_model.updateSteps(24*5)
        if debug:
            #print("R0 schedule:", new_model.convertToRoomName( new_model.agents[new_model.R0_agentId].schedule))
            logDataDict = new_model.printLog()
            for key, value in logDataDict.items():
                max_limits[key] = max_limits.get(key, []) + [value]
        R0Values.append(new_model.returnR0())
        
        print(f"finished {(i+1)/simulationN*100}% of cases")
    if debug:
        for key, value in max_limits.items():
            print(key, "max is the following:", value)
    print("R0 is", R0Values)
    if visual:
        new_model.visualOverTime()
    print("time:", time.time()-t1)
    data = statfile.analyzeData(R0Values)
    #pickleName = flr.fullPath("R0Data.pkl", "picklefile")
    # save the data just in case
    #flr.saveUsingDill(pickleName, R0Values)
    print(data)
    print("(npMean, stdev, rangeVal, median)")
    statfile.boxplot(R0Values,True, "R0 simulation", "cases", "infected people (R0)", ["base model"])
    
    
def main():
    """intialize and run the model"""    
    modelConfig = {
        # time intervals
        "unitTime" : "hour",

        # AGENTS
        "AgentPossibleStates": {
            "neutral" : ["susceptible", "exposed"],
            "infected" : ["infected Asymptomatic", "infected Asymptomatic Fixed", "infected Symptomatic Mild", "infected Symptomatic Severe"],  
            "recovered" : ["quarantined", "recovered"],
            "debugAndGraphingPurpose": ["falsePositive"],
            },

       
        # these are parameters, that are assigned later or is ok to be initialized with default value 0
        "extraParam": {
            "Agents": ["agentId","path", "destination", "currLocation",
                        "statePersistance","lastUpdate", "personality", 
                        "arrivalTime", "schedule", "travelTime",
                        "officeAttendee", "gathering"],
            "Rooms":  ["roomId","agentsInside","oddCap", "evenCap", "classname", "infectedNumber"],
            "Buildings": ["buildingId","roomsInside"],
        },
        "extraZipParam": {
            "Agents" : [("motion", "stationary"), ("infected", False), ("compliance", False)],
            
        },
        "booleanAssignment":{
            "Agents" : [("officeAttendee", 0), ("gathering", 0.5)],
        },
        "baseP" :1.25,
        "infectionSeedNumber": 10,
        "infectionSeedState": "exposed",
        "infectionContribution":{
            "infected Asymptomatic":0.5,
            "infected Asymptomatic Fixed":0.5,
            "infected Symptomatic Mild":1,
            "infected Symptomatic Severe":1,
        },
        # INFECTION STATE
        "transitionTime" : {
            "susceptible":-1,
            "exposed":2*24, # 2 days
            "infected Asymptomatic":2*24, # 2 days
            "infected Asymptomatic Fixed":10*24, # 10 days
            "infected Symptomatic Mild":10*24,# 10 Days
            "infected Symptomatic Severe":10*24, # 10 days
            "recovered":-1,
            "quarantined":24*14, # 2 weeks 
        },
        
        "transitionProbability" : {
            "susceptible": [("exposed", 1)],
            "exposed": [("infected Asymptomatic", 0.85), ("infected Asymptomatic Fixed", 1)],
            "infected Asymptomatic Fixed": [("recovered", 1)],
            "infected Asymptomatic": [("infected Symptomatic Mild", 0.5), ("infected Symptomatic Severe", 1)],
            "infected Symptomatic Mild": [("recovered", 1)],
            "infected Symptomatic Severe": [("recovered", 1)],
            "quarantined":[("susceptible", 1)],
            "recovered":[("susceptible", 0.5), ("recovered", 1)],
        },

        # QUARANTINE
        "quarantineSamplingProbability" : 0,
        "quarantineDelay":0,
        "walkinProbability" : {"infected Symptomatic Mild": 0.7, "infected Symptomatic Severe": 0.95},
        "quarantineSampleSize" : 400,
        "quarantineSamplePopulationSize":0.10,
        "quarantineRandomSubGroup": False,
        "closedBuildings": ["eating", "gym", "study"],
        "quarantineOffset": 1*24+9,
        "quarantineInterval": 24*1,
        "falsePositive":0.03,
        "falseNegative":0.001,
        "remoteStudentCount": 1000,
        
        # face mask
        "maskP":0.5,
        "nonMaskBuildingType": ["dorm", "dining", "faculty_dining_hall"],
        "nonMaskExceptionsHub": ["dorm", "dining"],
        "semiMaskBuilding": ["social", "large gathering"],
        "openHub" : ["dining", "faculty_dining_room"],
      
        # OTHER parameters
        "transitName": "transit_space_hub",
        "offCampusInfectionP":0.125/700,
        "trackLocation" : ["_hub"],
        #possible values:
        #    1: facemask
        #    3: testing for covid and quarantining
        #    4: closing large buildings
        #    5: removing office hours with professors
        #    6: shut down large gathering 
     
        "interventions":[5],#[1,3,4,5,6],
        "allowedActions": [],#["walkin"],
        "massInfectionRatio":0.10,
        "complianceRatio": 0,
        "randomSocial":False,
    }
    # you can control for multiple interventions by adding a case:
    #  [(modified attr1, newVal), (modified attr2, newVal), ...]
    simulationControls = [
        [("complianceRatio", 0)],
        [("complianceRatio", 0.33)],
        [("complianceRatio", 0.66)],
        [("complianceRatio", 1)],
    ]
    R0_controls = [("infectionSeedNumber", 10),("quarantineSamplingProbability", 0),
                    ("allowedActions",[]),("quarantineOffset", 20*24), ("interventions", [5])]
    
    allIn = [("complianceRatio", 1), ("interventions", [1,3,4,5,6]), ("allowedActions", ["walkin"]),]

    configCopy = dict(modelConfig)
    for variableTup in allIn:
        configCopy[variableTup[0]] = variableTup[1]
    simpleCheck(modelConfig, days=100, visuals=True, name="newBase_125p")
    
    #R0_simulation(modelConfig, R0_controls,20, debug=True, visual=True)
    
    
    return
    createdFiles = initializeSimulations(simulationControls, modelConfig, True)
    simulateAndPlot(createdFiles, 5, 24*100, additionalName="050P_", title="mask with 0.5 effectiveness", labels=labels)
    
def agentFactory(agent_df, slotVal):
    """
        factory function used to dynamically assign __slots__, creates agents from the given df
        the values stored in __slots__ are the column of the df and some additional parameters that deals with relatinships and membership

        Parameters:
        - agent_df: a panda dataframe with each row corresponding to an agent's initial value
        - slotVal: the column values of the dataframe
    
    """
    class Agents:
        """
            creates an agent that moves between rooms and interacts with each other (indirectly)
        """
        __slots__ = slotVal
        def __init__(self, agentParam):
            for slot, value in zip(self.__slots__, agentParam):
                self.__setattr__(slot, value)

        def updateLoc(self, currTime, adjDict):
            """
                change agent's state, either moving or stationary,
                look at adjacent rooms and move to one of the connected rooms

                Parameters:
                - currTime: the current time
                - adjDict: the adjacency dictionary, (key: roomId, value: list of roomsId of rooms connected to the key)    
            """
            curr_room = self.currLocation
            
            if self.motion == "stationary" and currTime >= self.arrivalTime:
                if True: #purly deterministic 
                    self.destination = self.checkschedule(currTime)
                    nextNode,lastNode  = adjDict[curr_room][0][0], adjDict[self.destination][0][0] 
                    if curr_room == self.destination:
                        self.path = []
                    elif nextNode == lastNode: # moving between the same superstructure
                        self.path = [nextNode]
                    else: # required to move across the transit hub
                        self.path = [lastNode, self.transit, nextNode] 
                    self.move(adjDict)
            elif self.motion == "moving" and currTime >= self.travelTime + self.arrivalTime:
                # the agent is still moving across
                self.move(adjDict)
                self.arrivalTime = currTime
            else: # the agent doesnt need to move
                return (self.currLocation, self.currLocation)
            return (curr_room, self.currLocation)

        def checkschedule(self, currTime):
            """
                check the current time and return the value stored in the shcedule

                Parameters:
                - currTime: current time, used to find the schedule item
            
            """
            # there are 24*7 hours in a week
            # currTime%24*7 will give you the time in terms of week, then // 24 give you days
            # if the value is greater than 5, then its a weekday
            # if currTime is odd, then its a odd day and vise versa with even days

        
            dayOfWeek = (currTime%(24*7))//24
            hourOfDay = currTime%24
            if self.state == "quarantined":
                return self.initial_location
            elif self.state == "infected Symptomatic Severe" and currTime>self.lastUpdate+120:
                return self.initial_location
            if dayOfWeek > 3: # its a weekend
                return self.schedule[2][hourOfDay]
            elif dayOfWeek & 1: # bit and, its an odd day
                return self.schedule[1][hourOfDay]
            else: # its an even day
                return self.schedule[0][hourOfDay]

        def move(self, adjDict):
            """
                chooses the random room and moves the agent inside
            """
            pastLocation = self.currLocation
            if self.destination in [a[0] for a in adjDict[self.currLocation]]:
                # the agent reached it's destination, takes a rest
                
                self.currLocation = self.destination
                self.destination = None
                self.path = []
                self.motion = "stationary"
            elif self.path == []:
                pass #no change
            else: #the path array is not empty, the agent is still moving
                self.motion = "moving"
                self.currLocation = self.path.pop()
                self.travelTime = 0
            return (pastLocation, self.currLocation)
   
        def changeState(self, updateTime, stateName, durration):
            """
                Change the state of the agents, all states have a minimum waiting time,
                and changing state durring that waiting period is not recommended, because it defeats the purpose
            
                If the current state can evolve unexpectedly, then set durration to 0 and use a random value to determine if the state should change.
                Negative value for durration means the state will persist on to infinity
            
                Parameters:
                - updateTime: the time when the state was updated
                - stateName: the name of the start to transition to 
                - infected: bool that tells if the agent was infected or not
                - durration: the minimum time required to wait until having the choice of chnaging states
            """
            self.lastUpdate = updateTime
            self.statePersistance = durration
            self.state = stateName
            if stateName in ["exposed", "infected Asymptomatic", "infected Asymptomatic Fixed", "infected Symptomatic Mild", "infected Symptomatic Severe"]:

                self.infected = True
        
        def transitionTime(self):
            """
                return the time that that the agent can change state,
                since the agent is looking at his "clock", the returned time could be off from the global time, can be used for comas (if those states are implimented)
            """
            return self.lastUpdate + self.statePersistance

        def __repr__(self):
            repr_list = [val for val in self.__slots__]
            return repr_list.join() 
        
        def __str__(self):
            repr_list = [val for val in self.__slots__]
            return repr_list.join() 

    # creates the agents and put them in a dictionary
    tempDict = dict()
    for index, row in agent_df.iterrows():
        tempDict[index] = Agents(row.values.tolist())
    return tempDict

def SuperStructBuilder():
    pass

def roomFactory(room_df, slotVal):
    """
        factory function used to dynamically assign __slots__

        Parameters:
        - agent_df: a panda dataframe with each row corresponding to a room's initial value
        - slotVal: the column values of the dataframe
    """
    class Partitions:
        __slots__ = slotVal
        def __init__(self, roomParam):
            for slot, value in zip(self.__slots__, roomParam):
                self.__setattr__(slot, value)

        def enter(self, agentId):
            """ a put the id of the agent that entered the room"""
            if self.checkCapacity():
                self.agentsInside.add(agentId)

        def checkCapacity(self):
            """return a boolean, return True if theres capacity for one more agent, False if the room is at max capacity 
            """
            
            if len(self.agentsInside) < int(self.capacity):
                return True
            return False
    
        def leave(self, agentId):
            """ remove the id of the agent that exited the room"""
            if agentId in self.agentsInside:
                self.agentsInside.discard(agentId)
        
    tempDict = dict()
    for index, row in room_df.iterrows():
        tempDict[index] = Partitions(row.values.tolist())
    return tempDict
    
def superStrucFactory(struc_df, slotVal):
    """
        creates and returns a dictionary that keeps the building class
    
        Parameters:
        - agent_df: a panda dataframe with each row corresponding to an buildings's initial value
        - slotVal: the column values of the dataframe
    """
    class Superstructure: # buildings
        __slots__ = slotVal
        def __init__(self, strucParam):
            for slot, value in zip(self.__slots__, strucParam):
                self.__setattr__(slot, value)

    temp_dict = dict()
    for index, row in struc_df.iterrows():
        temp_dict[index] = Superstructure(row.values.tolist())
    return temp_dict
        
class AgentBasedModel:
    # fin
    def __init__(self):
        """
        starts an instance of an agent based model,
        agents and a network is not added at this point
        """
        self.time = 0
        self.date = 0
        self.dateDescriptor = "E" # can be "E": even, "O": odd, or "W": weelend
        self.storeVal = False
        # maybe
        self.directedGraph = False
        # nope
        self.quarantineIntervention = False
        # nope
        self.closedLocation = []
        # nope
        self.buildingClosure = False
        # nope
        self.officeHours = True
        self.debug=True
        self.R0 = False
        self.R0_agentId = -1
        self.R0_agentIds = [-1]
        # debug/ additional requirements and features 
        self.gathering_count = 0
        self.officeHourCount = 0
        self.facemaskIntervention = False
        self.walkIn = False
        self.largeGathering = True
        self.quarantineList = []
        self.falsePositiveList = []
        self.R0_agentIds = []
        self.masksOn = False
   
        # rename in the future, used to cache informstion to reduce the number of filtering thats happening in the future run
        self.state2IdDict=dict()
   
    # fin       
    def loadAgent(self, fileName, folderName="configuration"):
        self.agent_df = flr.make_df(folderName, fileName)
    # fin 
    def loadBuilder(self, filename, folderName="configuration"):
        """use a builder to make the dataframe for the buiulding and rooms"""
        self.building_df, self.room_df = mod_df.mod_building(filename, folderName)
    
    # fin
    def changeStateDict(self, agentId, previousState, newState):
        """
            modifies the dictionary, state2IdDict, when an agent change states, 
            takes care of removal and addition to the appropriate dictionary value, and modifies the agent's attribute

            Parameters:
            - agentId: the agent's key/Id value 
            - previousState: the state of the agent, better to be a parameter because checks occurs before the function is called
            - newState: the state name to transition into
        """
        self.state2IdDict[previousState].discard(agentId)# remove the agent from the state list
        if previousState == "quarantined" and not self.agents[agentId].infected:
            self.state2IdDict["falsePositive"].discard(agentId)
        self.state2IdDict[newState].add(agentId)# then add them to the new state list
        self.agents[agentId].changeState(self.time, newState, self.config["transitionTime"][newState])
    
    # fin
    def addFalsePositive(self, agentId):
        self.state2IdDict["falsePositive"].add(agentId)

    # takes 4 seconds
    # fin
    def studentFacultySchedule(self):
        """
            calls the schedule creator and replace general notion of locations with specific location Id,
            for example if the string "dorm" is in the schedule, it will be replaced by a room located in a building with "building_type" equal to "dorm"
        """
        schedules, onVsOffCampus = schedule_students.scheduleCreator()
        fac_schedule, randomizedFac = schedule_faculty.scheduleCreator()
        roomIds = self.findMatchingRooms("building_type", "classroom")
        stem = self.findMatchingRooms("located_building", "STEM_office")
        art = self.findMatchingRooms("located_building", "HUM_office")
        hum = self.findMatchingRooms("located_building", "ART_office") 
        facultyDiningRoom = self.findMatchingRooms("building_type", "dining")[0]

        self.rooms[facultyDiningRoom].room_name = "faculty_dining_room"
        self.rooms[facultyDiningRoom].building_type = "faculty_dining_room"

        # sample faculty schedule ["Off", "Off", "dining", 45, "Off", ...]
        for index, (facSche, randFac) in enumerate(zip(fac_schedule, randomizedFac)):
            replacement = stem if randFac == "S" else (art if randFac == "A" else hum)
            for i, row in enumerate(facSche):
                for j, item in enumerate(row):
                    if item == "office": # choose a random office within their department
                        fac_schedule[index][i][j] = np.random.choice(replacement)
                    elif item == "dining": # convert to faculty dining to restict area to faculty only space
                        fac_schedule[index][i][j] = "faculty_dining_room"
                    elif isinstance(item, int): # maps the nth class to the right classroom Id
                        fac_schedule[index][i][j] = roomIds[item]

        # replace entries like (48, 1) --> 48, tuple extractor
        schedules = [[[roomIds[a[0]] if isinstance(a[0], int) else a for a in row] for row in student_schedule] for student_schedule in schedules]

        onCampusIndex, offCampusIndex, facultyIndex = 0, 0, 0
        offCampusSchedule, onCampusSchedule = [], [] 
        
        # map the schedules to oncampus and offcampus students
        for schedule, onOffDistinction in zip(schedules, onVsOffCampus):
            if onOffDistinction == "Off":
                offCampusSchedule.append(schedule)
            else:
                onCampusSchedule.append(schedule)

        # assign the schedule to the correct agent
        for agentId, agent in self.agents.items():
            if agent.archetype == "student": # needs to be for students
                if agent.Agent_type == "onCampus": # oncampus
                    agent.schedule = onCampusSchedule[onCampusIndex]
                    onCampusIndex+=1
                else: # offcampus
                    agent.schedule = offCampusSchedule[offCampusIndex]
                    offCampusIndex+=1
            else:# faculty
                agent.schedule = fac_schedule[facultyIndex] 
                facultyIndex+=1
        
        # this gets rid of "sleep", "Off", "dorm" and replace it with one of the leaf Ids
        for entry in ["sleep", "Off", "dorm"]:
            self.replaceScheduleEntry(entry)
        self.replaceByType(agentParam="Agent_type", agentParamValue="faculty", partitionTypes="faculty_dining_room", perEntry=False)
        print("social space random?",self.config["randomSocial"])
        if self.config["randomSocial"]:
            print("*"*20, "random social, please fix this")
            self.replaceByType(partitionTypes=["library", "dining","gym", "office"]) # social
            self.replaceByType(agentParam="Agent_type", agentParamValue="faculty", partitionTypes="social", perEntry=True)
        else:
            print("*"*20, "non random")
            self.replaceByType(partitionTypes=["library", "dining","gym", "office", "social"])
        print("finished schedules")


        """# print sample faculty schedules
        for agentId, agent in self.agents.items():
            if agentId > 2000 and agentId%100 == 0:
                print("below", "*"*20)
                print(agent.schedule[:2])
                print(self.convertToRoomName(agent.schedule[:2]))
        """  
    
    # fin
    def replaceByType(self, agentParam=None, agentParamValue=None, partitionTypes=None, perEntry=False):
        """
            go over the schedules of the agents of a specific type and convert entries in their schedules

            Parameters:
            - agentParam: a string of the attribute name
            - agentParamValue: the value of the agentParam attribute, filter agents with this value and apply the replace function
            - SuperStrucType: a string to replace 
            - perEntry: boolean, if True, it randomly chooses an Id from the pool every time it locates the identifier, if False, one Id is taken from the pool per agent
        """
        # filter rooms with specific value for building_type, returned roomIds dont include hub ids
        index = 0
        if not isinstance(partitionTypes, list): # if only one value is passed
            if agentParam != None and agentParamValue != None:
                filteredId = [agentId for agentId, agent in self.agents.items() if getattr(agent, agentParam) == agentParamValue]
            else: filteredId = list(self.agents.keys())
            roomIds = self.findMatchingRooms("building_type", partitionTypes)
           
            if not perEntry:
                randomVec = np.random.choice(roomIds, size=len(filteredId), replace=True)
            for agentId in filteredId:
                for i, row in enumerate(self.agents[agentId].schedule):
                    for j, item in enumerate(row):
                        if item == partitionTypes:
                            if not perEntry:
                                self.agents[agentId].schedule[i][j] = randomVec[index]
                            else:
                                self.agents[agentId].schedule[i][j] = np.random.choice(roomIds)
                index +=1
        else: # if a list of values is passed
            def indexVal(listObj, obj):
                try:
                    return listObj.index(obj)
                except ValueError:
                    return -1
            if agentParam != None and agentParamValue != None:
                filteredId = [agentId for agentId, agent in self.agents.items() if getattr(agent, agentParam) == agentParamValue]
            else: filteredId = list(self.agents.keys())
            
            partitionIds = [self.findMatchingRooms("building_type", partitionType)  for partitionType in partitionTypes]
            agentCount = len(self.agents)
            
            randRoomIds = []
            for idList in partitionIds:
                randRoomIds.append(np.random.choice(idList, size=agentCount, replace=True))

            for agentId in filteredId:
                for i, row in enumerate(self.agents[agentId].schedule):
                    for j, item in enumerate(row):
                        indx = indexVal(partitionTypes, item) 
                        if  indx != -1:
                            self.agents[agentId].schedule[i][j] = randRoomIds[indx][index]  
                index+=1

    # fin
    def replaceScheduleEntry(self, antecedent):
        """
            replace locations with each agent's initial location

            Parameters:
            - antecedent: the string to replace with the agent's initial location
        """
        for agentId, agent in self.agents.items():
            agent.schedule = [[a if a != antecedent else agent.initial_location for a in row] for row in agent.schedule] 
   
    # fin
    def initializeWorld(self):
        """
            initialize the world with default value, 
            also unpacks dataframe and make the classes 
        """
        # add a column to store the id of agents or rooms inside the strucuture
        
        # these are required values added to the df so that they can be used to store information and relationships 
        self.addToDf()
        print("*"*20)
        
        self.adjacencyDict = self.makeAdjDict()
        self.buildings = self.makeClass(self.building_df, superStrucFactory)
        self.rooms = self.makeClass(self.room_df, roomFactory)
        # a dictionary (key: buildingID, value: [roomID in the building])
        self.roomsInBuilding = dict((buildingId, []) for buildingId in self.buildings.keys())
        # a dictionary (key: buildingName, value: building ID)
        self.buildingNameId = dict((getattr(building, "building_name"), buildingId) for buildingId, building in self.buildings.items())
        # a dictionary (key: roomName, value: room ID)
        self.roomNameId = dict((getattr(room, "room_name"), roomId) for roomId, room in self.rooms.items())
        # initialize a transit hub
        self.agent_df["transit"] = self.roomNameId[self.config["transitName"]]
    
        # add rooms to buildings 
        self.addRoomsToBuildings()
        # create agents
        self.agents = self.makeClass(self.agent_df, agentFactory)
      
        for agentId, agent in self.agents.items():
            agent.agentId = agentId

        # build a dictionary, key: state --> value: list of agentIds
        for stateList in self.config["AgentPossibleStates"].values():
            for stateName in stateList:
                self.state2IdDict[stateName] = set()

    # fin   
    def addToDf(self):
        """add columns to dataframe before object creation, mainly because objects in this code use __slots__,
         __slots__ prevents the addition of attributes after instance creation, hence required to define them before creation"""
        keyList = list(self.config["extraParam"].keys())
        keyZipList = list(self.config["extraZipParam"].keys())
        for dfRef, keyStr in zip([self.agent_df, self.room_df, self.building_df], ["Agents", "Rooms", "Buildings"]):
            # assign 0 as default value:
            if keyStr in keyList:
                for attrName in self.config["extraParam"][keyStr]:
                    dfRef[attrName] = 0
            # assigned default value
            if keyStr in keyZipList:
                for (attrName, attrVal) in self.config["extraZipParam"][keyStr]:
                    dfRef[attrName] = attrVal

    # fin
    def startInfectionAndSchedule(self):
        
        self.initialize_infection()
        self.studentFacultySchedule()
        self.InitializeIntervention()
        self.booleanAssignment()
        if "walkin" in self.config["allowedActions"]:
            self.walkIn = True

        print("finished initializing intervention and schedules")

    # fin
    def booleanAssignment(self):
        for (VarName ,p_val) in self.config["booleanAssignment"]["Agents"]:
            self.agentAssignBool(p_val, VarName, replacement=False)  

    # fin
    def agentAssignBool(self, percent = 0, attrName="officeAttendee", replacement=False):
        """Assign True or false to Agent's office attend boolean value """
        # check if its a decimal or probability
        if percent > 1: percent/=100
        size = int(len(self.agents) * percent)
        sample = np.concatenate((np.ones(size), np.zeros(len(self.agents)-size)), axis=0)
        np.random.shuffle(sample)
        for index, agent in enumerate(self.agents.values()):
            if sample[index]:
                setattr(agent, attrName,True)
            else:
                setattr(agent, attrName,False)

    # fin
    def addRoomsToBuildings(self):
        """add room_id to associated buildings"""
        for buildingId, building in self.buildings.items():
            building.roomsInside = []   
        
        for roomId, room in self.rooms.items():
            self.roomsInBuilding[self.buildingNameId[room.located_building]].append(roomId)  
            self.buildings[self.buildingNameId[room.located_building]].roomsInside = self.buildings[self.buildingNameId[room.located_building]].roomsInside + [roomId] 
    
    # fin
    def generateAgentFromDf(self, counterColumn="totalCount"):
        """
        use this to multiple the number of agents, multiplies by looking at the counterColumn
        Expand the dataframe along the counterColumn 

        """
        slotVal = self.agent_df.columns.values.tolist()
        if counterColumn in slotVal:
            slotVal.remove(counterColumn)
        tempList = []
        for _, row in self.agent_df.iterrows():
            counter = row[counterColumn]
            rowCopy = row.drop(counterColumn).to_dict()
            tempList+=[rowCopy for _ in range(counter)]
        self.agent_df = pd.DataFrame(tempList)     
    
    # fin
    def initializeR0(self):
        self.R0 = True
        for agentIdVal in self.agents.keys():
            self.changeStateDict(agentIdVal, self.config["infectionSeedState"], "susceptible")        
        onCampusStudents = [agentId for agentId, agent in self.agents.items() if agent.Agent_type=="onCampus"]
        self.R0_agentIds = list(np.random.choice(onCampusStudents,size=self.config["infectionSeedNumber"], replace=False))
        self.R0_agentId = self.R0_agentIds[0]
        print("running R0 calculation with ID", self.R0_agentIds)
        for agentId in self.R0_agentIds:
            self.changeStateDict(agentId, "susceptible", self.config["infectionSeedState"])
     
        self.R0_agentIds = set(self.R0_agentIds)
     
    # fin
    def returnR0(self):
        counter = 0
        for key, value in self.parameters.items():
            if key != "susceptible":
                counter += value[-1]
        self.printRelevantInfo()
        print(f"# infected: {counter}, initial: {self.config['infectionSeedNumber']}, Ave R0: {(counter - self.config['infectionSeedNumber'])/self.config['infectionSeedNumber']}")
        return (counter - self.config["infectionSeedNumber"])/self.config["infectionSeedNumber"]
    
    # fin
    def initializeAgents(self):
        """
            change the agent's current location to match the initial condition
        """
        # convert agent's location to the corresponding room_id and add the agent's id to the room member
        # initialize
        print("*"*20)
        for rooms in self.rooms.values():
            rooms.agentsInside = set()
        # building_type
        bType_RoomId_Dict = dict()
        for buildingId, building in self.buildings.items():
            # get all rooms that dont end with "_hub"
            buildingType_roomId = [roomId for roomId in self.roomsInBuilding[buildingId] if not self.rooms[roomId].room_name.endswith("_hub")]
            bType_RoomId_Dict[building.building_type] = bType_RoomId_Dict.get(building.building_type, []) + buildingType_roomId

        for agentId, agent in self.agents.items():
            initialLoc = getattr(agent, "initial_location")
            if initialLoc in self.roomNameId.keys(): # if the room is specified
                # convert the location name to the corresponding id
                location = self.roomNameId[initialLoc]
            elif initialLoc in self.buildingNameId.keys(): # if location is under building name
                # randomly choose rooms from the a building
                possibleRoomsIds = self.roomsInBuilding[self.buildingNameId[initialLoc]]
                possibleRooms = [roomId for roomId in possibleRoomsIds if self.rooms[roomId].checkCapacity() and not self.rooms[roomId].room_name.endswith("_hub")]
                location = np.random.choice(possibleRooms)
            elif initialLoc in bType_RoomId_Dict.keys(): # if location is under building type
                possibleRooms = [roomId for roomId in bType_RoomId_Dict[initialLoc] if self.rooms[roomId].checkCapacity()]
                location = np.random.choice(possibleRooms)
            else:
                print("something wrong")
                # either the name isnt properly defined or the room_id was given
                pass
            agent.currLocation = location
            agent.initial_location = location
            self.rooms[location].agentsInside.add(agentId)
        
    def extraInitialization(self):
        self.globalCounter = 0
        self.R0_visits = []

    def makeSchedule(self):
        """
            part 1, dedicate a class to rooms
            create schedules for each agents
        """
        self.numAgent = len(self.agents.items())
        archetypeList = [agent.archetypes for agent in self.agents.values()]
        classIds = list(roomId for roomId, room in self.rooms.items() if room.building_type == "classroom" and not room.room_name.endswith("hub"))
        capacities = list(self.rooms[classId].limit for classId in classIds)
        self.scheduleList = schedule.createSchedule(self.numAgent, archetypeList,classIds,capacities)
        self.replaceStaticEntries("sleep")

    # NA
    def officeHour_infection(self):
        """
        an abstract reprsentation of professors meeting with students,
        People meet with proffesors and the pair might get infected 
        """
        for roomId, room in self.rooms.items():
            # this only happens in classrooms
            if len(self.rooms[roomId].agentsInside) > 0 and room.building_type == "classroom":
                # get the ids of faculty
                faculty = [agentId for agentId in self.rooms[roomId].agentsInside 
                        if "faculty" in self.agents[agentId].Agent_type] 
                # if faculty are in the system(partition)
                if len(faculty) > 0:
                    non_faculty = [agentId for agentId in self.rooms[roomId].agentsInside 
                                    if self.agents[agentId].officeAttendee and agentId not in faculty]
                    # setting up the infection 
                    officeHourAgents = non_faculty+faculty
                    agentsOnsite = len(officeHourAgents)
                    baseP = self.config["baseP"]
                    randVec = np.random.random(len(faculty)*len(non_faculty))
                    # pairwise infection happening
                    for i, tup in enumerate(itertools.product(faculty, non_faculty)):
                        contribution = self.infectionWithinPopulation(tup, roomId)
                        if randVec[i] < (3*baseP*contribution)/agentsOnsite:
                            for agentId in tup:
                                if self.agents[agentId].state == "susceptible":
                                    self.changeStateDict(agentId, "susceptible", "exposed")
                                    self.officeHourCount+=1
                                    #print(f"{self.time}, in {(roomId, room.room_name)} the {i}-th office interaction, office hourInfection randomVec < { (3*baseP*contribution)/agentsOnsite}, number of people in office: {agentsOnsite}, with {faculty} faculty" )

    # fin      
    def makeAdjDict(self):
        """
            creates an adjacency list implimented with a dictionary

            Parameters (implicit):
            - room's "connected_to" parameters
        """
        self.specialId = False
        adjDict = dict()
        for roomId, row in self.room_df.iterrows():
            adjRoom = self.room_df.index[self.room_df["room_name"] == row["connected_to"]].tolist()[0]
            travelTime = row["travel_time"]
            adjDict[roomId] = adjDict.get(roomId, []) + [(adjRoom, travelTime)]
            if not self.directedGraph:
                adjDict[adjRoom] = adjDict.get(adjRoom,[]) + [(roomId, travelTime)]
        return adjDict
    
    # fin
    def makeClass(self, dfRef, func):
        """
        returns a dictionary with ID as Keys and values as the class object
        
        Parameters:
        - dfRef: the dataframe object
        - func: a referenece to the function used to create the class object 
        """
        slotVal = dfRef.columns.values.tolist()
        tempDict = func(dfRef, slotVal)
        numObj, objVal = len(tempDict), list(tempDict.values())
        className = objVal[0].__class__.__name__ if numObj > 0 else "" 
        if self.debug:
            print(f"creating {numObj} {className} class objects, each obj will have __slots__ = {slotVal}")
        return tempDict

    # fin
    def findMatchingRooms(self, partitionAttr, attrVal=None, strType=False):
        """
            returns a list of room IDs that matches the criterion: if object.attrVal == partitionAttr
        
            Parameters:
            - roomParam: the attribute name
            - roomVal: the attribute value, if None, returns all room

            Parameters(might be removed):
            - strType (= False): if the value is a string or not, 
        """
        if attrVal==None: # return rooms without filters
            return [roomId for roomId, room in self.rooms.items() if not getattr(room, "room_name").endswith("hub")]
        if strType: # case insensitive
            return [roomId for roomId, room in self.rooms.items() if getattr(room, partitionAttr).strip().lower() == attrVal.strip().lower() and not getattr(room, "room_name").endswith("hub")]
        else:
            return [roomId for roomId, room in self.rooms.items() if getattr(room, partitionAttr) == attrVal and not getattr(room, "room_name").endswith("hub")]

    #fin
    def convertToRoomName(self, idList):
        """
            for debugging/output purpose
            get a single row of 24 hour schedule and convert the ids to the corresponding room name 

            Parameters:
            - idList: a list that stores room ids
        """
        return [[self.rooms[roomId].room_name for roomId in row] for row in idList]

    # fin    
    def updateSteps(self, step = 1):  
        for _ in range(step):     
            self.time+=1
            modTime =  self.time%24
            if  23 > modTime > 6 and len(self.state2IdDict["recovered"]) != len(self.agents): 
                # update 4 times to move the agents to their final destination
                # 4 is the max number of updates required for moving the agents from room --> building_hub --> transit_hub --> building_hub --> room
                for _ in range(4):
                    self.updateAgent()
                    self.hub_infection()
                self.infection()
                if self.officeHours: # remove office hours
                    self.officeHour_infection()

            if self.time%(24*7) == 0:
                self.big_gathering()
            # if weekdays
            if self.dateDescriptor != "W":
                if modTime == 8:
                    self.checkForWalkIn()
                if self.quarantineIntervention and self.time%self.quarantineInterval == 0 and self.time > self.config["quarantineOffset"]: 
                    self.testForDisease()
                self.delayed_quarantine()
            if self.storeVal and self.time%self.timeIncrement == 0:
                self.storeInformation()
            self.logData()
        
            if self.time%24==0:
                self.date+=1
                if self.date%7 > 3: ###############################
                    self.dateDescriptor = "W"
                elif self.date%2 == 0:
                    self.dateDescriptor = "E"
                else:
                    self.dateDescriptor ="O"

    # fin
    def big_gathering(self):
        if self.largeGathering: # big gathering at sunday midnight
            agentIds = [agentId for agentId, agent in self.agents.items() if agent.gathering]
            if len(agentIds) < 50:
                print("not enough for a party")
                return
            groupNumber = 3
            groupMinCount, groupMaxCount = 20, 60
            subsets, randVecs = [], []
            newly_infected = 0
            for _ in range(groupNumber):
                size = random.randint(groupMinCount,groupMinCount)
                subsets.append(np.random.choice(agentIds, size=size, replace=False))
                randVecs.append(np.random.random(size))
            totalSubset = list({agentId for subset in subsets for agentId in subset})
            
            counter = self.countWithinAgents(totalSubset, "susceptible")
            for subset, randVec in zip(subsets, randVecs):
                totalInfection = self.gathering_infection(subset)
                for index, agentId in enumerate(subset):
                    if self.agents[agentId].state == "susceptible" and randVec[index] < totalInfection: 
                        self.changeStateDict(agentId,"susceptible" ,"exposed")
                        newly_infected+=1
            self.gathering_count+=newly_infected
            print(f"big gathering at day {self.time/24}, at the gathering there were {counter} healthy out of {len(totalSubset)} and {newly_infected} additionally infected agents,", totalInfection)

    # fin
    def gathering_infection(self, subset):
        if self.masksOn:
            contribution = self.infectionWithinPopulation(subset, -1)
        else:
            contribution = self.infectionWithinPopulation(subset)
        print(f"gathering {(50*(int(len(subset)/50)+1))}, numerator {(self.config['baseP']*3*contribution)}")
        cummulativeFunc = (self.config["baseP"]*3*contribution)/(40*(int(len(subset)/40)+1))
        return cummulativeFunc

    # fin
    def findDoubleTime(self):
        """
            returns a tuple of (doublingTime, doublingInterval, doublingValue)
        """
        data = dict()
        data["infected"] = np.zeros(len(self.parameters["susceptible"]))
        for key in self.parameters.keys():
            if key in ["susceptible"]:
                data[key] = self.parameters[key]
            else:
                data["infected"]+=np.array(self.parameters[key]) 
        doublingTime = []
        doublingValue = []
        previousValue = 0
        for i, entry in enumerate(data["infected"]):
            if entry >= 2*previousValue:
                doublingTime.append(i/24)
                doublingValue.append(entry)
                previousValue = entry
        doublingInterval = []
        for i in range(len(doublingTime)-1):
            doublingInterval.append(doublingTime[i+1]-doublingTime[i])
        return (doublingTime, doublingInterval, doublingValue)

    # fin
    def addKeys(self, tempDict):
         self.config = tempDict

    #fin
    def startLog(self):
        """
            initialize the log, building, room and people in rooms
        """
        self.building_log = dict((key,[]) for key in self.buildings.keys())
        self.room_log = dict((key,[]) for key in self.rooms.keys())
        self.room_cap_log = dict((key,[]) for key in self.rooms.keys())
    # fin
    def logData(self):
        # find total infected and add them to the room_log
        if not self.R0:
            for roomId, room in self.rooms.items():
                total_infected = sum(self.countWithinAgents(room.agentsInside, stateName) for stateName in self.config["AgentPossibleStates"]["infected"])
                self.room_log[roomId].append(total_infected)
        
        # this is the total number of agents in the room
        for roomId, room in self.rooms.items():
            self.room_cap_log[roomId].append(len(room.agentsInside))
    # fin
    def printLog(self):
        """
            print the logs, only for debug purpose
        """ 
        # convert the log to 24 hour bits and get the daily activity
        timeInterval = 24
        maxDict = dict()
        scheduleDict = dict()
        for key, value in self.room_cap_log.items():
            buildingType = self.rooms[key].building_type 

            if len(value)%timeInterval !=0:
                remainder = len(value)%timeInterval
                value+=[0 for _ in range(timeInterval - remainder)]
            
            a = np.array(value).reshape((-1,timeInterval))
            maxDict[buildingType] = max(maxDict.get(buildingType, 0), max(value))
            scheduleDict[self.rooms[key].room_name] = a
        nodes = ["gym", "library", "offCampus", "social"]
        for node in nodes:
            if self.debug:
                for index, (key, value) in enumerate(scheduleDict.items()):
                    if node in key and not key.endswith("_hub") and index < 5:
                        print(key, value)
                for key, value in maxDict.items():
                    if node in key and not key.endswith("_hub"):
                        print(key, value)
        return maxDict
                
    # fin
    def updateAgent(self):
        """call the update function on each person"""
        # change location if the old and new location is different
        index = 0
        offCampusNumber = len(self.rooms[self.roomNameId["offCampus_hub"]].agentsInside)
        if not self.R0 and offCampusNumber > 0:
            randomVec = np.random.random(offCampusNumber) 
        for agentId, agent in self.agents.items():
            loc = agent.updateLoc(self.time, self.adjacencyDict)
            if loc[0] != loc[1]:
                # if the agent is coming back to the network from the offcampus node
                if not self.R0 and loc[0] == self.roomNameId["offCampus_hub"] and loc[1] == self.roomNameId[self.config["transitName"]]: 
                    if agent.state == "susceptible" and randomVec[index] < self.config["offCampusInfectionP"]:
                        print("*"*5, "chnaged state from susceptible to exposed through transit")
                        self.changeStateDict(agentId,agent.state, "exposed")
                    index+=1
                self.rooms[loc[0]].leave(agentId)
                self.rooms[loc[1]].enter(agentId)
    # fin
    def initialize_infection(self):
        """
            iniitilize the infection, start people off as susceptible
        """
        for agentId in self.agents.keys():
            # negative value for durration means the state will persist on to infinity
            self.changeStateDict(agentId, "susceptible", "susceptible")
        seedNumber = self.config["infectionSeedNumber"]
        seededState = self.config["infectionSeedState"]
        infectedAgentIds = np.random.choice(list(self.agents.keys()),size=seedNumber, replace=False)
        for agentId in infectedAgentIds:
            self.changeStateDict(agentId, "susceptible",seededState)
        debugTempDict = dict()
        for agentId in infectedAgentIds:
            debugTempDict[self.agents[agentId].Agent_type] = debugTempDict.get(self.agents[agentId].Agent_type, 0) + 1
        print(f"{seedNumber} seeds starting off with {seededState}, {debugTempDict.keys()}")
    # fin
    def hub_infection(self):
        randVec = np.random.random(len(self.state2IdDict["susceptible"]))
        index = 0
        for roomId, room in self.rooms.items():
            if room.room_name.endswith("_hub") and room.building_type != "offCampus":
                totalInfection = self.infectionInRoom(roomId)
                for  agentId in room.agentsInside:
                    if self.agents[agentId].state == "susceptible":
                        coeff = 1
                        if self.agents[agentId].compliance: # check for compliance
                            if self.rooms[roomId].building_type in self.config["nonMaskBuildingType"]:
                                coeff = self.maskP
                    
                        if randVec[index] < coeff*totalInfection:
                            self.changeStateDict(agentId,"susceptible", "exposed")
                            room.infectedNumber+=1
                            index+=1
                            print(f"at time {self.time}, in {(roomId, room.room_name)}, 1 got infected by the comparison randomValue < {totalInfection}. Kv is {room.Kv}, limit is {room.limit},  {len(room.agentsInside)} people in room ")

    # fin                 
    def infection(self):
        """
            the actual function that takes care of the infection
            goes over rooms and check if an infected person is inside and others were infected
        """
        # time it takes to transition states, negative means, states doesnt change
        if len(self.state2IdDict["recovered"]) != len(self.agents):
            transition = self.config["transitionTime"]
            transitionProbability = self.config["transitionProbability"]
            randVec = np.random.random(len(self.state2IdDict["susceptible"]))
            randVec2 = np.random.random(len(self.state2IdDict["exposed"]) + len(self.state2IdDict["infected Asymptomatic"]))
            index1, index2 = 0, 0
            for roomId, room in self.rooms.items():
                if room.building_type != "offCampus":
                    totalInfection = self.infectionInRoom(roomId)
                    if totalInfection > 0:
                        for agentId in room.agentsInside:
                            if self.agents[agentId].state == "susceptible":
                                coeff = 1
                                if self.agents[agentId].compliance: # check for compliance
                                    if self.rooms[roomId].building_type in self.config["nonMaskBuildingType"]:
                                        coeff = self.maskP
                                
                                if randVec[index1] < coeff*totalInfection:
                                    self.changeStateDict(agentId,"susceptible", "exposed")
                                    room.infectedNumber+=1
                                    index1+=1
                                    contribution = self.infectionWithinPopulation(self.rooms[roomId].agentsInside, roomId)
                                    print(f"at time {self.time}, in {(roomId, room.room_name)}, 1 got infected by the comparison randomValue < {totalInfection}. Kv is {room.Kv}, limit is {room.limit},  {len(room.agentsInside)} people in room, contrib: {contribution}")
                               
                # this loop takes care of agent's state transitions
                for agentId in room.agentsInside:   
                    state = self.agents[agentId].state
                    if self.agents[agentId].transitionTime() < self.time and state == "quarantined":
                        # go back to the susceptible state, because the agent was never infected, just self isolated
                        # or recovered from infection during quarantine
                        exitState = "recovered" if self.agents[agentId].infected else "susceptible" 
                        self.changeStateDict(agentId, "quarantined", exitState)
                    elif self.agents[agentId].transitionTime() < self.time and state != "quarantined" and state != "susceptible" and transition[state] > 0:
                        cdf = 0
                        if False and (agentId in self.R0_agentIds):
                                # only for R0, go to the worst case scenario, exposed --> infected Asymptomatic --> infected Symptomatic Mild
                            tup = transitionProbability[state][0]
                            self.changeStateDict(agentId, self.agents[agentId].state, tup[0])
                        else:
                            if len(transitionProbability[state]) > 1:
                                
                                for tup in transitionProbability[state]:
                                    if tup[1] > randVec2[index2] > cdf:
                                        cdf+=tup[1]
                                        nextState = tup[0]
                                index2+=1
                            else:
                                nextState = transitionProbability[state][0][0]

                            self.changeStateDict(agentId, self.agents[agentId].state, nextState)

    # fin                               
    def infectionInRoom(self, roomId):
        """find the total infectiousness of a room by adding up the contribution of all agents in the room"""
        contribution = self.infectionWithinPopulation(self.rooms[roomId].agentsInside, roomId)
        if self.rooms[roomId].building_type == "social" and not self.rooms[roomId].room_name.endswith("_hub"): # check for division by zero
            if len(self.rooms[roomId].agentsInside) == 0:
                return 0
            cummulativeFunc = (self.config["baseP"]*2*contribution)/(5*int(len(self.rooms[roomId].agentsInside)/5+1))
        else:
            cummulativeFunc = (self.config["baseP"]*self.rooms[roomId].Kv*contribution)/self.rooms[roomId].limit
        return cummulativeFunc

    # fin
    def infectionWithinPopulation(self, agentIds, roomId=None):
        contribution = 0
        for agentId in agentIds:
            lastUpdate = self.agents[agentId].lastUpdate
            individualContribution =  self.infectionContribution(agentId, lastUpdate)
            if self.facemaskIntervention and self.agents[agentId].compliance:
                if roomId!=None:
                    #if self.rooms[roomId].building_type in self.config["nonMaskExceptionHub"]
                    if roomId == -1:
                        individualContribution*=self.maskP 
                    elif self.rooms[roomId].building_type in self.config["nonMaskBuildingType"] and not self.rooms[roomId].room_name.endswith("_hub"):
                        individualContribution*=self.maskP 
                else:
                    individualContribution*=self.maskP   
            elif self.facemaskIntervention:
                if roomId!=None:
                    individualContribution*=self.maskP 
                elif self.rooms[roomId].building_type not in self.config["semiMaskBuilding"]:
                    individualContribution*=self.maskP   

            contribution+= individualContribution
        return contribution

    # fin
    def infectionContribution(self, agentId, lastUpdate):
        """return the contribution to the infection for a specific agent"""
        if self.R0: 
            if agentId in self.R0_agentIds:
                return self.config["infectionContribution"].get(self.agents[agentId].state, 0)
        else: 
            return self.config["infectionContribution"].get(self.agents[agentId].state, 0)
        return 0

    # fin
    def countWithinAgents(self, agentList, stateVal, attrName="state"):
        return len(list(filter(lambda x: getattr(x, attrName) == stateVal, [self.agents[val] for val in agentList]))) 

    # fin
    def countAgents(self, stateVal, attrName="state"):
        return len(list(filter(lambda x: getattr(x, attrName) == stateVal, self.agents.values() )))

    # fin
    def printRelevantInfo(self):
        """ print relevant information about the model and its current state, 
        this is the same as __str__ or __repr__, but this function is for debug purpose,
        later on this functio n will be converted to the proper format using __repr__"""
        
        stateList = [state for stateGroup in self.config["AgentPossibleStates"].values() for state in stateGroup]
        num = [self.countAgents(state) for state in stateList]
        def trunk(words):
            wordList = words.split()
            newWord = [a[:4] for a in wordList]
            return " ".join(newWord)

        stateListTrunked = []
        for state, number in zip(stateList, num):
            stateListTrunked.append(":".join([trunk(state), str(number)]))
        print(f"time: {self.time}, states occupied: {' | '.join(stateListTrunked)}")
    
    # fin
    def initializeStoringParameter(self, listOfStatus, steps=10):
        """
            tell the code which values to keep track of. 
            t defines the frequency of keeping track of the information
        """
        self.storeVal = True
        self.timeIncrement = steps 
        self.parameters = dict((stateName, []) for stateList in self.config["AgentPossibleStates"].values() for stateName in stateList)    
        self.timeSeries = []

    # fin
    def storeInformation(self):
        self.timeSeries.append(self.time)
        for param in self.parameters.keys():
            self.parameters[param].append(len(self.state2IdDict[param]))

    # fin
    def returnStoredInfo(self):
        return self.parameters

    # fin
    def returnMassInfectionTime(self):
        counts = np.zeros(len(self.parameters["recovered"]))
        massInfectionTime = 0
        for state in ["recovered", "infected Asymptomatic", "infected Asymptomatic Fixed", "infected Symptomatic Mild", "infected Symptomatic Severe"]:
                for row in self.parameters[state]:
                    counts+=np.array(row)
        
        for index, count in enumerate(counts):
            if count > len(self.agents)*self.config["massInfectionRatio"]:
                massInfectionTime = index
                break
        return massInfectionTime

    # fin
    def visualOverTime(self, boolVal = True, savePlt=False, saveName="defaultpic.png"):
        """
        Parameters:
        - boolVal
        - saveName
        """
        if boolVal:
            data = dict()
            print(list(self.parameters.keys()))
            
            data["Total infected"] = np.zeros(len(self.parameters[list(self.parameters.keys())[0]]))
            for key in self.parameters.keys():
                if key in ["susceptible", "quarantined", "recovered"]:
                    data[key] = self.parameters[key]
                elif key not in self.config["AgentPossibleStates"]["debugAndGraphingPurpose"]: #ignore keys with debug purpose add the rest to infection count
                    data["Total infected"]+=np.array(self.parameters[key])
            data["recovered"] = self.parameters["recovered"]
        else:
            data = {k:v for k,v in self.parameters.items() if k not in self.config["AgentPossibleStates"]["debugAndGraphingPurpose"]}
        data["susceptible"] = np.array(self.parameters["falsePositive"]) + np.array(data["susceptible"])    
        print([(key, value[-1]) for key, value in data.items()])
        vs.timeSeriesGraph(self.timeSeries, (0, self.time+1), (0,len(self.agents)), data, savePlt=savePlt, saveName=saveName, animatePlt=False)
    
    # fin
    def visualizeBuildings(self):
        pairs = [(room, adjRoom[0]) for room, adjRooms in self.adjacencyDict.items() for adjRoom in adjRooms]
        nameDict = dict((roomId, room.room_name) for roomId, room in self.rooms.items())
        vs.makeGraph(self.rooms.keys(), nameDict, pairs, self.buildings, self.roomsInBuilding, self.rooms)

    def getBuilding(self, buildingAttribute, attributeVal):
        return [buildingId for buildingId, building in self.buildings.items() if getattr(building, buildingAttribute) == attributeVal]

    # fin
    def initializeInterventionsAndPermittedActions():
        def inInterventions(interventionName):
            return True if interventionName.lower() in [intervention.lower() for intervention in self.config["World"]["TurnedOnInterventions"]] else False
        
        printStr = "the following interventions are turned on: "
        self.faceMask_intervention = inInterventions("FaceMask")
        self.walkIn = True if "walkin" in self.config["World"]["permittedAction"] else False
        self.quarantine_intervention = inInterventions("Quarantine")
        self.closedBuilding_intervention = inInterventions("ClosingBuildings")
        self.hybridClass_intervention = inInterventions("HybridClasses")

    def InitializeIntervention(self):
        interventionIds, description = self.config["interventions"], []
        for i in interventionIds:
            if i == 1: # face mask
                description.append("face masks")
                self.maskP = self.config["maskP"]
                self.facemaskIntervention = True
                self.facemask_startTime = 0
                self.agentAssignBool(self.config["complianceRatio"], "compliance")
            elif i == 3:
                # test for covid and quarantine
                self.quarantineIntervention = True
                self.quarantineInterval = self.config["quarantineInterval"]
                self.createTestingGroup()
            elif i == 4:
                self.buildingClosure = True
                self.closedLocation = self.config["closedBuildings"]
                self.closeBuildings()
                self.closeLeafOpenHub()
            elif i == 5:
                self.officeHours = False
            elif i == 6:
                self.largeGathering= False
        print("finished initializing interventions")

    def closeBuildings(self):
        library = self.findMatchingRooms("building_type", "library")
        gym =  self.findMatchingRooms("building_type", "gym") 
        #badLocations = library + gym
        badLocations = gym
        for agentId, agent in self.agents.items():
            for i, row in enumerate(agent.schedule):
                for j, item in enumerate(row):
                    if item in badLocations:
                        self.agents[agentId].schedule[i][j] = agent.initial_location

    def closeBuilding(self):
        for building in self.buildings.values():
            if building.building_type == "office":
                for roomId in building.roomsInside:
                    self.rooms[roomId].Kv = 0

    def hybridCourse(self):
        for roomId, room in self.rooms.items():
            if 1:
                pass
    
    def closeLeafOpenHub(self):
        """
            This function close down buildings, but keeps Hubs open, for buildings listed in the "openHub" entry in the config
            leafs of the building are closed by dialing Kv to 0, meaning agents who visit the rooms cant get infected, but the hub is unchanged,
            so the agents can go to the room without the fear of getting infected, but infection is turned on for the hub. 

            Parameters:
            - None
        """
        openHubLoc = self.config["openHub"]
        for buildingType in openHubLoc:
            roomIds = self.findMatchingRooms("building_type", buildingType)
            for roomId in roomIds:
                self.rooms[roomId].Kv = 0

    # fin
    def createTestingGroup(self):
        print("start quarantine Groups")
        if self.config["quarantineRandomSubGroup"]: # do nothing if quarantine screening is with random samples from the population
            self.groupIds = [agentId for agentId, agent in self.agents.items() if agent.Agent_type != "faculty"]
        else: # the population is split in smaller groups and after every interval we cycle through the groups in order and screen each member in the group
            totalIds = set([agentId for agentId, agent in self.agents.items() if agent.archetype == "student"])
            size = len(self.agents)
            # the size of the group, if there's a remainder, then they all get grouped together
            
            self.groupIds = []
            while len(totalIds) > 0:
                sampledIds = np.random.choice(list(totalIds), size=min(len(totalIds), self.config["quarantineSampleSize"]),replace=False)
                totalIds -= set(sampledIds)
                self.groupIds.append(list(sampledIds))
      
            self.quarantineGroupNumber, self.quarantineGroupIndex = len(self.groupIds), 0
    
    # fin
    def final_check(self):
        """
            used to print relevant inormation
        """
        # type and count dictionary
        buildingTCdict = dict()
        for buildingId, building in self.buildings.items():
            buildingCount = 0
            for roomId in building.roomsInside:
                buildingCount+=self.rooms[roomId].infectedNumber
            buildingTCdict[building.building_type] = buildingTCdict.get(building.building_type, 0)+buildingCount 
            print(building.building_name, building.building_type, buildingCount)
        
        print("*"*20, "abstactly represented location:")
        print("large gathering", self.gathering_count)
        print("office hour count", self.officeHourCount)
        print("*"*20, "breakdown for specific rooms:")
        for building in self.buildings.values():
            if building.building_type == "dining":
                for roomId in building.roomsInside:
                    if "faculty" in self.rooms[roomId].room_name:
                        print(f"in {self.rooms[roomId].room_name}, there were {self.rooms[roomId].infectedNumber} infection")
        print("*"*20, "filtering by building type:")
        
        for buildingType, count in buildingTCdict.items():
            print(buildingType, count)
       
        agentTypeDict = dict()
        for agentId, agent in self.agents.items():
            if agent.state != "susceptible":
                agentTypeDict[agent.Agent_type] = agentTypeDict.get(agent.Agent_type, 0) + 1
        print("*"*20, "# infected based on type")
        print(agentTypeDict.items())
        totalExposed = len(self.agents) - self.parameters["susceptible"][-1] - self.parameters["falsePositive"][-1]
        
        data = dict()
        data["TotalInfected"] = np.zeros(len(self.parameters[list(self.parameters.keys())[0]]))
        for key in self.parameters.keys():
            if key in ["susceptible", "quarantined", "recovered"]:
                data[key] = self.parameters[key]
            elif key not in self.config["AgentPossibleStates"]["debugAndGraphingPurpose"]: #ignore keys with debug purpose add the rest to infection count
                data["TotalInfected"]+=np.array(self.parameters[key])
        
        
        
        maxInfected = max(data["TotalInfected"])
        highestGrowth = "not yet"
        print(f"p: {self.config['baseP']}, R0: {self.R0}, total ever in exposed {totalExposed}, max infected {maxInfected}")
    
    # fin
    def testForDisease(self): 
        """
            This function tests people randomly or by batch, and save the result in the log.  The log is read and with a delay, the agents who are listed in the log is qurantined
            the false positive rate adds uninfected agents to the log.  The false negative rate is related to the number of infected agents that can get a false result (not-infected),
            otherwise they go through the normal screening process and they get added to the log based on their state.

            Parameters:
            - None
        """
        if self.config["quarantineRandomSubGroup"]: # if random
            listOfId = np.random.choice(self.groupIds, size=self.config["quarantineSampleSize"], replace=False)
        else: # we cycle through groups to check infected
            listOfId = self.groupIds[self.quarantineGroupIndex]
            self.quarantineGroupIndex = (self.quarantineGroupIndex+1)% self.quarantineGroupNumber
        size = len(listOfId)
        fpDelayedList, delayedList = [], []
        falsePositiveMask = np.random.random(len(listOfId))
        falsePositiveResult = [agentId for agentId, prob in zip(listOfId, falsePositiveMask) if prob < self.config["falsePositive"] and agentId in self.state2IdDict["susceptible"]]
        normalScreeningId = list(set(listOfId) - set(falsePositiveResult))
        # these people had false positive results and are quarantined
        for agentId in falsePositiveResult:
            fpDelayedList.append(agentId)
            
        falseNegVec = np.random.random(len(normalScreeningId))
        # these are people who are normally screened
        for i, agentId in enumerate(normalScreeningId):
            # double the difficulty to catch Asymptomatic compared to symptomatic
            coeff = 1 if self.agents[agentId].state != "infected Asymptomatic Fixed" else 2
            if self.agents[agentId].state in self.config["AgentPossibleStates"]["infected"]:
                if falseNegVec[i] > coeff*self.config["falseNegative"]: # infected and not a false positive result
                    delayedList.append(agentId)


        self.falsePositiveList.append(fpDelayedList)
        self.quarantineList.append(delayedList)
     #
    
    # fin
    def delayed_quarantine(self): 
        """
            the people who gets a mandatory testing will get their results in t time (t=0 means the result are given without any delay),
            in the testing phase, the agents are tested and the people who had false positive result and people with the covid is quarantined
            The agents are put in the quarantine state after a delay, and if the delay > time between successive testing, then there's a backlog with the resultsbeing returned. 
            since the testing and isolating based on the results could have a delay, I use a FIFO queue, meaning you get the results for the 1st group first, then 2nd, then 3rd, ....

            Parameters:
            - None
        """
        # if its the right time to give the results back to the agents  
        if self.quarantineIntervention and (self.time-self.config["quarantineDelay"])%self.quarantineInterval == 0 and self.time > self.config["quarantineOffset"]:
            if len(self.quarantineList) > 0:  # if the number of agent to isolate/quarantine is greater than zero
                quarantined_agent = self.quarantineList.pop(0) # get the test result for the first group in the queue
                falsePos_agent = self.falsePositiveList.pop(0)
                print(f"at time: {self.time}, {self.config['quarantineDelay']} hour delayed isolation of {len(quarantined_agent) + len(falsePos_agent)} agents, there are {len(self.quarantineList)} group backlog")
                for agentId in quarantined_agent:
                    self.changeStateDict(agentId, self.agents[agentId].state, "quarantined")
                for agentId in falsePos_agent:
                    self.changeStateDict(agentId, self.agents[agentId].state, "quarantined")
                    self.addFalsePositive(agentId)

    # fin           
    def checkForWalkIn(self):
        """
        when its 8AM, agents with symptoms will walkin for a check up, the probability that they will walkin differs based on how severe it is.

        Parameters:
        - None
        """
        if self.walkIn: # if people have a tendency of walkins and if it's 8AM
            mild, severe = self.state2IdDict["infected Symptomatic Mild"], self.state2IdDict["infected Symptomatic Severe"] 
            for agentId in mild|severe: # union of the two sets
                if self.agents[agentId].lastUpdate+23 > self.time: # people walkin if they seen symptoms for a day
                    # with some probability the agent will walkin
                    tupP = np.random.random(2) # (P of walking in,  P for false Pos)
                    if tupP[0] < self.config["walkinProbability"].get(self.agents[agentId].state, 0): # walkin occurs
                        if tupP[1] > self.config["falseNegative"]: # no false negatives
                            self.changeStateDict(agentId,self.agents[agentId].state, "quarantined")
                       
if __name__ == "__main__":
    main() 