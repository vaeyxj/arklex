from enum import Enum

# Enum for the different types of streams that can be used.
class StreamType(str, Enum):
    # AUDIO is used to denote audio streams
    AUDIO = 'audio'
    # TEXT is used to denote text streams
    TEXT = 'text'

# Enum for event types used when streaming data.
class EventType(str, Enum):
    # LAST is used to denote the last event in the stream
    LAST = 'last'
    # CHUNK is used to denote a chunk of data in the stream
    CHUNK = 'chunk'
    # TEXT is used to denote a chunk of text-only data in the stream
    TEXT = 'text'
    # AUDIO is used to denote a chunk of audio
    AUDIO_CHUNK = 'audio'
    # ERROR is used to denote an error
    ERROR = 'error'