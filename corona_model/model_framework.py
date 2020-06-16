import os
import random
import pandas as pd
import pickle
import file_related as flr
import numpy as np
import bisect
import visualize as vs

def convert_to_min(time_str):
    """convert time represnted in the following forms to minutes in a day, 
        this function is used to decode the schedule in terms of minutes
        1.) military time, xx:xx
        2.) time with Meridiem Indicator (AM/PM), xx:xxAM or xx:xxPM
    """
    meridiem_indicator = time_str[-2:]
    if meridiem_indicator in ["AM", "PM"]: # check if Meridiem Indicator is included
        time_str = time_str[:-2]
    hours, minutes = [int(a) for a in time_str.strip().split(":")]
    if meridiem_indicator == "PM": # if the period is PM, then add 12 hours to the time
            minutes += 60*12
    minutes+= hours*60
    return minutes

def find_tuple(val, item_list, index):
    """ return the first item in the list of tuple that have val in some index withing the tuple"""
    for tup in item_list:
        if tup[index] == val: return tup
    return None

def generate_path(starting_point, destination, adj_dict):
    pass

def main():
    """ the main function that starts the model"""
    # the "config" and "info" are different in that config tells the code what values/range are allowed for a variable.
    # the info are the specific data for a specific instance of the class
    
    file_loc = {
    "config_folder"     : "txt_config",
    "agent_config"      : "agent_config.txt",
    "room_config"       : "room_config.txt",
    "building_config"   : "building_config.txt",
    "schedule_config"   : "schedule_config.txt",
    
    "info_folder"       : "configuration",
    "agent_info"        : "agents.csv",
    "room_info"         : "rooms.csv",
    "building_info"     : "buildings.csv",
    "schedule_info"     : "schedules.csv"
    }
    model = Agent_based_model(file_loc)
    model.initialize_agents()
    model.initialize_storing_parameter(["healthy", "infected", "recovered"])
    model.print_relevant_info()
    for i in range(100):
        model.update_time(10)
        model.print_relevant_info()
        model.store_information()
    model.visual_over_time()
    model.visualize_buildings()
    model.print_relevant_info()
    #if str(input("does all the information look correct?")) in ["T", "t", "y", "Y", "Yes"]:
    #    pass


def agent_class(agent_df, slot_val =  ["name", "age", "gender", "immunity", "curr_location", "motion" "health_state", "archetype", "personality", "arrival_time", "path_to_dest", "waiting_time"]):
    # meta function used to dynamically assign __slots__
    class Agents:
        __slots__ = slot_val
        def __init__(self, values_in_rows):
            for slot, value in zip(self.__slots__, values_in_rows):
                self.__setattr__(slot, value)

        def update_loc(self, curr_time, adj_dict):
            """change between moving and stationary states"""
            threshold = 0.2
            if self.motion == "stationary" and curr_time > self.arrival_time:
                if random.random() < threshold:
                    rooms = list(adj_dict.keys())
                    self.destination =  np.random.choice(rooms, 1)
                    print("destination", self.destination)
                    self.move_to(adj_dict)
            elif self.motion == "moving" and curr_time > self.travel_time + self.arrival_time:
                self.move_to(adj_dict)
                self.arrival_time = curr_time
            else: 
                return (self.curr_location, self.curr_location)

        def move_to(self, adj_dict):
            past_location = self.curr_location
            if find_tuple(self.destination, adj_dict[self.curr_location], 1) != None:
                # the agent reached it's destination, takes a rest
                self.curr_location = self.destination
                self.destination = None
                self.motion = "stationary"
            else: # the agent is still moving
                self.motion = "moving"
                # choose a random room and go to it
                next_partition = np.random.choice(adj_dict[self.curr_location])
                self.travel_time = next_partition[1]
                self.curr_location = next_partition[0]
            return (past_location, self.curr_location)
        
    temp_dict = dict()
    for index, row in agent_df.iterrows():
        temp_dict[index] = Agents(row.values.tolist())
    return temp_dict

def room_class(room_df, slot_val):
    # meta function used to dynamically assign __slots__
    class Partitions:
        __slots__ = slot_val
        def __init__(self, param):
            for slot, value in zip(self.__slots__, param):
                self.__setattr__(slot, value)
    temp_dict = dict()
    for index, row in room_df.iterrows():
        temp_dict[index] = Partitions(row.values.tolist())
    return temp_dict
    
def superstruc_class(struc_df, slot_val):
    class Superstructure: # buildings
        __slots__ = slot_val
        def __init__(self, struc_param):
            for slot, value in zip(self.__slots__, struc_param):
                self.__setattr__(slot, value)

    temp_dict = dict()
    for index, row in struc_df.iterrows():
        temp_dict[index] = Superstructure(row.values.tolist())
    return temp_dict
        
class Agent_based_model:
    def __init__(self, files = {"config_folder" : "configuration", "agent_config" : "agent_config.txt", "room_config" : "room_config.txt", "building_config" : "building_config.txt", "schedule_config" : "schedule_config.txt",
    "info_folder" : "configuration", "agent_info" : "agents.csv", "room_info" : "rooms.csv", "building_info" : "buildings.csv", "schedule_info" :"schedules.csv"}):
        # get the dataframe of individual components
        self.agent_df = flr.make_df(files["info_folder"], files["agent_info"]) 
        self.building_df = flr.make_df(files["info_folder"], files["building_info"]) 
        self.room_df = flr.make_df(files["info_folder"], files["room_info"]) 
        self.schedule_df = flr.make_df(files["info_folder"], files["schedule_info"]) 
        # get the config of the individual components

        # add a column to store the id of agents or rooms inside the strucuture
        self.agent_df["curr_location"] = 0
        self.agent_df["motion"] = 0
        self.agent_df["arrival_time"] = 0
        self.agent_df["travel_time"] = 0
        self.building_df["rooms_inside"] = 0
        self.room_df["agents_inside"] = 0
        self.room_df["limit"] = 20
        print("*"*20)
        self.agent_config = flr.load_config(files["config_folder"], files["agent_config"])
        self.room_config = flr.load_config(files["config_folder"], files["room_config"])
        self.building_config = flr.load_config(files["config_folder"], files["building_config"])
        self.schedule_config = flr.load_config(files["config_folder"], files["schedule_config"])
        self.graph_type = "undirected"
        self.adjacency_dict = self.make_adj_dict()
        self.buildings = self.make_class(self.building_df, superstruc_class)
        self.rooms = self.make_class(self.room_df, room_class)
        self.agents = self.make_class(self.agent_df, agent_class)
        self.time = 0
        self.rooms_in_building = dict((building_id, []) for building_id in self.buildings.keys())
        self.building_name_id = dict((getattr(building, "building_name"), building_id) for building_id, building in self.buildings.items())
        self.room_name_id = dict((getattr(room, "room_name"), room_id) for room_id, room in self.rooms.items())
        self.agents_in_room = dict((room_id, []) for room_id in self.rooms.keys())
        self.add_rooms_to_buildings()
        
        
    def add_rooms_to_buildings(self):
        """add room_id to associated buildings"""
        for room_id, rooms in self.rooms.items():
            self.rooms_in_building[self.building_name_id[rooms.located_building]].append(room_id) 

    def initialize_agents(self):
        # convert agent's location to the corresponding room_id and add the agent's id to the room member
        for rooms in self.rooms.values():
            rooms.agents_inside = []
        for agent_id, agents in self.agents.items():
            initial_location = getattr(agents, "initial_location")
            if initial_location in self.building_name_id.keys():
                # randomly choose rooms from the a building
                possible_rooms = self.rooms_in_building[self.building_name_id[initial_location]]
                location = np.random.choice(possible_rooms)
            elif initial_location in self.room_name_id.keys():
                # convert the location name to the corresponding id
                location = self.room_name_id[initial_location]
            else:
                # either the name isnt properly defined or the room_id was given
                location = initial_location
            agents.curr_location = location
            self.rooms[location].agents_inside.append(agent_id)

    def make_adj_dict(self):
        """ creates an adjacency list implimented with a dictionary"""
        adj_dict = dict()
        for room_id, row in self.room_df.iterrows():
            adj_room = self.room_df.index[self.room_df["room_name"] == row["connected_to"]].tolist()[0]
            travel_time = row["travel_time"]
            adj_dict[room_id] = adj_dict.get(room_id, []) + [(adj_room, travel_time)]
            if self.graph_type == "undirected": 
                adj_dict[adj_room] = adj_dict.get(adj_room,[]) + [(room_id, travel_time)]
        return adj_dict
    
    def make_class(self, df_ref, func):
        slot_val = df_ref.columns.values.tolist()
        temp_dict = func(df_ref, slot_val)
        num_obj, obj_val = len(temp_dict), list(temp_dict.values())
        class_name = obj_val[0].__class__.__name__ if num_obj > 0 else "" 
        print(f"creating {num_obj} {class_name} class objects, each obj will have __slots__ = {slot_val}")
        return temp_dict

    def update_time(self, step = 1):
        """ 
        a function that updates the time and calls other update functions, 
        you can also set how many steps to update"""
        for t in range(step):
            self.time+=1
            self.update_agent()
            self.infection()

    def update_agent(self):
        """call the update function on each person"""
        for agent_id, agent in self.agents.items():
            loc = agent.update_loc(self.time, self.adjacency_dict)
            if loc[0] != loc[1]:
                self.rooms[loc[0]].agents_in_room.remove(agent_id)
                self.rooms[loc[1]].agents_in_room.append(agent_id)

    def count_within_agents(self, agent_list, state_name):
        return len(list(filter(lambda x: x.state == state_name, [self.agents[val] for val in agent_list]))) 

    def count_agents(self, state_name):
        return len(list(filter(lambda x: x.state == state_name, self.agents.values() )))

    def print_relevant_info(self):
        """ print relevant information about the model and its current state, 
        this is the same as __str__ or __repr__, but this function is for debug purpose,
        later on this functio n will be converted to the proper format using __repr__"""
        infected = self.count_agents("infected")
        carrier = self.count_agents("carrier")
        dead = self.count_agents("dead")
        healthy = self.count_agents("healthy")
        recovered = self.count_agents("recovered")
        print(f"time: {self.time} total healthy {healthy} infected: {infected}, carrier: {carrier}, dead: {dead}, recovered: {recovered}")
        #print(f" agent's locations is {list(room.agents_in_room for room in self.room_dict.values())}")
        #print(f"agent's location is {self.room_agent_dict}")
    
    def initialize_storing_parameter(self, list_of_status):
        self.parameters = dict((param, []) for param in list_of_status)
        self.timeseries = []

    def store_information(self):
        self.timeseries.append(self.time)
        for param in self.parameters.keys():
            self.parameters[param].append(self.count_agents(param))

    def visual_over_time(self):
        vs.draw_timeseries(self.timeseries, (0, self.time+1), (0,len(self.agents)), self.parameters)
    
    def visualize_buildings(self):
        if True:
            pairs = [(room, adj_room[0]) for room, adj_rooms in self.adjacency_dict.items() for adj_room in adj_rooms]
            name_dict = dict((room_id, room.room_name) for room_id, room in self.rooms.items())
            vs.make_graph(self.rooms.keys(), name_dict, pairs, self.buildings, self.rooms_in_building)
        

    def infection(self):
        base_p = 0.3 # 0.01
        rand_vect = np.random.random(len(self.agents))
        index = 0
        for room in self.rooms.values():
            total_infected = self.count_within_agents(room.agents_inside, "infected")
            for agent_id in room.agents_inside:
                #print(base_p*total_infected/room.limit)
                if self.agents[agent_id].state == "healthy" and rand_vect[index] < base_p*total_infected/room.limit: 
                    self.agents[agent_id].state = "infected"
                else:
                    state = self.agents[agent_id].state
                    if state == "infected":
                        if rand_vect[index] < 0.05:
                            self.agents[agent_id].state = "recovered"

                index +=1    

    def MMs_queueing_model(self, lambda_val, mean):
        pass

if __name__ == "__main__":
    main()    