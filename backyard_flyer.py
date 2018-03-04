import argparse
import time
from enum import Enum

import numpy as np

from udacidrone import Drone
from udacidrone.connection import MavlinkConnection, WebSocketConnection  # noqa: F401
from udacidrone.messaging import MsgID


class States(Enum):
    MANUAL = 0
    ARMING = 1
    TAKEOFF = 2
    WAYPOINT = 3
    LANDING = 4
    DISARMING = 5


class BackyardFlyer(Drone):

    def __init__(self, connection):
        super().__init__(connection)
        self.target_position = np.array([0.0, 0.0, 0.0])
        self.all_waypoints = []
        self.in_mission = True
        self.check_state = {}

        # initial state
        self.flight_state = States.MANUAL

        # TODO: Register all your callbacks here
        self.register_callback(MsgID.LOCAL_POSITION, self.local_position_callback)
        self.register_callback(MsgID.LOCAL_VELOCITY, self.velocity_callback)
        self.register_callback(MsgID.STATE, self.state_callback)

    def local_position_callback(self):
        """
        TODO: Implement this method

        This triggers when `MsgID.LOCAL_POSITION` is received and self.local_position contains new data
        """
        
        print("Current flight_state is ", self.flight_state)

        # Check flight state
        if States.TAKEOFF == self.flight_state:
        	# coordinate conversion
        	altitude = -1.0 * self.local_position[2]

        	# check if altitude is within 95% of target
        	if altitude > 0.95 * self.target_position[2]:
        		# self.landing_transition()
        		self.all_waypoints = self.calculate_box()
        		self.waypoint_transition()
        	return

        if States.WAYPOINT == self.flight_state:
        	# Check how close the current position to the target position
        	pos_diff = []
        	pos_diff.append(self.target_position[0] - self.local_position[0])
        	pos_diff.append(self.target_position[1] - self.local_position[1])
        	pos_diff.append(self.target_position[2] - abs(self.local_position[2]))

        	print("Current length of all_waypoints",  len(self.all_waypoints))
        	print("Current target_position is ", self.target_position)
        	print("Current local_position is ", self.local_position)
        	print("Current pos_diff is ", pos_diff)

        	if ((-0.5 < pos_diff[0] < 0.5) and
        		(-0.5 < pos_diff[1] < 0.5) and
        		(-0.5 < pos_diff[2] < 0.5)
        	   ):
        		if 0 == len(self.all_waypoints):
        			# Landing after all waypoints being consumed
        			self.landing_transition()
        		else:
        			# Move to next waypoint
        			self.waypoint_transition()

    def velocity_callback(self):
        """
        TODO: Implement this method

        This triggers when `MsgID.LOCAL_VELOCITY` is received and self.local_velocity contains new data
        """

        # Check flight state
        if States.LANDING == self.flight_state:
        	if ((self.global_position[2] - self.global_home[2] < 0.1) and 
        		(abs(self.local_position[2]) < 0.01)
        	   ):
        		self.disarming_transition()

    def state_callback(self):
    	"""
    	TODO: Implement this method

    	This triggers when `MsgID.STATE` is received and self.armed and self.guided contain new data
    	"""
    	if not self.in_mission:
    		return
    	if States.MANUAL == self.flight_state:
    		self.arming_transition()
    	elif States.ARMING == self.flight_state:
    		print("self.armed is ", self.armed)
    		if 1 == self.armed:
    			self.takeoff_transition()
    	elif States.DISARMING == self.flight_state:
    		print("self.armed is ", self.armed)
    		print("self.guided is ", self.guided)
    		if (0 == self.armed) and (0 == self.guided):
    			self.manual_transition()

    def calculate_box(self):
        """TODO: Fill out this method
        
        1. Return waypoints to fly a box
        """
        print("Calculating waypoints")

        # Create your own waypoints
        cur_waypoints = [[15.0, 0.0, 10.0],
        			[15.0, 15.0, 10.0],
        			[0.0, 15.0, 10.0],
        			[0.0, 0.0, 10.0],
        		   ]

        return cur_waypoints

    def arming_transition(self):
        """TODO: Fill out this method
        
        1. Take control of the drone
        2. Pass an arming command
        3. Set the home location to current position
        4. Transition to the ARMING state
        """
        print("arming transition")
        self.take_control()
        self.arm()

        # set the current location to be the home position
        self.set_home_position(self.global_position[0],
        					   self.global_position[1],
        					   self.global_position[2],
        					  )

        self.flight_state = States.ARMING

    def takeoff_transition(self):
        """TODO: Fill out this method
        
        1. Set target_position altitude to 3.0m
        2. Command a takeoff to 3.0m
        3. Transition to the TAKEOFF state
        """
        print("takeoff transition")
        target_altitude = 10.0
        self.target_position[2] = target_altitude
        self.takeoff(target_altitude)
        self.flight_state = States.TAKEOFF

    def waypoint_transition(self):
        """TODO: Fill out this method
    
        1. Command the next waypoint position
        2. Transition to WAYPOINT state
        """
        print("waypoint transition")
        # Return and remove the first element in the waypoint list
        self.target_position = self.all_waypoints.pop(0)

        # Command the drone to move to a specific defined position (in meters) with a specific heading (in radians)
        # In: (north, east, altitude, heading)
        north = self.target_position[0]
        east = self.target_position[1]
        altitude = self.target_position[2]
        heading = 0.0

        self.cmd_position(north, east, altitude, heading)
        self.flight_state = States.WAYPOINT

    def landing_transition(self):
        """TODO: Fill out this method
        
        1. Command the drone to land
        2. Transition to the LANDING state
        """
        print("landing transition")
        self.land()
        self.flight_state = States.LANDING

    def disarming_transition(self):
        """TODO: Fill out this method
        
        1. Command the drone to disarm
        2. Transition to the DISARMING state
        """
        print("disarm transition")
        self.disarm()
        self.release_control()
        self.flight_state = States.DISARMING

    def manual_transition(self):
        """This method is provided
        
        1. Release control of the drone
        2. Stop the connection (and telemetry log)
        3. End the mission
        4. Transition to the MANUAL state
        """
        print("manual transition")

        self.release_control()
        self.stop()
        self.in_mission = False
        self.flight_state = States.MANUAL

    def start(self):
        """This method is provided
        
        1. Open a log file
        2. Start the drone connection
        3. Close the log file
        """
        print("Creating log file")
        self.start_log("Logs", "NavLog.txt")
        print("starting connection")
        self.connection.start()
        print("Closing log file")
        self.stop_log()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5760, help='Port number')
    parser.add_argument('--host', type=str, default='127.0.0.1', help="host address, i.e. '127.0.0.1'")
    args = parser.parse_args()

    conn = MavlinkConnection('tcp:{0}:{1}'.format(args.host, args.port), threaded=False, PX4=False)
    #conn = WebSocketConnection('ws://{0}:{1}'.format(args.host, args.port))
    drone = BackyardFlyer(conn)
    time.sleep(2)
    drone.start()
