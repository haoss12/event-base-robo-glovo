import socket
import json
import time
import select
import sys
from statemachine import StateMachine, State

class RobotSM(StateMachine):
    wait_in_field = State()
    travel_to_restaurant = State()
    wait_in_restaurant = State()
    travel_to_client = State()
    wait_in_client = State()
    travel_to_base = State()
    wait_in_base = State(initial=True)

    robot_spawn = wait_in_base.to(wait_in_field, after='robot_spawn')
    robot_return = wait_in_field.to(travel_to_base, after='robot_return')
    robot_returned = travel_to_base.to(wait_in_base, after='robot_returned')

    robot_pick = wait_in_field.to(travel_to_restaurant, after='robot_pick')
    robot_arrived = travel_to_restaurant.to(wait_in_restaurant, after='robot_arrived')
    robot_pick = wait_in_restaurant.to(travel_to_restaurant, after='robot_pick')
    robot_deliver = wait_in_restaurant.to(travel_to_client, after='robot_deliver')
    food_delivered = travel_to_client.to(wait_in_client, after='food_delivered')
    robot_deliver = wait_in_client.to(travel_to_client, after='robot_deliver')
    robot_empty = wait_in_client.to(wait_in_field, after='robot_empty')

    def on_enter_state(self, target, event):
        print(f"Entering {target} from {event}")

class Robot:
    id = 0

    def __init__(self):
        self.id = Robot.id
        self.sm = RobotSM()
        Robot.id +=1

class OrderSM(StateMachine):
    initial = State(initial=True)
    wait_for_food = State()
    wait_for_pick = State()
    wait_for_deliver = State(final=True)

    food_start = initial.to(wait_for_food, after='food_start')
    food_ready = wait_for_food.to(wait_for_pick, after='food_ready')
    food_picked = wait_for_pick.to(wait_for_deliver, after='food_picked')

    def on_enter_state(self, target, event):
        print(f"Entering {target} from {event}")

class Order(StateMachine):
    id = 0

    def __init__(self):
        self.id = Order.id
        self.sm = OrderSM()
        Order.id +=1

    def is_finished():
        return False # TODO

class Supervisor:
    def __init__(self, host, port):
        self.robots = [Robot() for _ in range(3)]
        self.orders = []

    def receive(self, event):
        if event=='new_order':
            self.orders.append(Order())
        else:
            self.sm.send(self.sm_event)

supervisor = Supervisor('localhost', 12345)

event = {
    'id': 'new_order',
    'order_number': 1,
    'restaurant': [1, 2],
    'destination': [4, 5],
    'food': 5,
}
supervisor.receive(event)

#while True:
#    supervisor.send_dict({"message": 'Hello Simulation'})
#    received_data = supervisor.receive_dict()
#    time.sleep(1)
