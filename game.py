#!/usr/bin/env python3
"""
LED Runner - Simple reaction game on an LED strip
"""

import time
import pygame
import board
import neopixel
import json


class LEDGame:
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

        # Game variables
        self.player_pos = self.led_config['count'] // 2
        self.obstacles = []  # List of obstacle dictionaries: {'pos': int, 'color': tuple, 'button': int}
        self.score = 0  # Starting score
        self.running = True
        self.pressed_buttons = set()  # Which buttons are pressed
        self.button_press_time = {}  # When each button was pressed
        self.button_duration = 1.0  # How long a button stays "active"

        # Progression variables
        self.obstacles_passed = 0  # Total obstacles passed
        self.current_difficulty = 1  # Current difficulty level (no cap!)
        self.spawn_interval = self.led_config['count'] // 2  # Start with 2 obstacles on strip (30 LEDs)
        self.next_spawn_at = self.led_config['count'] - 1  # When next obstacle spawns
        self.color_history = []  # Which colors were successfully dodged (for score display)

        # Dynamic difficulty settings
        self.base_speed = 0.25  # Starting speed slightly faster (was 0.3s)
        self.current_speed = self.base_speed  # Current speed (gets faster gradually)

        # Color definition with button mapping (SNES layout)
        self.colors = {
            'yellow': {'rgb': (255, 255, 0),   'button': self.game_config['buttons']['yellow']},  # Bright yellow
            'red':    {'rgb': (255, 0, 0),     'button': self.game_config['buttons']['red']},
            'green':  {'rgb': (0, 150, 0),     'button': self.game_config['buttons']['green']},   # Darker green
            'blue':   {'rgb': (0, 0, 255),     'button': self.game_config['buttons']['blue']}
        }

        # Cache player color
        self.player_color = (
            self.game_config['player_color']['r'],
            self.game_config['player_color']['g'],
            self.game_config['player_color']['b']
        )


    def update_display(self):
        """Update the LED strip with current game state"""
        # Clear everything
        self.strip.fill((0, 0, 0))

        # Draw all obstacles with their color
        for obs in self.obstacles:
            if 0 <= obs['pos'] < self.led_config['count']:
                self.strip[obs['pos']] = obs['color']

        # Draw player - only visible when NOT jumping
        # If a button is pressed, the player is "in the air" (invisible)
        if len(self.pressed_buttons) == 0:
            self.strip[self.player_pos] = self.player_color

        self.strip.show()

    def show_animation(self, color, duration=1.0, blink_count=3):
        """Show an animation on all LEDs"""
        blink_duration = duration / (blink_count * 2)
        anim_color = (color['r'], color['g'], color['b'])

        for _ in range(blink_count):
            # On
            self.strip.fill(anim_color)
            self.strip.show()
            time.sleep(blink_duration)

            # Off
            self.strip.fill((0, 0, 0))
            self.strip.show()
            time.sleep(blink_duration)

    def press_button(self, button):
        """Register button press"""
        self.pressed_buttons.add(button)
        self.button_press_time[button] = time.time()

        # Print which color button was pressed (for feedback)
        color_name = None
        for name, data in self.colors.items():
            if data['button'] == button:
                color_name = name.upper()
                break
        if color_name:
            print(f"🎮 Button {button} → {color_name} button pressed!")
        else:
            print(f"🎮 Button {button} pressed (unknown)")

    def get_gradient_color(self, value, max_value):
        """Calculate gradient color from green to red"""
        # value 0.0 = green, 0.5 = yellow, 1.0 = red
        ratio = min(value / max_value, 1.0) if max_value > 0 else 0

        if ratio < 0.5:
            # Green to yellow
            r = int(255 * (ratio * 2))
            g = 255
            b = 0
        else:
            # Yellow to red
            r = 255
            g = int(255 * (1 - (ratio - 0.5) * 2))
            b = 0

        return (r, g, b)

    def show_score_bar(self):
        """Show score as bar graph with colored segments"""
        # Clear strip
        self.strip.fill((0, 0, 0))

        # Calculate how many LEDs per point (dynamic scaling for high scores)
        total_leds = self.led_config['count']

        if self.score <= total_leds:
            # 1 LED per point until we fill the strip
            leds_to_light = self.score
            for i in range(leds_to_light):
                color = self.get_gradient_color(i, total_leds)
                self.strip[i] = color
        else:
            # Score > LED count: scale so full strip = current score
            # Each LED represents multiple points
            points_per_led = self.score / total_leds

            for i in range(total_leds):
                # Color based on position
                color = self.get_gradient_color(i, total_leds)
                self.strip[i] = color

        self.strip.show()

    def show_score_digits(self):
        """Show score as digits with color coding (10 LEDs per digit)"""
        # Clear strip
        self.strip.fill((0, 0, 0))

        # Purple for 0 (special pattern: on-off-on-off)
        color_zero = (200, 0, 200)  # Purple

        # Score to digits (left to right)
        digits = [int(d) for d in str(self.score)]  # 157 -> [1, 5, 7]

        total_leds = self.led_config['count']
        max_digits = total_leds // 10  # Max 6 digits on 60 LEDs
        num_digits = len(digits)

        # Colors array (same order as game: yellow, red, green, blue)
        colors_palette = [
            (255, 255, 0),  # Yellow
            (255, 0, 0),    # Red
            (0, 255, 0),    # Green
            (0, 0, 255),    # Blue
        ]

        # Draw each digit (from left to right)
        for pos, digit in enumerate(digits):
            if pos >= max_digits:
                break  # Too many digits for strip

            # Start position for this digit
            start_led = pos * 10

            if digit == 0:
                # Special pattern for 0: on-off-on-off-on-off-on-off-on-off
                for i in range(10):
                    led_idx = start_led + i
                    if led_idx < total_leds:
                        if i % 2 == 0:  # Even positions = on
                            self.strip[led_idx] = color_zero
                        # Odd positions stay off (black)
            else:
                # Normal digit: first N LEDs on, rest off
                # Choose color based on position from left
                color_bright = colors_palette[pos % 4]

                for i in range(10):
                    led_idx = start_led + i
                    if led_idx < total_leds:
                        if i < digit:
                            # LED on
                            self.strip[led_idx] = color_bright
                        # Rest stays off (black)

        self.strip.show()

    def show_score(self):
        """Show score as colored digits on LED strip"""
        # Print exact score in console
        print(f"\n{'='*40}")
        print(f"🏆 FINAL SCORE: {self.score} points!")
        print(f"{'='*40}\n")

        # Show digit display
        self.show_score_digits()

        # Wait at least 3 seconds
        print(f"Score displayed for 3 seconds...")
        time.sleep(3.0)

        # Clear event buffer (ignore buttons during score display)
        pygame.event.clear()

        # Now wait for button press to restart
        print(f"Press a color button to restart...")
        waiting = True
        while waiting:
            pygame.event.pump()
            for event in pygame.event.get():
                if event.type == pygame.JOYBUTTONDOWN:
                    # Check if it's a color button
                    for color_data in self.colors.values():
                        if event.button == color_data['button']:
                            waiting = False
                            break
            time.sleep(0.1)

    def get_available_colors(self):
        """Return available colors based on score (progressively adding)"""
        if self.score >= 18:
            return ['yellow', 'red', 'green', 'blue']  # All 4 colors
        elif self.score >= 12:
            return ['yellow', 'red', 'green']  # 3 colors
        elif self.score >= 6:
            return ['yellow', 'red']  # 2 colors
        else:
            return ['yellow']  # Only yellow (start)

    def update_difficulty(self):
        """Update difficulty level based on score"""
        # Fast start progression, then gradual
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
            # After score 20: every 8 points +1 level
            new_difficulty = 5 + ((self.score - 20) // 8)

        if new_difficulty > self.current_difficulty:
            old_difficulty = self.current_difficulty
            self.current_difficulty = new_difficulty

            # Update spawn interval (minimum 3 LEDs apart)
            self.spawn_interval = max(3, self.led_config['count'] // self.current_difficulty)

            # Update speed (gets faster: 0.3 → 0.05s minimum)
            # Each level: -0.015s faster
            self.current_speed = max(0.05, self.base_speed - (self.current_difficulty * 0.015))

            # Extended feedback
            print(f"⚡ Level {self.current_difficulty}!")
            print(f"   📏 Interval: {self.spawn_interval} LEDs")
            print(f"   ⏱️  Speed: {self.current_speed:.3f}s")

        # Check for new colors
        available_colors = self.get_available_colors()
        if len(available_colors) == 2 and self.score == 6:
            print(f"🎨 New color! Red added - use B button!")
        elif len(available_colors) == 3 and self.score == 12:
            print(f"🎨 New color! Green added - use A button!")
        elif len(available_colors) == 4 and self.score == 18:
            print(f"🎨 New color! Blue added - use X button!")

    def should_spawn_obstacle(self):
        """Check if we should spawn a new obstacle"""
        # Check if there's already an obstacle at spawn position (prevents overlap)
        spawn_pos = self.led_config['count'] - 1
        for obs in self.obstacles:
            if obs['pos'] == spawn_pos:
                return False
        return True

    def spawn_obstacle(self):
        """Spawn 1 new obstacle with random color at the start of the strip"""
        if self.should_spawn_obstacle():
            import random

            # Choose random color from available colors
            available_colors = self.get_available_colors()
            color_name = random.choice(available_colors)
            color_data = self.colors[color_name]

            # Create obstacle object
            obstacle = {
                'pos': self.led_config['count'] - 1,
                'color': color_data['rgb'],
                'button': color_data['button'],
                'color_name': color_name
            }

            self.obstacles.append(obstacle)
            self.next_spawn_at = obstacle['pos'] - self.spawn_interval

    def game_over(self):
        """Game over animation"""
        print(f"❌ Hit! Final score: {self.score}")

        # First: red blinking (fail animation)
        self.show_animation(self.game_config['fail_color'], 1.0, 3)

        # Then: show score
        if self.score > 0:
            self.show_score()

        # Reset for new game
        self.score = 0
        self.obstacles = []
        self.obstacles_passed = 0
        self.current_difficulty = 1
        self.spawn_interval = self.led_config['count'] // 2  # Start with 2 obstacles (30 LEDs)
        self.next_spawn_at = self.led_config['count'] - 1
        self.pressed_buttons = set()
        self.button_press_time = {}
        self.color_history = []  # Reset color history
        self.current_speed = self.base_speed  # Reset speed

    def handle_input(self):
        """Process controller input"""
        pygame.event.pump()

        for event in pygame.event.get():
            # Button pressed - register color button
            if event.type == pygame.JOYBUTTONDOWN:
                # Check if it's one of the color buttons
                for color_data in self.colors.values():
                    if event.button == color_data['button']:
                        self.press_button(event.button)
                        break

    def update_obstacles(self):
        """Move all obstacles and check collision"""
        # Update button press status (expire old presses)
        current_time = time.time()
        expired_buttons = []
        for button, press_time in self.button_press_time.items():
            if current_time - press_time > self.button_duration:
                expired_buttons.append(button)

        for button in expired_buttons:
            self.pressed_buttons.discard(button)
            del self.button_press_time[button]

        # Move all obstacles 1 position to the left
        for obs in self.obstacles:
            obs['pos'] -= 1

        # Check if we need to spawn new obstacle (continuous flow!)
        if len(self.obstacles) == 0 or self.obstacles[-1]['pos'] <= self.next_spawn_at:
            self.spawn_obstacle()

        # Check collision with all obstacles
        for obs in self.obstacles[:]:  # Copy list to allow removal during iteration
            if obs['pos'] == self.player_pos:
                # Obstacle is EXACTLY on player!
                # Check if correct button is pressed
                if obs['button'] in self.pressed_buttons:
                    # Correct color! Safe! Save color for score display
                    print(f"✅ {obs['color_name'].upper()} - Well done!")
                    self.color_history.append(obs['color'])
                else:
                    # Wrong button or not pressed - hit!
                    print(f"💥 Missed! Should have pressed {obs['color_name'].upper()} button!")
                    self.game_over()
                    return

        # Count obstacles that passed and remove them
        before_count = len(self.obstacles)
        self.obstacles = [obs for obs in self.obstacles if obs['pos'] >= 0]
        obstacles_passed = before_count - len(self.obstacles)

        if obstacles_passed > 0:
            self.obstacles_passed += obstacles_passed
            self.score += 1
            print(f"✅ Score: {self.score}")
            self.update_difficulty()  # Check if difficulty should increase

    def run(self):
        """Start the game loop"""
        print("\n🎮 LED Runner started!")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("SNES Controller:")
        print("  🟡 Y button (top) = Yellow obstacles")
        print("  🔴 B button (right) = Red obstacles")
        print("  🟢 A button (bottom) = Green obstacles")
        print("  🔵 X button (left) = Blue obstacles")
        print("\nPress the correct color button for each obstacle!")
        print("Press CTRL+C to stop\n")

        try:
            last_update = time.time()

            while self.running:
                # Handle input
                self.handle_input()

                # Update obstacle positions on interval (use dynamic speed!)
                current_time = time.time()
                if current_time - last_update >= self.current_speed:
                    self.update_obstacles()
                    last_update = current_time

                # Update display
                self.update_display()

                # Small delay to save CPU
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
