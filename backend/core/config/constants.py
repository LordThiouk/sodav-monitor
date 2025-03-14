"""Constants used throughout the application."""

# Redis key prefixes
REDIS_DETECTION_PREFIX = "detection"
REDIS_STATION_PREFIX = "station"
REDIS_CACHE_PREFIX = "cache"
REDIS_LOCK_PREFIX = "lock"

# Cache durations (in seconds)
CACHE_SHORT = 60  # 1 minute
CACHE_MEDIUM = 300  # 5 minutes
CACHE_LONG = 3600  # 1 hour
CACHE_VERY_LONG = 86400  # 24 hours

# Audio processing
AUDIO_FORMATS = [".mp3", ".wav", ".flac", ".m4a", ".ogg"]
MAX_AUDIO_FILE_SIZE = 50 * 1024 * 1024  # 50MB
SUPPORTED_SAMPLE_RATES = [44100, 48000]
SUPPORTED_CHANNELS = [1, 2]

# API rate limits
RATE_LIMIT_DEFAULT = "100/minute"
RATE_LIMIT_AUTH = "20/minute"
RATE_LIMIT_UPLOAD = "10/minute"

# WebSocket events
WS_EVENT_DETECTION = "detection"
WS_EVENT_STATUS = "status"
WS_EVENT_ERROR = "error"
WS_EVENT_HEARTBEAT = "heartbeat"

# Database
DB_BATCH_SIZE = 1000
MAX_QUERY_LIMIT = 100
DEFAULT_PAGE_SIZE = 20

# File paths
UPLOAD_DIR = "uploads"
TEMP_DIR = "temp"
LOG_DIR = "logs"

# Date formats
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
TIMESTAMP_FORMAT = "%Y%m%d%H%M%S"
