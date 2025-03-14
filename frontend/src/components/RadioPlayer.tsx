import React, { useRef, useState, useEffect } from 'react';
import {
  Box,
  Button,
  HStack,
  Text,
  VStack,
  Icon,
  IconButton,
  Image,
  useColorModeValue,
  Slider,
  SliderTrack,
  SliderFilledTrack,
  SliderThumb,
  Tooltip,
  Badge,
} from '@chakra-ui/react';
import { FaPlay, FaPause, FaVolumeUp, FaVolumeMute } from 'react-icons/fa';
import type { RadioStation } from '../types';

interface RadioPlayerProps {
  station: RadioStation | null;
  onError?: (error: string) => void;
}

// Separate the station info display into its own component
const StationInfo: React.FC<{
  station: RadioStation;
}> = ({ station }) => (
  <VStack align="start" flex={1} spacing={1}>
    <Text fontWeight="bold" noOfLines={1}>
      {station.name}
    </Text>
    <HStack spacing={2}>
      {station.codec && (
        <Badge colorScheme="green" fontSize="xs">
          {station.codec.toUpperCase()}
        </Badge>
      )}
      {station.bitrate && (
        <Badge colorScheme="blue" fontSize="xs">
          {station.bitrate}kbps
        </Badge>
      )}
    </HStack>
  </VStack>
);

// Separate the volume control into its own component
const VolumeControl: React.FC<{
  volume: number;
  isMuted: boolean;
  onVolumeChange: (value: number) => void;
  onToggleMute: () => void;
}> = ({ volume, isMuted, onVolumeChange, onToggleMute }) => {
  const [showVolumeSlider, setShowVolumeSlider] = useState(false);
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  return (
    <Box position="relative" onMouseEnter={() => setShowVolumeSlider(true)} onMouseLeave={() => setShowVolumeSlider(false)}>
      <IconButton
        aria-label={isMuted ? 'Unmute' : 'Mute'}
        icon={<Icon as={isMuted || volume === 0 ? FaVolumeMute : FaVolumeUp} />}
        onClick={onToggleMute}
        colorScheme="green"
        variant="ghost"
      />

      {showVolumeSlider && (
        <Box
          position="absolute"
          bottom="100%"
          left="50%"
          transform="translateX(-50%)"
          mb={2}
          p={4}
          bg={bgColor}
          borderRadius="md"
          boxShadow="lg"
          border="1px"
          borderColor={borderColor}
          width="120px"
        >
          <Slider
            aria-label="Volume"
            defaultValue={volume}
            min={0}
            max={1}
            step={0.01}
            onChange={onVolumeChange}
            orientation="horizontal"
          >
            <SliderTrack>
              <SliderFilledTrack />
            </SliderTrack>
            <SliderThumb />
          </Slider>
        </Box>
      )}
    </Box>
  );
};

const RadioPlayer: React.FC<RadioPlayerProps> = ({ station, onError }) => {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [volume, setVolume] = useState(0.8);
  const [isMuted, setIsMuted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  useEffect(() => {
    if (station) {
      handlePlay();
    } else {
      handleStop();
    }
  }, [station]);

  const handlePlay = async () => {
    if (!station) return;

    try {
      setIsLoading(true);
      if (audioRef.current) {
        audioRef.current.src = station.stream_url;
        audioRef.current.volume = volume;
        await audioRef.current.play();
        setIsPlaying(true);
      }
    } catch (error) {
      onError?.(error instanceof Error ? error.message : 'Failed to play station');
      setIsPlaying(false);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStop = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setIsPlaying(false);
    }
  };

  const togglePlay = () => {
    if (isPlaying) {
      handleStop();
    } else {
      handlePlay();
    }
  };

  const handleVolumeChange = (value: number) => {
    setVolume(value);
    if (audioRef.current) {
      audioRef.current.volume = value;
    }
    if (value > 0) {
      setIsMuted(false);
    }
  };

  const toggleMute = () => {
    if (audioRef.current) {
      audioRef.current.muted = !isMuted;
      setIsMuted(!isMuted);
    }
  };

  if (!station) return null;

  return (
    <Box
      p={4}
      bg={bgColor}
      borderRadius="lg"
      border="1px"
      borderColor={borderColor}
      boxShadow="lg"
      width="100%"
    >
      <HStack spacing={4} align="center">
        <Image
          src={station.favicon || '/radio-placeholder.png'}
          alt={station.name}
          boxSize="50px"
          borderRadius="md"
          objectFit="cover"
          fallbackSrc="https://via.placeholder.com/50"
        />

        <StationInfo station={station} />

        <HStack spacing={2}>
          <IconButton
            aria-label={isPlaying ? 'Pause' : 'Play'}
            icon={<Icon as={isPlaying ? FaPause : FaPlay} />}
            onClick={togglePlay}
            isLoading={isLoading}
            colorScheme="green"
            variant="ghost"
          />

          <VolumeControl
            volume={volume}
            isMuted={isMuted}
            onVolumeChange={handleVolumeChange}
            onToggleMute={toggleMute}
          />
        </HStack>
      </HStack>

      <audio ref={audioRef} />
    </Box>
  );
};

export default RadioPlayer;
