from backend.api.systems import SystemsMixin
from backend.api.roms import RomsMixin
from backend.api.tags import TagsMixin
from backend.api.files import FilesMixin
from backend.api.collections import CollectionsMixin
from backend.api.retroachievements import RetroAchievementsMixin

class Api(SystemsMixin, RomsMixin, TagsMixin, FilesMixin, CollectionsMixin, RetroAchievementsMixin):
    def __init__(self, window=None):
        self.window = window
