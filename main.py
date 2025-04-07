import vlc
import time
import os
import signal
import sys
from gpiozero import Button

# Define GPIO buttons
buttons = {
    17: "001.mp4",
    27: "002.mp4",
    22: "003.mp4",
    23: "004.mp4",
    24: "005.mp4"
}

gpio_buttons = {pin: Button(pin) for pin in buttons}

# VLC Player Setup
instance = vlc.Instance("--no-video-title-show")
player = instance.media_player_new()

# Video Paths
video_path = "/home/digitalsign/7dpreshow/videos/"
loop_video_file = os.path.join(video_path, "000.mp4")
black_screen_file = os.path.join(video_path, "black.mp4")  # A 1-second black video to prevent signal loss

def play_video(video):
    """Load and play a video without interrupting HDMI signal"""
    media = instance.media_new(video)
    player.set_media(media)
    player.set_fullscreen(True)
    player.play()
    time.sleep(1)  # Allow VLC to start
    player.audio_set_volume(100)  # Set normal volume

def fade_out():
    """Gradually reduce volume for smooth fade-out"""
    current_vol = player.audio_get_volume()
    for vol in range(current_vol, -1, -5):
        player.audio_set_volume(vol)
        time.sleep(0.1)

def switch_video(video):
    """Switch video smoothly without volume spikes"""
    fade_out()  # Fade out the current video

    # Prepare new media
    media = instance.media_new(video)
    player.set_media(media)

    player.audio_set_volume(0)  # Set volume to 0 BEFORE starting playback
    time.sleep(0.1)             # Give VLC a moment to register volume

    player.play()

    time.sleep(0.5)  # Allow VLC to start playing

    # Fade in smoothly
    for vol in range(0, 101, 5):
        player.audio_set_volume(vol)
        time.sleep(0.1)

def loop_video(video):
    """Loop a video indefinitely until any button press, with reduced volume"""
    play_video(video)
    player.audio_set_volume(70)  # Set lower volume for loop video (adjust as needed)

    while True:
        # Restart video if it ends
        if player.get_state() in [vlc.State.Ended, vlc.State.Stopped]:
            player.set_media(instance.media_new(video))
            player.play()
            player.audio_set_volume(60)

        # Check for button press
        for pin, button in gpio_buttons.items():
            if button.is_pressed:
                switch_video(black_screen_file)  # Play a black screen momentarily
                return pin  # Return the pressed button's GPIO pin

        time.sleep(0.2)

# Handle CTRL+C to exit cleanly
def exit_handler(sig, frame):
    print("\nExiting...")
    player.stop()
    sys.exit(0)

signal.signal(signal.SIGINT, exit_handler)

while True:
    pressed_pin = loop_video(loop_video_file)  # Start looping 000.mp4 until button is pressed

    if pressed_pin in buttons:
        player.audio_set_volume(0)  # Ensure volume is 0 before switching videos
        switch_video(os.path.join(video_path, buttons[pressed_pin]))  # Play selected video

        # Monitor playback of selected video
        while player.get_state() not in [vlc.State.Ended, vlc.State.Stopped]:
            if any(button.is_pressed for button in gpio_buttons.values()):  # Interrupt if any button is pressed
                player.audio_set_volume(0)  # Lower volume before interrupt
                switch_video(black_screen_file)  # Play black screen momentarily
                break  # Exit playback early and return to looping 000.mp4
            time.sleep(0.2)

