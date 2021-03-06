import model_framework
import platform
import statfile

def main():
    """intialize and run the model, for indepth detail about the config or how to run the code, go to the github page for this code"""    
    modelConfig = {
        "Agents" : {
            "PossibleStates":{
                "neutral" : ["susceptible", "exposed"],
                "infected" : ["infected Asymptomatic", "infected Asymptomatic Fixed", "infected Symptomatic Mild", "infected Symptomatic Severe"],  
                "recovered" : ["quarantined", "recovered"],
                "debugAndGraphingPurpose": ["falsePositive"],
                },
            "ExtraParameters":[
                        "agentId","path", "destination", "currLocation",
                        "statePersistance","lastUpdate", "personality", 
                        "arrivalTime", "schedule",  "gathering",
                        # "travelTime", "officeAttendee",
                ], # travelTime and officeAttendee will be commented out
            "ExtraZipParameters": [("motion", "stationary"), ("infected", False), ("compliance", False)],
            "booleanAssignment":[ ("gathering", 0.5)], # ("officeAttendee", 0),
            
        },
        "Rooms" : {
            "ExtraParameters": ["roomId","agentsInside","oddCap", "evenCap", "classname", "infectedNumber", "hubCount"],
        },
        "Buildings" : {
            "ExtraParameters": ["buildingId","roomsInside"],
        },
        "Infection" : {
            "baseP" : 1.15,
            "SeedNumber" : 10,
            "SeedState" : "exposed",
            "Contribution" : {
                "infected Asymptomatic":0.5,
                "infected Asymptomatic Fixed":0.5,
                "infected Symptomatic Mild":1,
                "infected Symptomatic Severe":1,
            },
            # INFECTION STATE
            "TransitionTime" : {
                "susceptible" : -1, # never, unless acted on
                "exposed" : 2*24, # 2 days
                "infected Asymptomatic" : 2*24, # 2 days
                "infected Asymptomatic Fixed" : 10*24, # 10 days
                "infected Symptomatic Mild" : 10*24,# 10 Days
                "infected Symptomatic Severe" : 10*24, # 10 days
                "recovered" : -1, # never
                "quarantined" : 24*14, # 2 weeks 
            },
            # INFECTION TRANSITION PROBABILITY
            "TransitionProbability" : {
                "susceptible" : [("exposed", 1)],
                "exposed" : [("infected Asymptomatic", 0.85), ("infected Asymptomatic Fixed", 1)],
                "infected Asymptomatic Fixed": [("recovered", 1)],
                "infected Asymptomatic": [("infected Symptomatic Mild", 0.5), ("infected Symptomatic Severe", 1)],
                "infected Symptomatic Mild": [("recovered", 1)],
                "infected Symptomatic Severe": [("recovered", 1)],
                "quarantined":[("susceptible", 1)],
                "recovered":[("susceptible", 0.5), ("recovered", 1)],
            },
        },
        "World" : {
            "UnitTime" : "Hours",
            # by having the supposed days to be simulated, 
            # we can allocate the required space beforehand to speedup data storing
            "InferedSimulatedDays":100,
            # put the name(s) of intervention(s) to be turned on 
            "TurnedOnInterventions":[],# ["HybridClasses", "ClosingBuildings", "Quarantine", "FaceMasks"], 
            "permittedAction": [],#["walkin"],
            "transitName": "transit_space_hub",
            "offCampusInfectionProbability":0.125/880,
            "massInfectionRatio":0.10,
            "complianceRatio": 0,
            "stateCounterInterval": 5,
            "socialInteraction": 0.15,
            "LazySunday": True,
            "LargeGathering": True,
        },
       
        # interventions
        "FaceMasks" : {
            "MaskInfectivity" : 0.5,
            "MaskBlock":0.75,
            "NonCompliantLeaf": ["dorm", "dining", "faculty_dining_hall", "faculty_dining_room"],
            "CompliantHub" : ["dorm", "dining"],
            "NonCompliantBuilding" : ["social", "largeGathering"],
        },
        "Quarantine" : {
            # this dictates if we randomly sample the population or cycle through Batches
            "RandomSampling": False,
            "RandomSampleSize": 100,
            # for random sampling from the agent population
            "SamplingProbability" : 0,
            "ResultLatency":2*24,
            "walkinProbability" : {
                "infected Symptomatic Mild": 0.7, 
                "infected Symptomatic Severe": 0.95,
                },
            "BatchSize" : 100,
            "ShowingUpForScreening": 1,
            "offset": 9, # start at 9AM
            "checkupFrequency": 24*1,
            "falsePositive":0.001,
            "falseNegative":0#0.03,
        },
        "ClosingBuildings": {
            "ClosedBuildingOpenHub" : [],
            # close buildings in the list(remove them from the schedule), and go home or go to social spaces 
            "ClosedBuilding_ByType" : ["gym", "library"],
            "GoingHomeP": 0.5,
            # the building in the list will be removed with probability and replaced with going home, otherwise it stays
            "Exception_SemiClosedBuilding": [],
            "Exception_GoingHomeP":0.5,
            
        },
        "HybridClass":{
            "RemoteStudentCount": 1000,
            "RemoteFacultyCount": 180,
            "RemovedDoubleCount": 0,
            "OffCampusCount": 500,
            "TurnOffLargeGathering": True,
            "ChangedSeedNumber": 10,
        },
        "LessSocializing":{
            "SocializingProbability":0.5
        }

    }
  
    # you can control for multiple interventions by adding a case:
    #  [(modified attr1, newVal), (modified attr2, newVal), ...]

    # simulation name --> simulation controlled variable(s)
    # dont use . or - in the simulation name because the names are used to save images, or any symbols below
    """
        < (less than)
        > (greater than)
        : (colon - sometimes works, but is actually NTFS Alternate Data Streams)
        " (double quote)
        / (forward slash)
        \ (backslash)
        | (vertical bar or pipe)
        ? (question mark)
        * (asterisk)
    """
    """
    high setting
    
    
    
    
    """


    ControlledExperiment = {
        "baseModel":{}, # no changes
        "facemasks_f1":{
            "World": [
                ("TurnedOnInterventions", ["FaceMasks"]),
                ("ComplianceRatio", 1),
                ],
        },
        "high_dedensification":{
            "World": [
                ("TurnedOnInterventions", ["HybridClasses"]),
                ],
            "HybridClass":[
                ("RemoteStudentCount", 1000),
                ("RemoteFacultyCount", 300),
                ("RemovedDoubleCount", 525),
                ("OffCampusCount", 500),
                ("TurnOffLargeGathering", True),
                ("ChangedSeedNumber", 5),
            ], 
        },
        "lessSocial":{
            "World": [
                ("TurnedOnInterventions", ["LessSocial"]),
                ],
        },
        "Minimal": {
            "World": [
                ("TurnedOnInterventions", ["FaceMasks", "Quarantine"]),
                ("ComplianceRatio", 0.5),
                ],
            "Quarantine": [
                ("ResultLatency", 2*24), 
                ("BatchSize", 100),
                ("ShowingUpForScreening", 0.8),
                ],
        }, 
        "Moderate": {
            "World": [
                ("TurnedOnInterventions", ["FaceMasks", "Quarantine", "ClosingBuildings"]),
                ("ComplianceRatio", 0.5)
            ],
            "Quarantine": [
                ("ResultLatency", 2*24), 
                ("BatchSize", 250),
                ( "ShowingUpForScreening", 0.8),
                ],
            "ClosingBuildings": [
                ("ClosedBuildingType", ["gym", "library"]),
                ("GoingHomeP", 0.5),
            ]
        }, 
        "Strong":{
            "World": [
                ("TurnedOnInterventions", ["FaceMasks", "Quarantine", "ClosingBuildings","HybridClasses", "LessSocial"]),
                ("ComplianceRatio", 1),
                ("LargeGathering", False),
            ],
            "Quarantine": [
                ("ResultLatency", 2*24), 
                ("BatchSize", 500),
                ( "ShowingUpForScreening", 1),
            ],
            "ClosingBuildings": [
                ("ClosedBuildingType", ["gym", "library", "office"]),
                ("ClosedBuildingOpenHub", ["dining"]),
                ("GoingHomeP", 1),
            ],
            "HybridClass":[
                ("RemoteStudentCount", 1000),
                ("RemoteFacultyCount", 300),
                ("RemovedDoubleCount", 525),
                ("OffCampusCount", 500),
                ("TurnOffLargeGathering", True),
                ("ChangedSeedNumber", 5),
            ],
        },    
        "Strong_lessTesting":{
            "World": [
                ("TurnedOnInterventions", ["FaceMasks", "Quarantine", "ClosingBuildings","HybridClasses", "LessSocial"]),
                ("ComplianceRatio", 1),
                ("LargeGathering", False),
            ],
            "Quarantine": [
                ("ResultLatency", 2*24), 
                ("BatchSize", 250),
                ( "ShowingUpForScreening", 1),
            ],
            "ClosingBuildings": [
                ("ClosedBuildingType", ["gym", "library", "office"]),
                ("ClosedBuildingOpenHub", ["dining"]),
                ("GoingHomeP", 1),
            ],
            "HybridClass":[
                ("RemoteStudentCount", 1000),
                ("RemoteFacultyCount", 300),
                ("RemovedDoubleCount", 525),
                ("OffCampusCount", 500),
                ("TurnOffLargeGathering", True),
                ("ChangedSeedNumber", 5),
            ],
        },
        "Strong_lessFaceMask":{
            "World": [
                ("TurnedOnInterventions", ["FaceMasks", "Quarantine", "ClosingBuildings","HybridClasses", "LessSocial"]),
                ("ComplianceRatio", 0),
                ("LargeGathering", False),
            ],
            "Quarantine": [
                ("ResultLatency", 2*24), 
                ("BatchSize", 500),
                ( "ShowingUpForScreening", 1),
            ],
            "ClosingBuildings": [
                ("ClosedBuildingType", ["gym", "library", "office"]),
                ("ClosedBuildingOpenHub", ["dining"]),
                ("GoingHomeP", 1),
            ],
            "HybridClass":[
                ("RemoteStudentCount", 1000),
                ("RemoteFacultyCount", 300),
                ("RemovedDoubleCount", 525),
                ("OffCampusCount", 500),
                ("TurnOffLargeGathering", True),
                ("ChangedSeedNumber", 5),
            ],
        },
        "Strong_moreSocial":{
            "World": [
                ("TurnedOnInterventions", ["FaceMasks", "Quarantine", "ClosingBuildings","HybridClasses"]),
                ("ComplianceRatio", 1),
                ("LargeGathering", False),
            ],
            "Quarantine": [
                ("ResultLatency", 2*24), 
                ("BatchSize", 500),
                ( "ShowingUpForScreening", 1),
            ],
            "ClosingBuildings": [
                ("ClosedBuildingType", ["gym", "library", "office"]),
                ("ClosedBuildingOpenHub", ["dining"]),
                ("GoingHomeP", 0.5),
            ],
            "HybridClass":[
                ("RemoteStudentCount", 1000),
                ("RemoteFacultyCount", 300),
                ("RemovedDoubleCount", 525),
                ("OffCampusCount", 500),
                ("TurnOffLargeGathering", True),
                ("ChangedSeedNumber", 5),
            ],
        },
        "Strong_openDiningHall":{
            "World": [
                ("TurnedOnInterventions", ["FaceMasks", "Quarantine", "ClosingBuildings","HybridClasses"]),
                ("ComplianceRatio", 1),
                ("LargeGathering", False),
            ],
            "Quarantine": [
                ("ResultLatency", 2*24), 
                ("BatchSize", 500),
                ( "ShowingUpForScreening", 1),
            ],
            "ClosingBuildings": [
                ("ClosedBuildingType", ["gym", "library", "office"]),
                ("ClosedBuildingOpenHub", []),
                ("GoingHomeP", 1),
            ],
            "HybridClass":[
                ("RemoteStudentCount", 1000),
                ("RemoteFacultyCount", 300),
                ("RemovedDoubleCount", 525),
                ("OffCampusCount", 500),
                ("TurnOffLargeGathering", True),
                ("ChangedSeedNumber", 5),
            ],
        },
        "Strong+LargeGathering":{
            "World": [
                ("TurnedOnInterventions", ["FaceMasks", "Quarantine", "ClosingBuildings","HybridClasses"]),
                ("ComplianceRatio", 1),
                ("LargeGathering", True),
            ],
            "Quarantine": [
                ("ResultLatency", 2*24), 
                ("BatchSize", 500),
                ( "ShowingUpForScreening", 1),
            ],
            "ClosingBuildings": [
                ("ClosedBuildingType", ["gym", "library", "office"]),
                ("ClosedBuildingOpenHub", ["dining"]),
                ("GoingHomeP", 1),
            ],
            "HybridClass":[
                ("RemoteStudentCount", 1000),
                ("RemoteFacultyCount", 300),
                ("RemovedDoubleCount", 525),
                ("OffCampusCount", 500),
                ("TurnOffLargeGathering", False),
                ("ChangedSeedNumber", 5),
            ],
        },
    }
    R0_controls = {
        "justFacemask": {
            "World": [
                ("TurnedOnInterventions", ["FaceMasks"]),
                ("ComplianceRatio", 1),  
            ],
            },
        "justquarantine":{
            "World": [
                ("TurnedOnInterventions", ["Quarantine"]),
           
            ],
        },
        "closingbuilding":{
            "World": [
                ("TurnedOnInterventions", [ "ClosingBuildings"]),
     
            ],
        },
        "hybrid":{"World": [
                ("TurnedOnInterventions", ["HybridClasses"]),
            
            ],
            },
        "lessSocial":{
            "World": [
                ("TurnedOnInterventions", [ "LessSocial"]),
        
            ],
        },
    }
    R0Dict = dict()
    InfectedCountDict = dict()
    simulationGeneration = "5"
    osName = platform.system()
    files = "images\\" if osName.lower() == "windows" else "images/"
    for index, (modelName, modelControl) in enumerate(ControlledExperiment.items()):
        configCopy = dict(modelConfig)
        print("*"*20)
        print(f"started working on initializing the simualtion for {modelName}")
        for categoryKey, listOfControls in modelControl.items():
            for (specificKey, specificValue) in listOfControls:
                configCopy[categoryKey][specificKey] = specificValue
        R0Count = 100 if index < 1 else 40
        multiCounts = 20
        if True or index in []: 
            typeName = "p_" + str(configCopy["Infection"]["baseP"]) + "_"
            modelName=typeName+modelName+"_"+str(simulationGeneration)
            #model_framework.simpleCheck(configCopy, days=100, visuals=True, debug=False, modelName=files+modelName)
            #InfectedCountDict[modelName] = model_framework.multiSimulation(multiCounts, configCopy, days=100, debug=False, modelName=files+modelName) 
            R0Dict[modelName] = model_framework.R0_simulation(modelConfig, R0_controls,R0Count, debug=True, timeSeriesVisual=False, R0Visuals=True, modelName=modelName)
            # the value of the dictionary is ([multiple R0 values], (descriptors, (tuple of useful data like mean and stdev)) 
    print(InfectedCountDict.items())
    print(R0Dict.items())
    
    if True:
        saveName = "comparingModels_"+simulationGeneration
        labels = []
        R0data = []
        R0AnalyzedData = []
        for key, value in R0Dict.items():
            labels.append(key)
            R0data.append(value[0])
            R0AnalyzedData.append(value[1]) 
        statfile.boxplot(R0data,oneD=False, pltTitle="R0 Comparison (box)", xlabel="Model Name",
             ylabel="Infected people (R0)", labels=labels, savePlt=True, saveName="R0_box_"+saveName)
        statfile.barChart(R0data, oneD=False, pltTitle="R0 Comparison (bar)", xlabel="Model Name", 
            ylabel="Infected Agents (R0)", labels=labels, savePlt=True, saveName="R0_bar_"+saveName)

        labels = []
        infectedCounts = []
      
        for key, value in InfectedCountDict.items():
            labels.append(key)
            infectedCounts.append(value)
        statfile.boxplot(infectedCounts,oneD=False, pltTitle="Infection Comparison (box)", xlabel="Model Name",
             ylabel="Total Infected Agents", labels=labels, savePlt=True, saveName="infe_box_"+saveName)
        statfile.barChart(infectedCounts, oneD=False, pltTitle="Infection Comparison (bar)", xlabel="Model Name", 
            ylabel="Total Infected Agents", labels=labels, savePlt=True, saveName="infe_bar_"+saveName)
         
if __name__ == "__main__":
    main()