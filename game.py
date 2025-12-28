#!/usr/bin/env python3
"""
LED Strip Game - Simpel reactiespel op een LED strip
"""

import time
import pygame
import board
import neopixel
import json


class LEDGame:
    def __init__(self, config_file="config.json"):
        """Initialiseer het spel met configuratie"""
        # Laad configuratie
        with open(config_file, 'r') as f:
            config = json.load(f)

        self.led_config = config['led']
        self.game_config = config['game']

        # GPIO pin mapping
        gpio_map = {
            12: board.D12,
            13: board.D13,
            18: board.D18,
            21: board.D21
        }

        gpio_pin = self.led_config.get('pin', 18)
        if gpio_pin not in gpio_map:
            print(f"❌ Ongeldige GPIO pin: {gpio_pin}")
            print(f"   Gebruik: 12, 13, 18 of 21")
            exit(1)

        # Setup LED strip
        try:
            self.strip = neopixel.NeoPixel(
                gpio_map[gpio_pin],
                self.led_config['count'],
                brightness=self.led_config['brightness'] / 255.0,
                auto_write=False,
                pixel_order=neopixel.GRB
            )
        except Exception as e:
            print(f"❌ Fout bij initialiseren LED strip: {e}")
            print(f"   Draai je het script met sudo?")
            exit(1)

        # Setup pygame en controller
        pygame.init()
        if pygame.joystick.get_count() == 0:
            print("⚠️  Geen controller gevonden! Sluit een controller aan.")
            exit(1)

        self.joystick = pygame.joystick.Joystick(0)
        self.joystick.init()
        print(f"🎮 Controller gevonden: {self.joystick.get_name()}")

        # Spel variabelen
        self.player_pos = self.led_config['count'] // 2
        self.obstacles = []  # List van obstakel dictionaries: {'pos': int, 'color': tuple, 'button': int}
        self.score = 0  # Start score
        self.running = True
        self.pressed_buttons = set()  # Welke knoppen zijn ingedrukt
        self.button_press_time = {}  # Wanneer elke knop werd ingedrukt
        self.button_duration = 1.0  # Hoe lang een knop "actief" blijft

        # Progressie variabelen
        self.obstacles_passed = 0  # Totaal aantal gepasseerde obstakels
        self.current_difficulty = 1  # Huidige moeilijkheidsgraad (geen cap!)
        self.spawn_interval = self.led_config['count'] // 2  # Start met 2 obstacles op strip (30 LEDs)
        self.next_spawn_at = self.led_config['count'] - 1  # Wanneer volgende obstakel spawnt
        self.color_history = []  # Welke kleuren zijn succesvol gedodged (voor score display)

        # Dynamic difficulty settings
        self.base_speed = 0.25  # Start snelheid iets sneller (was 0.3s)
        self.current_speed = self.base_speed  # Huidige snelheid (wordt langzaam sneller)

        # Kleur definitie met button mapping (SNES layout)
        self.colors = {
            'yellow': {'rgb': (255, 255, 0),   'button': self.game_config['buttons']['yellow']},  # Helder geel
            'red':    {'rgb': (255, 0, 0),     'button': self.game_config['buttons']['red']},
            'green':  {'rgb': (0, 150, 0),     'button': self.game_config['buttons']['green']},   # Donkerder groen
            'blue':   {'rgb': (0, 0, 255),     'button': self.game_config['buttons']['blue']}
        }

        # Cache speler kleur
        self.player_color = (
            self.game_config['player_color']['r'],
            self.game_config['player_color']['g'],
            self.game_config['player_color']['b']
        )


    def update_display(self):
        """Update de LED strip met huidige spelstatus"""
        # Clear alles
        self.strip.fill((0, 0, 0))

        # Teken alle obstakels met hun kleur
        for obs in self.obstacles:
            if 0 <= obs['pos'] < self.led_config['count']:
                self.strip[obs['pos']] = obs['color']

        # Teken speler - alleen zichtbaar als NIET aan het springen
        # Als er een knop ingedrukt is, is de speler "in de lucht" (onzichtbaar)
        if len(self.pressed_buttons) == 0:
            self.strip[self.player_pos] = self.player_color

        self.strip.show()

    def show_animation(self, color, duration=1.0, blink_count=3):
        """Toon een animatie op alle LEDs"""
        blink_duration = duration / (blink_count * 2)
        anim_color = (color['r'], color['g'], color['b'])

        for _ in range(blink_count):
            # Aan
            self.strip.fill(anim_color)
            self.strip.show()
            time.sleep(blink_duration)

            # Uit
            self.strip.fill((0, 0, 0))
            self.strip.show()
            time.sleep(blink_duration)

    def press_button(self, button):
        """Registreer knopdruk"""
        self.pressed_buttons.add(button)
        self.button_press_time[button] = time.time()

        # Print welke kleur knop werd gedrukt (voor feedback)
        color_name = None
        for name, data in self.colors.items():
            if data['button'] == button:
                color_name = name.upper()
                break
        if color_name:
            print(f"🎮 Button {button} → {color_name} knop gedrukt!")
        else:
            print(f"🎮 Button {button} gedrukt (onbekend)")

    def get_gradient_color(self, value, max_value):
        """Bereken gradient kleur van groen naar rood"""
        # value 0.0 = groen, 0.5 = geel, 1.0 = rood
        ratio = min(value / max_value, 1.0) if max_value > 0 else 0

        if ratio < 0.5:
            # Groen naar geel
            r = int(255 * (ratio * 2))
            g = 255
            b = 0
        else:
            # Geel naar rood
            r = 255
            g = int(255 * (1 - (ratio - 0.5) * 2))
            b = 0

        return (r, g, b)

    def show_score_bar(self):
        """Toon score als bar graph met gekleurde segmenten"""
        # Clear strip
        self.strip.fill((0, 0, 0))

        # Bereken hoeveel LEDs per punt (dynamisch schalen voor hoge scores)
        total_leds = self.led_config['count']

        if self.score <= total_leds:
            # 1 LED per punt tot we de strip vol hebben
            leds_to_light = self.score
            for i in range(leds_to_light):
                color = self.get_gradient_color(i, total_leds)
                self.strip[i] = color
        else:
            # Score > LED count: schaal zodat volle strip = huidige score
            # Elke LED representeert meerdere punten
            points_per_led = self.score / total_leds

            for i in range(total_leds):
                # Kleur gebaseerd op positie
                color = self.get_gradient_color(i, total_leds)
                self.strip[i] = color

        self.strip.show()

    def show_score_digits(self):
        """Toon score als cijfers met kleurcodering (10 LEDs per cijfer)"""
        # Clear strip
        self.strip.fill((0, 0, 0))

        # Paars voor 0 (speciaal patroon: aan-uit-aan-uit)
        color_zero = (200, 0, 200)  # Paars

        # Score naar cijfers (gewoon links naar rechts)
        digits = [int(d) for d in str(self.score)]  # 157 -> [1, 5, 7]

        total_leds = self.led_config['count']
        max_digits = total_leds // 10  # Max 6 cijfers op 60 LEDs
        num_digits = len(digits)

        # Kleuren array (zelfde volgorde als game: geel, rood, groen, blauw)
        colors_palette = [
            (255, 255, 0),  # Geel
            (255, 0, 0),    # Rood
            (0, 255, 0),    # Groen
            (0, 0, 255),    # Blauw
        ]

        # Teken elk cijfer (van links naar rechts)
        for pos, digit in enumerate(digits):
            if pos >= max_digits:
                break  # Te veel cijfers voor strip

            # Start positie voor dit cijfer
            start_led = pos * 10

            if digit == 0:
                # Speciaal patroon voor 0: aan-uit-aan-uit-aan-uit-aan-uit-aan-uit
                for i in range(10):
                    led_idx = start_led + i
                    if led_idx < total_leds:
                        if i % 2 == 0:  # Even posities = aan
                            self.strip[led_idx] = color_zero
                        # Oneven posities blijven uit (zwart)
            else:
                # Normaal cijfer: eerste N LEDs aan, rest uit
                # Kies kleur op basis van positie vanaf links
                color_bright = colors_palette[pos % 4]

                for i in range(10):
                    led_idx = start_led + i
                    if led_idx < total_leds:
                        if i < digit:
                            # LED aan
                            self.strip[led_idx] = color_bright
                        # Rest blijft uit (zwart)

        self.strip.show()

    def show_score(self):
        """Toon score als gekleurde cijfers op LED strip"""
        # Print exacte score in console
        print(f"\n{'='*40}")
        print(f"🏆 EINDSTAND: {self.score} punten!")
        print(f"{'='*40}\n")

        # Toon cijfer display
        self.show_score_digits()

        # Wacht minimaal 3 seconden
        print(f"Score wordt getoond voor 3 seconden...")
        time.sleep(3.0)

        # Leeg event buffer (negeer knoppen tijdens score display)
        pygame.event.clear()

        # Nu wacht op knopdruk om opnieuw te starten
        print(f"Druk op een kleurknop om opnieuw te starten...")
        waiting = True
        while waiting:
            pygame.event.pump()
            for event in pygame.event.get():
                if event.type == pygame.JOYBUTTONDOWN:
                    # Check of het een kleurknop is
                    for color_data in self.colors.values():
                        if event.button == color_data['button']:
                            waiting = False
                            break
            time.sleep(0.1)

    def get_available_colors(self):
        """Geef beschikbare kleuren op basis van score (progressief toevoegen)"""
        if self.score >= 18:
            return ['yellow', 'red', 'green', 'blue']  # Alle 4 kleuren
        elif self.score >= 12:
            return ['yellow', 'red', 'green']  # 3 kleuren
        elif self.score >= 6:
            return ['yellow', 'red']  # 2 kleuren
        else:
            return ['yellow']  # Alleen geel (begin)

    def update_difficulty(self):
        """Update moeilijkheidsgraad op basis van score"""
        # Snelle start progressie, daarna geleidelijk
        if self.score <= 2:
            new_difficulty = 1
        elif self.score <= 5:
            new_difficulty = 2
        elif self.score <= 9:
            new_difficulty = 3
        elif self.score <= 14:
            new_difficulty = 4
        elif self.score <= 20:
            new_difficulty = 5
        else:
            # Na score 20: elke 8 punten +1 level
            new_difficulty = 5 + ((self.score - 20) // 8)

        if new_difficulty > self.current_difficulty:
            old_difficulty = self.current_difficulty
            self.current_difficulty = new_difficulty

            # Update spawn interval (minimum 3 LEDs apart)
            self.spawn_interval = max(3, self.led_config['count'] // self.current_difficulty)

            # Update speed (wordt sneller: 0.3 → 0.05s minimum)
            # Elke level: -0.015s sneller
            self.current_speed = max(0.05, self.base_speed - (self.current_difficulty * 0.015))

            # Uitgebreide feedback
            print(f"⚡ Level {self.current_difficulty}!")
            print(f"   📏 Interval: {self.spawn_interval} LEDs")
            print(f"   ⏱️  Snelheid: {self.current_speed:.3f}s")

        # Check voor nieuwe kleuren
        available_colors = self.get_available_colors()
        if len(available_colors) == 2 and self.score == 6:
            print(f"🎨 Nieuwe kleur! Rood toegevoegd - gebruik B knop!")
        elif len(available_colors) == 3 and self.score == 12:
            print(f"🎨 Nieuwe kleur! Groen toegevoegd - gebruik A knop!")
        elif len(available_colors) == 4 and self.score == 18:
            print(f"🎨 Nieuwe kleur! Blauw toegevoegd - gebruik X knop!")

    def should_spawn_obstacle(self):
        """Check of we een nieuw obstakel moeten spawnen"""
        # Kijk of er al een obstakel is op de spawn positie (voorkomt overlap)
        spawn_pos = self.led_config['count'] - 1
        for obs in self.obstacles:
            if obs['pos'] == spawn_pos:
                return False
        return True

    def spawn_obstacle(self):
        """Spawn 1 nieuw obstakel met random kleur aan het begin van de strip"""
        if self.should_spawn_obstacle():
            import random

            # Kies random kleur uit beschikbare kleuren
            available_colors = self.get_available_colors()
            color_name = random.choice(available_colors)
            color_data = self.colors[color_name]

            # Maak obstakel object
            obstacle = {
                'pos': self.led_config['count'] - 1,
                'color': color_data['rgb'],
                'button': color_data['button'],
                'color_name': color_name
            }

            self.obstacles.append(obstacle)
            self.next_spawn_at = obstacle['pos'] - self.spawn_interval

    def game_over(self):
        """Game over animatie"""
        print(f"❌ Geraakt! Eindstand: {self.score}")

        # Eerst: rood knipperen (fail animatie)
        self.show_animation(self.game_config['fail_color'], 1.0, 3)

        # Dan: score tonen
        if self.score > 0:
            self.show_score()

        # Reset voor nieuwe game
        self.score = 0
        self.obstacles = []
        self.obstacles_passed = 0
        self.current_difficulty = 1
        self.spawn_interval = self.led_config['count'] // 2  # Start met 2 obstacles (30 LEDs)
        self.next_spawn_at = self.led_config['count'] - 1
        self.pressed_buttons = set()
        self.button_press_time = {}
        self.color_history = []  # Reset kleur geschiedenis
        self.current_speed = self.base_speed  # Reset snelheid

    def handle_input(self):
        """Verwerk controller input"""
        pygame.event.pump()

        for event in pygame.event.get():
            # Knop gedrukt - registreer kleurknop
            if event.type == pygame.JOYBUTTONDOWN:
                # Check of het een van de kleurknoppen is
                for color_data in self.colors.values():
                    if event.button == color_data['button']:
                        self.press_button(event.button)
                        break

    def update_obstacles(self):
        """Beweeg alle obstakels en check collision"""
        # Update button press status (laat oude presses verlopen)
        current_time = time.time()
        expired_buttons = []
        for button, press_time in self.button_press_time.items():
            if current_time - press_time > self.button_duration:
                expired_buttons.append(button)

        for button in expired_buttons:
            self.pressed_buttons.discard(button)
            del self.button_press_time[button]

        # Beweeg alle obstakels 1 positie naar links
        for obs in self.obstacles:
            obs['pos'] -= 1

        # Check of we nieuwe obstakel moeten spawnen (continue flow!)
        if len(self.obstacles) == 0 or self.obstacles[-1]['pos'] <= self.next_spawn_at:
            self.spawn_obstacle()

        # Check collision met alle obstakels
        for obs in self.obstacles[:]:  # Copy list to allow removal during iteration
            if obs['pos'] == self.player_pos:
                # Obstakel is PRECIES op speler!
                # Check of juiste knop is ingedrukt
                if obs['button'] in self.pressed_buttons:
                    # Juiste kleur! Safe! Sla kleur op voor score display
                    print(f"✅ {obs['color_name'].upper()} - Goed gedaan!")
                    self.color_history.append(obs['color'])
                else:
                    # Verkeerde knop of niet gedrukt - geraakt!
                    print(f"💥 Gemist! Moest {obs['color_name'].upper()} knop drukken!")
                    self.game_over()
                    return

        # Tel obstakels die voorbij zijn gegaan en verwijder ze
        before_count = len(self.obstacles)
        self.obstacles = [obs for obs in self.obstacles if obs['pos'] >= 0]
        obstacles_passed = before_count - len(self.obstacles)

        if obstacles_passed > 0:
            self.obstacles_passed += obstacles_passed
            self.score += 1
            print(f"✅ Score: {self.score}")
            self.update_difficulty()  # Check of moeilijkheidsgraad omhoog moet

    def run(self):
        """Start de game loop"""
        print("\n🎮 LED Strip Kleur Game gestart!")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("SNES Controller:")
        print("  🟡 Y knop (boven) = Gele obstakels")
        print("  🔴 B knop (rechts) = Rode obstakels")
        print("  🟢 A knop (onder) = Groene obstakels")
        print("  🔵 X knop (links) = Blauwe obstakels")
        print("\nDruk de juiste kleurknop voor elk obstakel!")
        print("Druk CTRL+C om te stoppen\n")

        try:
            last_update = time.time()

            while self.running:
                # Handel input af
                self.handle_input()

                # Update obstakels positie op interval (gebruik dynamic speed!)
                current_time = time.time()
                if current_time - last_update >= self.current_speed:
                    self.update_obstacles()
                    last_update = current_time

                # Update display
                self.update_display()

                # Kleine delay om CPU te sparen
                time.sleep(0.01)

        except KeyboardInterrupt:
            print(f"\n\n👋 Game gestopt. Eindstand: {self.score}")
        finally:
            self.strip.fill((0, 0, 0))
            self.strip.show()
            pygame.quit()


if __name__ == "__main__":
    game = LEDGame()
    game.run()
