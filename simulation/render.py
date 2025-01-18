import random

import pygame


class Renderer:
    def __init__(self, city_size, cell_size, num_restaurants):
        pygame.init()

        self.city_size = city_size  # Size of the city grid (number of tiles)
        self.cell_size = cell_size  # Size of each tile in pixels
        self.num_restaurants = num_restaurants  # Number of restaurants

        # Screen setup
        self.screen = pygame.display.set_mode(
            (city_size[0] * cell_size, city_size[1] * cell_size)
        )
        pygame.display.set_caption("RoboGlovo")

        # Generate buildings and roads
        self.buildings = self.generate_buildings()

    def generate_buildings(self):
        """
        Generate buildings, restaurants, and main roads in the city.
        """
        buildings = {}
        available_positions = [
            (x, y)
            for x in range(self.city_size[0])
            for y in range(self.city_size[1])
        ]

        # Base
        base_position = (0, 0)
        buildings = {base_position: "robot_base"}
        available_positions.remove(base_position)

        # Roads
        road_spacing = 3
        road_positions = [
            (x, y)
            for x in range(self.city_size[0])
            for y in range(self.city_size[1])
            if x % road_spacing == 0 or y % road_spacing == 0
        ]
        for x, y in road_positions:
            if (x, y) != base_position:
                buildings[(x, y)] = "road"


        # Restaurants
        restaurant_positions = random.sample(
            [pos for pos in available_positions if pos not in road_positions],
            self.num_restaurants
        )
        for x, y in restaurant_positions:
            buildings[(x, y)] = "restaurant"


        # Rest of the buildings
        for x, y in available_positions:
            if (x, y) not in buildings:
                buildings[(x, y)] = random.choice(
                    ["house", "block", "skyscraper", "shop"]
                )
        return buildings

    def get_restaurants(self):
        """
        Returns a list of coordinates where restaurants are located.
        """
        restaurants_list = []
        for position, building_type in self.buildings.items():
            if building_type == "restaurant":
                restaurants_list.append(position)
        return restaurants_list

    def draw_road(self, x, y):
        """
        Draws a road with dashed lines separating lanes and crosswalks at intersections.
        """
        base_x = x * self.cell_size
        base_y = y * self.cell_size

        # Road background
        pygame.draw.rect(
            self.screen,
            (60, 60, 60),  # Dark gray for the road
            pygame.Rect(base_x, base_y, self.cell_size, self.cell_size),
        )

        # Dashed centerline for horizontal roads
        if x % 3 != 0:
            for i in range(0, self.cell_size, self.cell_size // 8):
                pygame.draw.line(
                    self.screen,
                    (255, 255, 255),  # White dashed line
                    (base_x + i, base_y + self.cell_size // 2),
                    (base_x + i + self.cell_size // 16, base_y + self.cell_size // 2),
                    2,
                )

        # Dashed centerline for vertical roads
        if y % 3 != 0:
            for i in range(0, self.cell_size, self.cell_size // 8):
                pygame.draw.line(
                    self.screen,
                    (255, 255, 255),  # White dashed line
                    (base_x + self.cell_size // 2, base_y + i),
                    (base_x + self.cell_size // 2, base_y + i + self.cell_size // 16),
                    2,
                )

        # Crosswalk at intersections
        if (
            x % 3 == 0
            and y % 3 == 0
        ):
            for i in range(0, self.cell_size, self.cell_size // 8):
                pygame.draw.line(
                    self.screen,
                    (255, 255, 255),  # White dashed line
                    (base_x + self.cell_size // 2, base_y + i),
                    (base_x + self.cell_size // 2, base_y + i + self.cell_size // 16),
                    2,
                )
            for i in range(0, self.cell_size, self.cell_size // 8):
                pygame.draw.line(
                    self.screen,
                    (255, 255, 255),  # White dashed line
                    (base_x + i, base_y + self.cell_size // 2),
                    (base_x + i + self.cell_size // 16, base_y + self.cell_size // 2),
                    2,
                )

    def draw_building(self, x, y, building_type):
        """
        Draws a building or road based on its type.
        """
        base_x = x * self.cell_size
        base_y = y * self.cell_size

        if building_type == "road":
            self.draw_road(x, y)

        if building_type == "house":
            # Adjusted house to avoid overlapping roads
            rect = pygame.Rect(
                base_x + self.cell_size // 4,
                base_y + self.cell_size // 2 + self.cell_size // 6,
                self.cell_size // 2,
                self.cell_size // 3,
            )
            pygame.draw.rect(self.screen, (150, 75, 0), rect)  # Brown base

            # Roof
            pygame.draw.polygon(
                self.screen,
                (200, 50, 50),  # Red roof
                [
                    (base_x + self.cell_size // 4, base_y + self.cell_size // 2 + self.cell_size // 6),
                    (base_x + self.cell_size // 2, base_y + self.cell_size // 2),
                    (base_x + 3 * self.cell_size // 4, base_y + self.cell_size // 2 + self.cell_size // 6),
                ],
            )

            # Door
            door = pygame.Rect(
                rect.left + self.cell_size // 4  + self.cell_size // 16,
                rect.bottom - self.cell_size // 4,
                self.cell_size // 6,
                self.cell_size // 4,
            )
            pygame.draw.rect(self.screen, (100, 50, 0), door)
            pygame.draw.circle(
                self.screen, (255, 255, 0), (door.left + 3, door.centery), 1
            )  # Door handle

            # Window
            window = pygame.Rect(
                rect.left + self.cell_size // 8 - self.cell_size // 16,
                rect.top + self.cell_size // 10,
                self.cell_size // 6,
                self.cell_size // 6,
            )
            pygame.draw.rect(self.screen, (50, 190, 255), window)
            pygame.draw.line(
                self.screen, (0, 0, 0), window.midtop, window.midbottom, 1
            )  # Vertical divider
            pygame.draw.line(
                self.screen, (0, 0, 0), window.midleft, window.midright, 1
            )  # Horizontal divider

        elif building_type == "block":
            # Adjusted block to avoid overlapping roads
            rect = pygame.Rect(
                base_x + self.cell_size // 8,
                base_y + self.cell_size // 3,
                3 * self.cell_size // 4,
                2 * self.cell_size // 3,
            )
            pygame.draw.rect(self.screen, (100, 100, 100), rect)  # Gray base

            # Windows grid
            for i in range(3):
                for j in range(4):
                    window = pygame.Rect(
                        rect.left + self.cell_size // 8 + j * self.cell_size // 6,
                        rect.top + self.cell_size // 8 + i * self.cell_size // 6,
                        self.cell_size // 10,
                        self.cell_size // 10,
                    )
                    pygame.draw.rect(
                        self.screen,
                        (255, 255, 0) if (i + j) % 2 == 0 else (50, 190, 255),
                        window,
                    )

        elif building_type == "robot_base":
            # Baza robotów – wyśrodkowany kwadrat
            base_x = x * self.cell_size
            base_y = y * self.cell_size
            pygame.draw.rect(
                self.screen,
                (0, 150, 0),  # Zielony kolor bazy
                pygame.Rect(base_x, base_y, self.cell_size, self.cell_size)
            )
            font = pygame.font.SysFont("Arial", self.cell_size // 4, bold=True)
            text = font.render("BASE", True, (255, 255, 255))
            self.screen.blit(
                text,
                (base_x + self.cell_size // 4, base_y + self.cell_size // 3),
            )

        elif building_type == "restaurant":
            # Restauracja (McDonald's)

            # Czerwona podstawa budynku zaczynająca się od dołu kratki
            rect = pygame.Rect(
                base_x + self.cell_size // 8,
                base_y + self.cell_size // 2,
                3 * self.cell_size // 4,
                self.cell_size // 2,
            )
            pygame.draw.rect(self.screen, (255, 0, 0), rect)  # Czerwona podstawa

            # Żółty dach
            roof = pygame.Rect(
                rect.left,
                rect.top - self.cell_size // 18,
                rect.width,
                self.cell_size // 18,
            )
            pygame.draw.rect(self.screen, (255, 255, 0), roof)  # Żółty dach

            # Duża żółta litera "M" na dachu
            font = pygame.font.SysFont("Arial", self.cell_size // 3, bold=True)
            text = font.render("M", True, (255, 255, 0))  # Żółta litera
            self.screen.blit(
                text,
                (
                    roof.centerx - text.get_width() // 2,
                    roof.centery - text.get_height() // 2,
                ),
            )

            # Niebieskie okna na froncie
            for i in range(2):  # Dwa okna
                window = pygame.Rect(
                    rect.left + i * rect.width // 2 + rect.width // 8,
                    rect.top + rect.height // 4,
                    rect.width // 4,
                    rect.height // 3,
                )
                pygame.draw.rect(self.screen, (150, 220, 255), window)  # Jasnoniebieskie szkło

            # Opcjonalne stoliki przed restauracją
            for i in range(3):  # Trzy stoliki
                table = pygame.Rect(
                    base_x + self.cell_size // 5 + i * self.cell_size // 4,
                    rect.bottom - self.cell_size // 6,
                    self.cell_size // 8,
                    self.cell_size // 12,
                )
                pygame.draw.ellipse(self.screen, (255, 255, 255), table)  # Biały stolik
                pygame.draw.line(
                    self.screen,
                    (150, 150, 150),
                    (table.centerx, table.bottom),
                    (table.centerx, table.bottom + self.cell_size // 16),
                    2,
                )  # Noga stolika


        elif building_type == "skyscraper":
            # Wieżowiec zaczynający się u podstawy kratki
            rect = pygame.Rect(
                base_x + self.cell_size // 3,  # Wyśrodkowana pozycja w poziomie
                base_y + self.cell_size // 2,                       # Zaczyna od podstawy kratki
                self.cell_size // 3,          # Węższy wieżowiec
                self.cell_size // 2,          # Niższy wieżowiec
            )
            pygame.draw.rect(self.screen, (50, 50, 150), rect)  # Niebieska podstawa

            # Siatka wycentrowanych okien na elewacji
            window_width = self.cell_size // 12
            window_height = self.cell_size // 12
            window_spacing_x = (rect.width - 3 * window_width) // 4
            window_spacing_y = (rect.height - 4 * window_height) // 5

            for i in range(4):  # 4 rzędy okien
                for j in range(3):  # 3 kolumny okien
                    window = pygame.Rect(
                        rect.left + window_spacing_x + j * (window_width + window_spacing_x),
                        rect.top + window_spacing_y + i * (window_height + window_spacing_y),
                        window_width,
                        window_height,
                    )
                    pygame.draw.rect(self.screen, (200, 200, 255), window)

            # Dekoracyjny dach na górze
            roof = pygame.Rect(
                rect.left + rect.width // 6,
                rect.top - self.cell_size // 16,
                rect.width * 2 // 3,
                self.cell_size // 16,
            )
            pygame.draw.rect(self.screen, (70, 70, 200), roof)  # Ciemniejszy dach

            # Antena na dachu
            pygame.draw.line(
                self.screen,
                (255, 255, 255),
                (roof.centerx, roof.top),
                (roof.centerx, roof.top - self.cell_size // 8),
                1,
            )
            pygame.draw.circle(
                self.screen,
                (255, 0, 0),
                (roof.centerx, roof.top - self.cell_size // 8),
                1,
            )  # Czerwona końcówka anteny


        elif building_type == "shop":
            # Sklep z detalami
            # Główna część sklepu (podstawa)
            rect = pygame.Rect(
                base_x + self.cell_size // 8,
                base_y + self.cell_size // 2,
                3 * self.cell_size // 4,
                self.cell_size // 2,
            )
            pygame.draw.rect(self.screen, (100, 200, 100), rect)  # Zielona podstawa
            
            # Drzwi wejściowe
            door = pygame.Rect(
                base_x + self.cell_size // 2 - self.cell_size // 8,
                base_y + 2 * self.cell_size // 2 - self.cell_size // 6,
                self.cell_size // 6,
                self.cell_size // 6,
            )
            pygame.draw.rect(self.screen, (80, 80, 80), door)  # Szare drzwi
            pygame.draw.line(
                self.screen,
                (200, 200, 200),
                (door.left, door.centery),
                (door.right, door.centery),
                2,
            )  # Ozdoba na drzwiach
            
            # Witryny po obu stronach drzwi
            for i in [-1, 1]:
                window = pygame.Rect(
                    base_x + self.cell_size // 2 + i * self.cell_size // 4 - self.cell_size // 8,
                    base_y + self.cell_size // 2 + self.cell_size // 4,
                    self.cell_size // 6,
                    self.cell_size // 5,
                )
                pygame.draw.rect(self.screen, (150, 220, 255), window)  # Błękitne witryny
            
            # Żółty szyld nad wejściem
            sign = pygame.Rect(
                base_x + self.cell_size // 4,
                base_y + self.cell_size // 8 + self.cell_size // 2,
                self.cell_size // 2,
                self.cell_size // 8,
            )
            pygame.draw.rect(self.screen, (255, 255, 0), sign)  # Żółty prostokąt
            pygame.draw.rect(
                self.screen,
                (0, 0, 0),
                sign.inflate(-4, -4),
                2,
            )  # Czarne obramowanie szyldu
            
            # Geometryczne logo na szyldzie
            logo_circle = pygame.Rect(
                sign.centerx - self.cell_size // 12,
                sign.centery - self.cell_size // 12,
                self.cell_size // 6,
                self.cell_size // 6,
            )
            pygame.draw.ellipse(self.screen, (200, 50, 50), logo_circle)  # Czerwone koło
            pygame.draw.rect(
                self.screen,
                (255, 255, 255),
                logo_circle.inflate(-self.cell_size // 12, -self.cell_size // 12),
            )  # Białe wypełnienie w środku

    def draw_grid(self):
        """
        Draw roads first, then buildings.
        """
        # Draw roads first
        for (x, y), building_type in self.buildings.items():
            if building_type == "road":
                self.draw_road(x, y)

        # Draw buildings on top of roads
        for (x, y), building_type in self.buildings.items():
            if building_type != "road":
                self.draw_building(x, y, building_type)

    def draw_robots(self, robots):
        """
        Draws robots on the map. If multiple robots are on the same tile, they are stacked.
        """
        # Group robots by their position
        robot_positions = {}
        for robot in robots:
            position = (robot.x, robot.y)
            if position not in robot_positions:
                robot_positions[position] = []
            robot_positions[position].append(robot)

        # Draw robots at each position
        for position, robots_at_position in robot_positions.items():
            center_x = int(position[0] * self.cell_size + self.cell_size // 2)
            center_y = int(position[1] * self.cell_size + self.cell_size // 2)

            # If there is more than one robot on this tile, draw them smaller
            if len(robots_at_position) > 1:
                num_robots = len(robots_at_position)
                spacing = self.cell_size // (2 * num_robots)  # Adjust spacing based on the number of robots
                for i, robot in enumerate(robots_at_position):
                    offset_x = (i - (num_robots - 1) / 2) * spacing
                    offset_y = (i - (num_robots - 1) / 2) * spacing

                    # Smaller robot body
                    body = pygame.Rect(
                        center_x - self.cell_size // 12 + offset_x,
                        center_y - self.cell_size // 12 + offset_y,
                        self.cell_size // 6,
                        self.cell_size // 6,
                    )
                    pygame.draw.rect(self.screen, (200, 200, 200), body, border_radius=3)  # Metallic body

                    # Smaller head
                    head = pygame.Rect(
                        body.centerx - self.cell_size // 20,
                        body.top - self.cell_size // 12,
                        self.cell_size // 10,
                        self.cell_size // 10,
                    )
                    pygame.draw.rect(self.screen, (180, 180, 180), head, border_radius=2)  # Metallic head

                    # Smaller eyes
                    eye_radius = self.cell_size // 24
                    pygame.draw.circle(self.screen, (0, 255, 0), (head.centerx - eye_radius, head.centery), eye_radius)
                    pygame.draw.circle(self.screen, (0, 255, 0), (head.centerx + eye_radius, head.centery), eye_radius)

                    # Antenna
                    pygame.draw.line(
                        self.screen,
                        (255, 0, 0),
                        (head.centerx, head.top),
                        (head.centerx, head.top - self.cell_size // 12),
                        1,
                    )
                    pygame.draw.circle(
                        self.screen,
                        (255, 0, 0),
                        (head.centerx, head.top - self.cell_size // 12),
                        self.cell_size // 24,
                    )

                    # Smaller wheels
                    wheel_radius = self.cell_size // 16
                    pygame.draw.circle(
                        self.screen,
                        (100, 100, 100),
                        (body.left + wheel_radius, body.bottom + wheel_radius),
                        wheel_radius,
                    )
                    pygame.draw.circle(
                        self.screen,
                        (100, 100, 100),
                        (body.right - wheel_radius, body.bottom + wheel_radius),
                        wheel_radius,
                    )
            else:
                # Draw a normal-sized robot
                robot = robots_at_position[0]
                # Body of the robot
                body = pygame.Rect(
                    center_x - self.cell_size // 6,
                    center_y - self.cell_size // 6,
                    self.cell_size // 3,
                    self.cell_size // 3,
                )
                pygame.draw.rect(self.screen, (200, 200, 200), body, border_radius=5)  # Metallic body

                # Head of the robot
                head = pygame.Rect(
                    center_x - self.cell_size // 10,
                    center_y - self.cell_size // 4,
                    self.cell_size // 5,
                    self.cell_size // 5,
                )
                pygame.draw.rect(self.screen, (180, 180, 180), head, border_radius=3)  # Metallic head

                # Eyes
                eye_radius = self.cell_size // 20
                pygame.draw.circle(self.screen, (0, 255, 0), (head.centerx - eye_radius, head.centery), eye_radius)  # Left eye
                pygame.draw.circle(self.screen, (0, 255, 0), (head.centerx + eye_radius, head.centery), eye_radius)  # Right eye

                # Antenna
                pygame.draw.line(
                    self.screen,
                    (255, 0, 0),  # Red antenna
                    (head.centerx, head.top),
                    (head.centerx, head.top - self.cell_size // 8),
                    2,
                )
                pygame.draw.circle(
                    self.screen,
                    (255, 0, 0),
                    (head.centerx, head.top - self.cell_size // 8),
                    self.cell_size // 20,
                )  # Antenna tip

                # Backpack (for food delivery)
                backpack = pygame.Rect(
                    center_x - self.cell_size // 8,
                    center_y + self.cell_size // 6,
                    self.cell_size // 4,
                    self.cell_size // 6,
                )
                pygame.draw.rect(self.screen, (50, 50, 150), backpack)  # Blue backpack

                # Arms
                arm_length = self.cell_size // 6
                pygame.draw.line(
                    self.screen,
                    (200, 200, 200),  # Metallic arms
                    (body.left, body.centery),
                    (body.left - arm_length, body.centery + arm_length // 2),
                    3,
                )
                pygame.draw.line(
                    self.screen,
                    (200, 200, 200),  # Metallic arms
                    (body.right, body.centery),
                    (body.right + arm_length, body.centery + arm_length // 2),
                    3,
                )

                # Wheels (below the body)
                wheel_radius = self.cell_size // 12
                pygame.draw.circle(
                    self.screen,
                    (100, 100, 100),
                    (body.left + wheel_radius, body.bottom + wheel_radius),
                    wheel_radius,
                )
                pygame.draw.circle(
                    self.screen,
                    (100, 100, 100),
                    (body.right - wheel_radius, body.bottom + wheel_radius),
                    wheel_radius,
                )

    def update(self, robots):
        """
        Updates the view with robots and buildings.
        """
        self.screen.fill((30, 30, 30))  # Background color
        self.draw_grid()
        self.draw_robots(robots)
        pygame.display.flip()
