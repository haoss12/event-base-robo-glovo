import json
import os
import random
from collections import deque
from enum import Enum

import pygame

from communication import Communication
from render import Renderer


class Objective(Enum):
    IDLE = 0
    PICKING_UP = 1
    GOING_WITH_ORDER = 2
    RETURNING_TO_BASE = 3

# Event Types


class EventType(Enum):
    NEW_ORDER = "new_order"
    SPAWN_COURIER = "robot_spawn"
    RETURN_TO_BASE = "robot_return"
    ARRIVED_AT_BASE = "robot_returned"
    LOW_BATTERY_WARNING = "battery_low"
    BATTERY_DEPLETED = "battery_dead"
    ARRIVED_AT_RESTAURANT = "robot_arrived"
    ROBOT_PICK_FOOD = "robot_pick"
    FOOD_PICKED_UP = "food_picked"
    FOOD_READY = "food_ready"
    DELIVER_FOOD = "robot_deliver"
    FOOD_DELIVERED = "food_delivered"
    BACKPACK_EMPTIED = "robot_empty"  # "plecak_skurwiela_oprozniony"
    FOOD_START = "food_start"


class Robot:
    def __init__(self, robot_id, x, y, battery_range, backpack_capacity, event_queue, road_spacing):
        self.robot_id = robot_id
        self.x = x
        self.y = y
        # zasięg na baterii (np. liczba "kroków")
        self.battery_range = battery_range
        self.current_baterry_range = battery_range
        self.backpack_capacity = backpack_capacity
        self.current_capacity = 0
        self.target_x = None
        self.target_y = None
        self.current_objective = Objective.IDLE
        self.carrying_food = dict()  # Tu można trzymać informacje o jedzeniu
        self.event_queue: EventQueue = event_queue  # Reference to the event queue
        self.orders = {}
        self.road_spacing = road_spacing

    def set_target(self, tx, ty, type: Objective):
        self.target_x = tx
        self.target_y = ty
        self.current_objective = type

    def add_order(self, restaurant, order_number, food):
        self.orders[order_number] = {"restaurant": restaurant, "ready_flag": False, "food": food}

    def set_order_ready(self, order_number):
        self.orders[order_number]["ready_flag"] = True

    def pickup_food(self, restaurant):
        """Add food to backpack, simulating pickup of an order from restaurant"""
        for order_number, order_param in self.orders.items():
            restaurant_location = order_param["restaurant"]
            if restaurant_location != restaurant:
                continue

            if order_param["ready_flag"]:
                food_capacity = order_param["food"]
                if (self.current_capacity + food_capacity) > self.backpack_capacity:
                    raise Exception(
                        f"Supervisor exceeded max capacity for robot #{self.robot_id}")
                self.current_capacity += food_capacity
                self.carrying_food[restaurant] = food_capacity
                self.event_queue.enqueue({
                    "id": EventType.FOOD_PICKED_UP.value,
                    "order_number": order_number,
                    "food": food_capacity,
                    "restaurant": restaurant,
                })

            else:
                self.event_queue.enqueue({
                    "id": EventType.ARRIVED_AT_RESTAURANT.value,
                    "robot_number": self.robot_id,
                    "restaurant": restaurant,
                    "repetition_flag": True,
                })

    def give_food(self, food_id):
        """Remove food from backpack, simulating giving order to customer"""
        removed_capacity = self.carrying_food[food_id]
        self.current_capacity -= removed_capacity
        del self.carrying_food[food_id]

        self.event_queue.enqueue({
            "id": EventType.FOOD_DELIVERED.value,
            "order_number": self.order_number,
            "address": [self.target_x, self.target_y],
        })

        # Generate event: Backpack emptied
        if self.current_capacity == 0:
            self.event_queue.enqueue({
                "id": EventType.BACKPACK_EMPTIED.value,
                "robot_number": self.robot_id
            })

    # def adjust_to_road(self, x, y, road_spacing):
    #     """
    #     Dostosowuje współrzędne (x, y) do najbliższej kratki drogi.
    #     """
    #     x = round(x / road_spacing) * road_spacing
    #     y = round(y / road_spacing) * road_spacing
    #     return x, y

    def move(self):
        """
        Simple "taxi-like" movement (Manhattan distance):
        - If a target is set, we move towards the target along the X-axis first, then along the Y-axis (or vice versa).
        - No obstacle avoidance.
        """
        if self.target_x is not None and self.target_y is not None:
            if self.y < self.target_y:
                self.y += 1
            elif self.y > self.target_y:
                self.y -= 1
            elif self.x < self.target_x:
                self.x += 1
            elif self.x > self.target_x:
                self.x -= 1

            # self.x, self.y = self.adjust_to_road(
            #     self.x, self.y, self.road_spacing)

            # Każdy krok zużywa 1 "jednostkę" baterii
            self.current_baterry_range -= 1

            # Low battery warning
            if self.current_baterry_range <= 0.1 * self.battery_range:
                self.event_queue.enqueue({
                    "id": EventType.LOW_BATTERY_WARNING.value,
                    "robot_id": self.robot_id
                })

            # Sprawdzamy, czy dotarliśmy do celu
            if self.x == self.target_x and self.y == self.target_y:
                # Generate event: Arrived at destination
                if self.current_objective == Objective.PICKING_UP:
                    self.event_queue.enqueue({
                        "id": EventType.ARRIVED_AT_RESTAURANT.value,
                        "robot_number": self.robot_id,
                        "restaurant": [self.target_x, self.target_y],
                        "repetition_flag": False,
                    })
                elif self.current_objective == Objective.GOING_WITH_ORDER:
                    self.event_queue.enqueue({
                        "id": EventType.FOOD_DELIVERED.value,
                        "order_number": 1,
                        "address_xy": [self.target_x, self.target_y],
                    })
                elif self.target_x == 0 and self.target_y == 0 and self.current_objective == Objective.RETURNING_TO_BASE:
                    self.event_queue.enqueue({
                        "id": EventType.ARRIVED_AT_BASE.value,
                        "robot_id": self.robot_id,
                    })

                # Clear target
                self.target_x = None
                self.target_y = None
                self.current_objective = Objective.IDLE

        # Battery depleted
        if self.current_baterry_range <= 0:
            self.event_queue.enqueue({
                "id": EventType.BATTERY_DEPLETED.value,
                "robot_id": self.robot_id
            })


class Restaurant:
    def __init__(self, x, y, event_queue):
        self.restaurant = [x, y]
        self.order_dict = dict()
        self.event_queue: EventQueue = event_queue

    def give_order(self, order_number):
        del self.order_dict[order_number]

    def start_preparing_order(self, food_details, order_number):
        time = random.randint(1, 15)
        self.order_dict[order_number] = [food_details, time]

    def restaurant_tick(self):
        for order_number, order_details in self.order_dict.items():
            if order_details[1] > 0:
                order_details[1] -= 1

                if order_details[1] == 0: # food ready
                    self.event_queue.enqueue({
                    "id": EventType.FOOD_READY.value,
                    "order_number": order_number,
                    "restaurant": self.restaurant,
                })



class EventQueue:
    def __init__(self):
        self.queue = deque()

    def enqueue(self, event_dict: dict):
        self.queue.append(event_dict)
        print(f"Added new event of type: {event_dict}")

    def dequeue(self):
        return self.queue.popleft() if self.queue else None

    def is_empty(self):
        return len(self.queue) == 0

    def process_events(self, robots: list[Robot], max_robots, backpack_capacity, next_robot_id, communication: Communication, road_spacing):
        """
        Processes all events in the queue and executes their corresponding logic.

        Args:
            robots (list): List of active robots.
            max_robots (int): Maximum allowed robots in the simulation.
            backpack_capacity (int): Default backpack capacity for new robots.
            next_robot_id (int): ID to assign to the next spawned robot.

        Returns:
            int: Updated next_robot_id value.
        """
        messages_to_send = []

        payload = communication.receive_dict()
        for event in payload:
            event: dict
            self.enqueue(event)

        while not self.is_empty():
            event = self.dequeue()
            event_id = event.get("id", "")

            if event_id == EventType.NEW_ORDER.value:
                messages_to_send.append(
                    event
                )
                print(f"[EVENT] New order: {event}")

            elif event_id == EventType.SPAWN_COURIER.value:
                if len(robots) < max_robots:
                    r = Robot(next_robot_id, 0, 0, event.get(
                        "battery_range", 100), backpack_capacity, self, road_spacing)
                    robots.append(r)
                    print(f"[EVENT] Spawned new courier: ID={next_robot_id}")
                    next_robot_id += 1
                else:
                    print("[EVENT] Maximum number of robots reached.")
                    # TODO: raise it to the supervisor

            elif event_id == EventType.RETURN_TO_BASE.value:
                robot_id = event["robot_id"]
                for r in robots:
                    if r.robot_id == robot_id:
                        r.set_target(0, 0, Objective.RETURNING_TO_BASE)
                        print(f"[EVENT] Robot {robot_id} returning to base.")

            elif event_id == EventType.ARRIVED_AT_BASE.value:
                # NOTE Szpak: Supervisor currently does not use this event
                messages_to_send.append(
                    event
                )
                robot_id = event["robot_id"]
                print(f"[EVENT] Robot {robot_id} arrived at base.")

            elif event_id == EventType.LOW_BATTERY_WARNING.value:
                # NOTE Szpak: Supervisor currently does not use this event
                messages_to_send.append(
                    event
                )
                robot_id = event["robot_id"]
                print(f"[EVENT] Warning: Robot {robot_id} has low battery.")

            elif event_id == EventType.BATTERY_DEPLETED.value:
                # NOTE Szpak: Supervisor currently does not use this event
                robot_id = event["robot_id"]
                messages_to_send.append(
                    event
                )
                print(
                    f"[EVENT] Robot {robot_id} battery depleted. Removing from simulation.")
                robots = [r for r in robots if r.robot_id != robot_id]
                # TODO: handle situation when robot is handling order

            elif event_id == EventType.ARRIVED_AT_RESTAURANT.value:
                robot_id = event["robot_id"]
                restaurant = event["restaurant"]
                if not event["repetition_flag"]:
                    del event["repetition_flag"]
                    messages_to_send.append(
                        event
                    )
                    print(
                        f"[EVENT] Robot {robot_id} arrived at restaurant {restaurant}.")
                for r in robots:
                    if r.robot_id == robot_id:
                        r.pickup_food(restaurant)
                        print(f"[EVENT] Robot {robot_id} trying to pick food from restaurant {restaurant}.")

            elif event_id == EventType.ROBOT_PICK_FOOD.value:
                robot_id = event["robot_number"]
                food = event["food"]
                restaurant = event["restaurant"]
                order_number = event["order_number"]

                for r in robots:
                    if r.robot_id == robot_id:
                        r.set_target(
                            restaurant[0], restaurant[1], Objective.PICKING_UP)
                        r.add_order(restaurant, order_number, food)
                        print(f"[EVENT] Robot {robot_id} picking up food.")

                print(
                    f"[EVENT] Robot pick, robot_id = {robot_id}, food = {food}, restaurant = {restaurant}")

            elif event_id == EventType.FOOD_PICKED_UP.value:
                messages_to_send.append(
                    event
                )
                robot_id = event["robot_id"]
                restaurant_xy = event["restaurant_xy"]
                food_details = event["food"]
                print(
                    f"[EVENT] Robot {robot_id} picked up food from restaurant {restaurant_xy}. Food: {food_details}")

            elif event_id == EventType.FOOD_READY.value:
                restaurant = event["restaurant"]
                order_number = event["order_number"]
                food_details = event["food"]
                for r in robots:
                    if order_number in r.orders.keys():
                        r.set_order_ready(order_number)

                print(
                    f"[EVENT] Food ready for pickup at restaurant {restaurant}. Food: {food_details}")

            elif event_id == EventType.DELIVER_FOOD.value:
                robot_id = event["robot_number"]
                address = event["address"]
                food_details = event["food"]
                for r in robots:
                    if r.robot_id == robot_id:
                        # TODO: Food information is not stored anywhere
                        r.set_target(
                            address[0], address[1], Objective.GOING_WITH_ORDER)
                        print(
                            f"[EVENT] Robot {robot_id} delivering food to {address}. Food: {food_details}")

            elif event_id == EventType.FOOD_DELIVERED.value:
                messages_to_send.append(
                    event
                )
                robot_id = event["robot_id"]
                address_xy = event["address_xy"]
                food_details = event["food"]
                print(
                    f"[EVENT] Robot {robot_id} delivered food to {address_xy}. Food: {food_details}")

            elif event_id == EventType.BACKPACK_EMPTIED.value:
                messages_to_send.append(
                    event
                )
                robot_id = event["robot_id"]
                print(f"[EVENT] Robot {robot_id}'s backpack has been emptied.")

            elif event_id == EventType.FOOD_START.value:
                # TODO
                restaurant = event["restaurant"]
                food_details = event["food"]
                order_number = event["order_number"]
                print(
                    f"[EVENT] Restaurant {restaurant} preparing food. Food: {food_details}, {order_number}")

            else:
                print(
                    f"[EVENT] Unknown event type: {event_id}. Params: {event}")

        communication.send_data(messages_to_send)

        return next_robot_id


def main():
    # 1. Wczytanie konfiguracji
    with open("config.json", 'r', encoding='utf-8') as f:
        config = json.load(f)

    city_size = config["city_size"]  # [width, height], np. [10, 10]
    max_robots = config["max_robots"]  # maks. liczba robotów
    cell_size = config["cell_size"]    # in px
    backpack_capacity = config["backpack_capacity"]
    restaurant_count = config["restaurant_count"]  # liczba restauracji
    road_spacing = 3  # Rozstaw dróg (stały)

    # 2. Inicjalizacja Pygame
    clock = pygame.time.Clock()

    event_queue = EventQueue()

    # 3. Renderer
    renderer = Renderer(city_size, cell_size, restaurant_count)
    restaurants_positions = renderer.get_restaurants()

    restaurants = []
    for x_, y_ in restaurants_positions:
        restaurants.append(Restaurant(x_, y_, event_queue))

    # 4. Communication
    communication = Communication("localhost", 12345)

    # 5. Lista robotów i zmienna do przydzielania ID
    robots = []
    next_robot_id = 0
    order_number = 0

    running = True

    while running:
        # Obsługa zdarzeń Pygame (np. zamknięcie okna)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Generowanie losowych zamówień
        if random.random() < 0.15:  # 5% szansa na tick
            address_x = random.randint(0, city_size[0] - 1)
            address_y = random.randint(0, city_size[1] - 1)

            # Dostosuj adres do drogi
            # address_x, address_y = adjust_to_road(address_x, address_y, road_spacing)

            rest_x, rest_y = random.choice(restaurants)
            # rest_x, rest_y = adjust_to_road(rest_x, rest_y, road_spacing)

            food = {"size": random.randint(1, 3)}
            event_queue.enqueue({
                "id": EventType.NEW_ORDER.value,
                "order_number": order_number,
                "food": food,
                "address": [address_x, address_y],
                "restaurant": [rest_x, rest_y],
            })
            order_number += 1

        # Ruch robotów
        for r in robots[:]:
            r: Robot
            print(f"pos: {r.x}, {r.y}, target: {r.target_x}, {r.target_y}")
            if r.battery_range > 0:
                r.move()
            else:
                print(
                    f"[SIM] Robot {r.robot_id} ma rozładowaną baterię i zostaje usunięty z symulacji.")
                robots.remove(r)

        for restaurant in restaurants:
            restaurant.restaurant_tick()

        # Przetwarzanie zdarzeń
        next_robot_id = event_queue.process_events(
            robots, max_robots, backpack_capacity, next_robot_id, communication, road_spacing)

        # Renderowanie
        renderer.update(robots)
        clock.tick(2)  # 2 FPS – można zmienić w zależności od potrzeb

    pygame.quit()


if __name__ == "__main__":
    main()
