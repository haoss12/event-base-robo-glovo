import pygame
import json
import os
import communication
import simulation
import time
import random


# -------------------------------
# Klasa opisująca robota
# -------------------------------
class Robot:
    def __init__(self, robot_id, x, y, battery_range, backpack_capacity):
        self.robot_id = robot_id
        self.x = x
        self.y = y
        self.battery_range = battery_range  # zasięg na baterii (np. liczba "kroków")
        self.backpack_capacity = backpack_capacity
        self.target_x = None
        self.target_y = None
        self.carrying_food = []  # tu można trzymać informacje o jedzeniu

    def set_target(self, tx, ty):
        self.target_x = tx
        self.target_y = ty

    def move(self):
        """
        Prosty ruch "taksówkowy" (Manhattan distance):
        - Jeśli mamy ustalony target, to idziemy w stronę targetu w osi X, potem w osi Y (lub odwrotnie).
        - Brak omijania przeszkód.
        """
        if self.target_x is not None and self.target_y is not None:
            if self.x < self.target_x:
                self.x += 1
            elif self.x > self.target_x:
                self.x -= 1
            elif self.y < self.target_y:
                self.y += 1
            elif self.y > self.target_y:
                self.y -= 1

            # Każdy krok zużywa 1 "jednostkę" baterii
            self.battery_range -= 1

            # Sprawdzamy, czy dotarliśmy do celu
            if self.x == self.target_x and self.y == self.target_y:
                # Docieramy do celu: można wysłać zdarzenie do supervisora, itp.
                self.target_x = None
                self.target_y = None


# -------------------------------
# Funkcja do wczytywania zdarzeń z events.json
# -------------------------------
def load_events_from_file(events_file):
    if not os.path.exists(events_file):
        return []  # brak pliku => brak zdarzeń
    try:
        with open(events_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # data powinno być listą zdarzeń
            return data
    except:
        return []


# -------------------------------
# Główna pętla symulacji
# -------------------------------
def main():
    # 1. Wczytanie konfiguracji
    with open("config.json", 'r', encoding='utf-8') as f:
        config = json.load(f)

    city_size = config["city_size"]  # [width, height], np. [10, 10]
    max_robots = config["max_robots"]  # maks. liczba robotów
    backpack_capacity = config["backpack_capacity"]
    restaurant_count = config["restaurant_count"]  # liczba restauracji

    # 2. Inicjalizacja Pygame
    pygame.init()
    cell_size = 40  # rozmiar jednej komórki w pikselach
    screen = pygame.display.set_mode((city_size[0] * cell_size, city_size[1] * cell_size))
    pygame.display.set_caption("Symulacja dostaw robotów")

    clock = pygame.time.Clock()

    # 3. Generujemy pozycje restauracji – losowe, ale stałe przez całą symulację.
    #    Moglibyśmy przechowywać je w pliku konfig., ale tu, dla demonstracji, losujemy:
    restaurants = []
    occupied_positions = set()
    # Upewniamy się, że baza (0,0) nie jest zajęta przez restaurację
    occupied_positions.add((0, 0))

    for _ in range(restaurant_count):
        while True:
            rx = random.randint(0, city_size[0] - 1)
            ry = random.randint(0, city_size[1] - 1)
            if (rx, ry) not in occupied_positions:
                restaurants.append((rx, ry))
                occupied_positions.add((rx, ry))
                break

    # 4. Lista robotów i zmienna do przydzielania ID
    robots = []
    next_robot_id = 1

    running = True


    events_to_send = {}
    nwm: any = None
    communication_class = communication.Communication("localhost", 12345)
    simulation_class = simulation.CustomClass()

    while running:
        received_events = communication_class.run(events_to_send)
        idk = simulation_class.run(nwm)


        # Obsługa zdarzeń Pygame (np. zamknięcie okna)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Wczytanie zdarzeń z pliku
        events = load_events_from_file("events.json")

        # Czyścimy plik (aby nie przetwarzać ponownie tych samych zdarzeń):
        if events:
            with open("events.json", 'w', encoding='utf-8') as f:
                json.dump([], f)

        # Obsługa zdarzeń
        for ev in events:
            event_id = ev.get("id")
            params = ev.get("params", {})

            if event_id == 1:
                # spawn nowego kuriera
                # "params": {"battery_range": 10}
                if len(robots) < max_robots:
                    battery_range = params.get("battery_range", 10)
                    r = Robot(next_robot_id, 0, 0, battery_range, backpack_capacity)
                    robots.append(r)
                    print(f"[SIM] Spawn nowego robota o ID={next_robot_id}, zasięg={battery_range}")
                    next_robot_id += 1
                else:
                    print("[SIM] Osiągnięto maksymalną liczbę robotów!")

            elif event_id == 2:
                # powrót kuriera do bazy
                # "params": {"robot_id": 2}
                rid = params.get("robot_id")
                for r in robots:
                    if r.robot_id == rid:
                        r.set_target(0, 0)
                        print(f"[SIM] Robot {rid} wraca do bazy (0,0)")

            elif event_id == 3:
                # zlecenie restauracji gotowania
                # "params": {"restaurant_xy": [2,3], "food_size": 1}
                rest_xy = params.get("restaurant_xy", [0, 0])
                food_size = params.get("food_size", 1)
                print(f"[SIM] Restauracja {rest_xy} gotuje jedzenie (rozmiar={food_size})")

            elif event_id == 4:
                # zlecenie kurierowi odbiór z restauracji
                # "params": {"robot_id": 1, "restaurant_xy": [2,3], "food_size": 1}
                rid = params.get("robot_id")
                rest_xy = params.get("restaurant_xy", [0, 0])
                food_size = params.get("food_size", 1)
                for r in robots:
                    if r.robot_id == rid:
                        r.set_target(rest_xy[0], rest_xy[1])
                        print(f"[SIM] Robot {rid} jedzie do restauracji {rest_xy} (food={food_size})")

            elif event_id == 5:
                # zlecenie kurierowi dowozu do klienta
                # "params": {"robot_id": 1, "address_xy": [5,5], "food_size": 1}
                rid = params.get("robot_id")
                address_xy = params.get("address_xy", [0, 0])
                food_size = params.get("food_size", 1)
                for r in robots:
                    if r.robot_id == rid:
                        r.set_target(address_xy[0], address_xy[1])
                        print(f"[SIM] Robot {rid} dostarcza jedzenie do {address_xy}")

        # Ruch robotów
        for r in robots[:]:  # [:] – aby iterować po kopii listy, bo możemy usuwać
            if r.battery_range > 0:
                r.move()
            else:
                print(f"[SIM] Robot {r.robot_id} ma rozładowaną baterię i zostaje usunięty z symulacji.")
                robots.remove(r)

        # Renderowanie w oknie Pygame
        screen.fill((255, 255, 255))

        # Rysowanie siatki
        for i in range(city_size[0]):
            for j in range(city_size[1]):
                rect = pygame.Rect(i * cell_size, j * cell_size, cell_size, cell_size)
                pygame.draw.rect(screen, (200, 200, 200), rect, 1)

        # Rysowanie bazy (0,0) – np. czerwone kółko
        base_center = (0 * cell_size + cell_size // 2, 0 * cell_size + cell_size // 2)
        pygame.draw.circle(screen, (255, 0, 0), base_center, cell_size // 3)

        # Rysowanie restauracji – np. zielone kwadraty
        for (rx, ry) in restaurants:
            rest_rect = pygame.Rect(rx * cell_size + 5, ry * cell_size + 5, cell_size - 10, cell_size - 10)
            pygame.draw.rect(screen, (0, 200, 0), rest_rect)

        # Rysowanie robotów (kurierów) – np. niebieskie kwadraty
        for r in robots:
            robot_rect = pygame.Rect(r.x * cell_size + 10, r.y * cell_size + 10, cell_size - 20, cell_size - 20)
            pygame.draw.rect(screen, (0, 128, 255), robot_rect)
            # Można też dorysować ID robota, używając np. pygame.font (jeśli potrzeba)

        pygame.display.flip()
        clock.tick(2)  # 2 FPS – można zmienić w zależności od potrzeb

    pygame.quit()


if __name__ == "__main__":
    main()
