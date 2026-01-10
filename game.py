#!/usr/bin/env python3
"""
LED Runner - Simple reaction game on an LED strip
"""

import time
import random
import pygame
import board
import neopixel
import json


class LEDGame:
    # Game states
    STATE_PLAYING = 'playing'
    STATE_PAUSED = 'paused'
    STATE_GAME_OVER = 'game_over'

    def __init__(self, config_file="config.json"):
        """Initialize the game with configuration"""
        # Load configuration
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
            print(f"❌ Invalid GPIO pin: {gpio_pin}")
            print(f"   Use: 12, 13, 18 or 21")
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
            print(f"❌ Error initializing LED strip: {e}")
            print(f"   Are you running the script with sudo?")
            exit(1)

        # Setup pygame and controller
        pygame.init()
        if pygame.joystick.get_count() == 0:
            print("⚠️  No controller found! Connect a controller.")
            exit(1)

        self.joystick = pygame.joystick.Joystick(0)
        self.joystick.init()
        print(f"🎮 Controller found: {self.joystick.get_name()}")

        # Start button
        self.start_button = self.game_config['buttons'].get('start', 9)

        # Color definition with button mapping (SNES layout)
        self.colors = {
            'yellow': {'rgb': (255, 255, 0),   'button': self.game_config['buttons']['yellow']},
            'red':    {'rgb': (255, 0, 0),     'button': self.game_config['buttons']['red']},
            'green':  {'rgb': (0, 150, 0),     'button': self.game_config['buttons']['green']},
            'blue':   {'rgb': (0, 0, 255),     'button': self.game_config['buttons']['blue']}
        }

        # Cache player color
        self.player_color = (
            self.game_config['player_color']['r'],
            self.game_config['player_color']['g'],
            self.game_config['player_color']['b']
        )

        # Initialize game
        self.running = True
        self.reset_game()
        self.state = self.STATE_PLAYING  # Start immediately

    def reset_game(self):
        """Reset all game variables for a new game"""
        self.player_pos = self.led_config['count'] // 2
        self.obstacles = []
        self.score = 0
        self.pressed_buttons = set()
        self.button_press_time = {}
        self.button_duration = 1.0
        self.obstacles_passed = 0
        self.current_difficulty = 1
        self.spawn_interval = self.led_config['count'] // 2
        self.next_spawn_at = self.led_config['count'] - 1
        self.color_history = []
        self.base_speed = 0.25
        self.current_speed = self.base_speed
        self.last_update = time.time()

    def update_display(self):
        """Update the LED strip with current game state"""
        self.strip.fill((0, 0, 0))

        # Draw all obstacles
        for obs in self.obstacles:
            if 0 <= obs['pos'] < self.led_config['count']:
                self.strip[obs['pos']] = obs['color']

        # Draw player - only visible when NOT jumping
        if len(self.pressed_buttons) == 0:
            self.strip[self.player_pos] = self.player_color

        self.strip.show()

    def show_pause_display(self):
        """Show pause indicator - blinking game state"""
        t = time.time()

        if int(t * 2) % 2 == 0:
            self.strip.fill((0, 0, 0))
            for obs in self.obstacles:
                if 0 <= obs['pos'] < self.led_config['count']:
                    self.strip[obs['pos']] = obs['color']
            self.strip[self.player_pos] = self.player_color
        else:
            self.strip.fill((0, 0, 0))
            for obs in self.obstacles:
                if 0 <= obs['pos'] < self.led_config['count']:
                    r, g, b = obs['color']
                    self.strip[obs['pos']] = (r // 4, g // 4, b // 4)

        self.strip.show()

    def show_animation(self, color, duration=1.0, blink_count=3):
        """Show a blink animation on all LEDs"""
        blink_duration = duration / (blink_count * 2)
        anim_color = (color['r'], color['g'], color['b'])

        for _ in range(blink_count):
            self.strip.fill(anim_color)
            self.strip.show()
            time.sleep(blink_duration)

            self.strip.fill((0, 0, 0))
            self.strip.show()
            time.sleep(blink_duration)

    def show_score_digits(self):
        """Show score as digits with color coding (10 LEDs per digit)"""
        self.strip.fill((0, 0, 0))

        color_zero = (200, 0, 200)  # Purple for 0
        digits = [int(d) for d in str(self.score)]

        total_leds = self.led_config['count']
        max_digits = total_leds // 10

        colors_palette = [
            (255, 255, 0),  # Yellow
            (255, 0, 0),    # Red
            (0, 255, 0),    # Green
            (0, 0, 255),    # Blue
        ]

        for pos, digit in enumerate(digits):
            if pos >= max_digits:
                break

            start_led = pos * 10

            if digit == 0:
                for i in range(10):
                    led_idx = start_led + i
                    if led_idx < total_leds and i % 2 == 0:
                        self.strip[led_idx] = color_zero
            else:
                color_bright = colors_palette[pos % 4]
                for i in range(10):
                    led_idx = start_led + i
                    if led_idx < total_leds and i < digit:
                        self.strip[led_idx] = color_bright

        self.strip.show()

    def press_button(self, button):
        """Register button press"""
        self.pressed_buttons.add(button)
        self.button_press_time[button] = time.time()

        color_name = None
        for name, data in self.colors.items():
            if data['button'] == button:
                color_name = name.upper()
                break
        if color_name:
            print(f"🎮 {color_name} button pressed!")

    def get_available_colors(self):
        """Return available colors based on score"""
        if self.score >= 18:
            return ['yellow', 'red', 'green', 'blue']
        elif self.score >= 12:
            return ['yellow', 'red', 'green']
        elif self.score >= 6:
            return ['yellow', 'red']
        else:
            return ['yellow']

    def update_difficulty(self):
        """Update difficulty level based on score"""
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
            new_difficulty = 5 + ((self.score - 20) // 8)

        if new_difficulty > self.current_difficulty:
            self.current_difficulty = new_difficulty
            self.spawn_interval = max(3, self.led_config['count'] // self.current_difficulty)
            self.current_speed = max(0.05, self.base_speed - (self.current_difficulty * 0.015))

            print(f"⚡ Level {self.current_difficulty}!")
            print(f"   📏 Interval: {self.spawn_interval} LEDs")
            print(f"   ⏱️  Speed: {self.current_speed:.3f}s")

        available_colors = self.get_available_colors()
        if len(available_colors) == 2 and self.score == 6:
            print(f"🎨 New color! Red added - use B button!")
        elif len(available_colors) == 3 and self.score == 12:
            print(f"🎨 New color! Green added - use A button!")
        elif len(available_colors) == 4 and self.score == 18:
            print(f"🎨 New color! Blue added - use X button!")

    def spawn_obstacle(self):
        """Spawn a new obstacle"""
        spawn_pos = self.led_config['count'] - 1

        for obs in self.obstacles:
            if obs['pos'] == spawn_pos:
                return

        available_colors = self.get_available_colors()
        color_name = random.choice(available_colors)
        color_data = self.colors[color_name]

        obstacle = {
            'pos': spawn_pos,
            'color': color_data['rgb'],
            'button': color_data['button'],
            'color_name': color_name
        }

        self.obstacles.append(obstacle)
        self.next_spawn_at = obstacle['pos'] - self.spawn_interval

    def game_over(self):
        """Handle game over"""
        print(f"❌ Hit! Final score: {self.score}")

        self.show_animation(self.game_config['fail_color'], 1.0, 3)

        # Show score
        print(f"\n{'='*40}")
        print(f"🏆 FINAL SCORE: {self.score} points!")
        print(f"{'='*40}")
        print(f"\n⏸️  Press START for new game...")

        self.show_score_digits()
        self.state = self.STATE_GAME_OVER

    def handle_input(self):
        """Process controller input"""
        pygame.event.pump()

        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN:
                # Start button handling
                if event.button == self.start_button:
                    if self.state == self.STATE_PLAYING:
                        self.state = self.STATE_PAUSED
                        print("\n⏸️  PAUSED - Press START to resume")
                    elif self.state == self.STATE_PAUSED:
                        self.state = self.STATE_PLAYING
                        self.last_update = time.time()
                        print("\n▶️  RESUMED")
                    elif self.state == self.STATE_GAME_OVER:
                        self.reset_game()
                        self.state = self.STATE_PLAYING
                        print("\n🎮 New game started!")

                # Color button handling (only when playing)
                elif self.state == self.STATE_PLAYING:
                    for color_data in self.colors.values():
                        if event.button == color_data['button']:
                            self.press_button(event.button)
                            break

    def update_obstacles(self):
        """Move all obstacles and check collision"""
        # Expire old button presses
        current_time = time.time()
        expired_buttons = []
        for button, press_time in self.button_press_time.items():
            if current_time - press_time > self.button_duration:
                expired_buttons.append(button)

        for button in expired_buttons:
            self.pressed_buttons.discard(button)
            del self.button_press_time[button]

        # Move obstacles
        for obs in self.obstacles:
            obs['pos'] -= 1

        # Spawn new obstacle if needed
        if len(self.obstacles) == 0 or self.obstacles[-1]['pos'] <= self.next_spawn_at:
            self.spawn_obstacle()

        # Check collision
        for obs in self.obstacles[:]:
            if obs['pos'] == self.player_pos:
                if obs['button'] in self.pressed_buttons:
                    print(f"✅ {obs['color_name'].upper()} - Well done!")
                    self.color_history.append(obs['color'])
                else:
                    print(f"💥 Missed! Should have pressed {obs['color_name'].upper()} button!")
                    self.game_over()
                    return

        # Remove passed obstacles and update score
        before_count = len(self.obstacles)
        self.obstacles = [obs for obs in self.obstacles if obs['pos'] >= 0]
        obstacles_passed = before_count - len(self.obstacles)

        if obstacles_passed > 0:
            self.obstacles_passed += obstacles_passed
            self.score += 1
            print(f"✅ Score: {self.score}")
            self.update_difficulty()

    def run(self):
        """Main game loop"""
        print("\n🎮 LED Runner")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("Controls:")
        print("  START = Pause / Resume / New game")
        print("  🟡 Y = Yellow")
        print("  🔴 B = Red")
        print("  🟢 A = Green")
        print("  🔵 X = Blue")
        print("\nGame starting...")
        print("Press CTRL+C to quit\n")

        try:
            while self.running:
                self.handle_input()

                if self.state == self.STATE_PLAYING:
                    current_time = time.time()
                    if current_time - self.last_update >= self.current_speed:
                        self.update_obstacles()
                        self.last_update = current_time
                    self.update_display()

                elif self.state == self.STATE_PAUSED:
                    self.show_pause_display()

                elif self.state == self.STATE_GAME_OVER:
                    # Score stays displayed, just wait for input
                    pass

                time.sleep(0.01)

        except KeyboardInterrupt:
            print(f"\n\n👋 Game stopped. Final score: {self.score}")
        finally:
            self.strip.fill((0, 0, 0))
            self.strip.show()
            pygame.quit()


if __name__ == "__main__":
    game = LEDGame()
    game.run()
