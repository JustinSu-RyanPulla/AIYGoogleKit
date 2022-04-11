import logging
import re
import subprocess
import sys
import threading

import vlc
import youtube_dl

from aiy.assistant import auth_helpers
from aiy.assistant.library import Assistant
from aiy.board import Board, Led
from aiy.voice import tts
from google.assistant.library.event import EventType



class MusicPlayer:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    )

    ydl_opts = {
        'default_search': 'ytsearch1:',
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True
    }
    vlc_instance = vlc.get_default_instance()
    vlc_player = vlc_instance.media_player_new()


    def __init__(self):
        self.task = threading.Thread(target=self.run_task)
        self.can_start_conversation = False
        self.assistant = None
        self.board = Board()
        self.board.button.when_pressed = self.on_button_pressed

    def start(self):
            """
            Starts the assistant event loop and begins processing events.
            """
            self.task.start()

    def run_task(self):
        credentials = auth_helpers.get_assistant_credentials()
        with Assistant(credentials) as assistant:
            self.assistant = assistant
            for event in assistant.start():
                self.process_event(event)

    def power_off_pi():
        tts.say('Good bye!')
        subprocess.call('sudo shutdown now', shell=True)

    def reboot_pi():
        tts.say('See you in a bit!')
        subprocess.call('sudo reboot', shell=True)

    def say_ip():
        ip_address = subprocess.check_output("hostname -I | cut -d' ' -f1", shell=True)
        tts.say('My IP address is %s' % ip_address.decode('utf-8'))

    def play_music(name):
        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                meta = ydl.extract_info(name, download=False)
        except Exception:
            tts.say('Sorry, I can\'t find that song.')
            return

        if meta:
            info = meta['entries'][0]
            tts.say('Now playing ' + re.sub(r'[^\s\w]', '', info['title']))
            MusicPlayer().vlc_player.play()


    def process_event(assistant, event):

        logging.info(event)
        if event.type == EventType.ON_START_FINISHED:
            self.board.led.status = Led.BEACON_DARK  # Ready.
            self.can_start_conversation = True
            logging.info('Say "OK, Google" then speak, or press Ctrl+C to quit...')

        elif event.type == EventType.ON_CONVERSATION_TURN_STARTED:
            led.state = Led.ON  # Listening.
            self.can_start_conversation = False

        elif event.type == EventType.ON_RECOGNIZING_SPEECH_FINISHED and event.args:
            print('You said:', event.args['text'])
            text = event.args['text'].lower()
            if text == 'stop':
                if MusicPlayer().vlc_player.get_state() == vlc.State.Playing:
                    MusicPlayer().vlc_player.stop()

            elif text == 'power off':
                assistant.stop_conversation()
                MusicPlayer().power_off_pi()

            elif text == 'reboot':
                assistant.stop_conversation()
                MusicPlayer().reboot_pi()

            elif text == 'ip address':
                assistant.stop_conversation()
                MusicPlayer().say_ip()

            elif text == 'pause':
                assistant.stop_conversation()
                MusicPlayer().vlc_player.set_pause(True)

            elif text == 'resume':
                assistant.stop_conversation()
                MusicPlayer().vlc_player.set_pause(False)

            elif text.startswith('play '):
                assistant.stop_conversation()
                MusicPlayer().play_music(text[5:])

        elif event.type == EventType.ON_END_OF_UTTERANCE:
            self.board.led.state = Led.PULSE_QUICK  # Thinking.

        elif (event.type == EventType.ON_CONVERSATION_TURN_FINISHED
            or event.type == EventType.ON_CONVERSATION_TURN_TIMEOUT
            or event.type == EventType.ON_NO_RESPONSE):
            self.board.led.state = Led.BEACON_DARK  # Ready.

        elif event.type == EventType.ON_ASSISTANT_ERROR and event.args and event.args['is_fatal']:
            sys.exit(1)

    def on_button_pressed(self):
        # Check if we can start a conversation. 'self._can_start_conversation'
        # is False when either:
        # 1. The assistant library is not yet ready; OR
        # 2. The assistant library is already in a conversation.
        if self.can_start_conversation:
            self.assistant.start_conversation()

def main():
    logging.basicConfig(level=logging.INFO)
    MusicPlayer().start()


if __name__ == '__main__':
    main()
