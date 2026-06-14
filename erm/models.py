from dataclasses import dataclass
from typing import Optional


@dataclass
class Room:
    id: int
    name: str
    duration_seconds: int
    intro_video_path: Optional[str]
    ending_video_path: Optional[str]
    wins: int = 0
    losses: int = 0
    intro_video_path_fr: Optional[str] = None


@dataclass
class Objective:
    id: int
    room_id: int
    title: str
    order_index: int
    checkpoint_video_path: Optional[str]
    completed: bool = False
    code: Optional[str] = None
    description: Optional[str] = None


@dataclass
class Hint:
    id: int
    objective_id: int
    text: str
    order_index: int
    rating: int = 0
    video_path: Optional[str] = None


@dataclass
class Clue:
    id: int
    room_id: int
    label: str
    order_index: int
    checked: bool = False


@dataclass
class SessionState:
    room_id: int
    status: str
    remaining_seconds: int
    messages_sent: int = 0
    time_adjusted_seconds: int = 0
    updated_at: Optional[str] = None


@dataclass
class RoomAudioSettings:
    room_id: int
    alert_volume: int = 100
    alert_muted: bool = False
    alert_path: Optional[str] = None
    game_music_volume: int = 100
    game_music_muted: bool = False
    game_music_path: Optional[str] = None
    success_volume: int = 100
    success_muted: bool = False
    success_path: Optional[str] = None
    fail_volume: int = 100
    fail_muted: bool = False
    fail_path: Optional[str] = None
    video_volume: int = 100
    video_muted: bool = False
    master_volume: int = 100
    master_muted: bool = False
