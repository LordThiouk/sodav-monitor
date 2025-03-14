import { ExternalRadioStation, RadioStation, RadioBrowserError, RadioBrowserException } from '../types';

const BASE_URL = 'https://de1.api.radio-browser.info/json';

// Helper function to map external station data to internal format
const mapExternalToInternalStation = (external: ExternalRadioStation): RadioStation => ({
    id: parseInt(external.stationuuid),
    name: external.name,
    stream_url: external.url_resolved || external.url,
    country: external.country,
    language: external.language,
    is_active: external.lastcheckok,
    last_checked: external.lastchecktime,
    total_play_time: '00:00:00', // Default value since external API doesn't provide this
    favicon: external.favicon,
    codec: external.codec,
    bitrate: external.bitrate,
    homepage: external.homepage,
    tags: external.tags ? external.tags.split(',').map(tag => tag.trim()) : undefined
});

// Helper function for API calls
const fetchFromApi = async <T>(endpoint: string, errorType: string = 'API_ERROR'): Promise<T> => {
    try {
        const response = await fetch(`${BASE_URL}${endpoint}`);
        if (!response.ok) {
            throw new RadioBrowserException({
                code: errorType,
                message: `API request failed: ${response.status} ${response.statusText}`
            });
        }
        return await response.json();
    } catch (error) {
        if (error instanceof RadioBrowserException) {
            throw error;
        }
        throw new RadioBrowserException({
            code: 'NETWORK_ERROR',
            message: error instanceof Error ? error.message : 'Network request failed'
        });
    }
};

export const searchStationsByName = async (name: string): Promise<RadioStation[]> => {
    const stations = await fetchFromApi<ExternalRadioStation[]>(
        `/stations/byname/${encodeURIComponent(name)}`
    );
    return stations.map(mapExternalToInternalStation);
};

export const searchStationsByCountry = async (country: string): Promise<RadioStation[]> => {
    const stations = await fetchFromApi<ExternalRadioStation[]>(
        `/stations/bycountry/${encodeURIComponent(country)}`
    );
    return stations.map(mapExternalToInternalStation);
};

export const searchStationsByLanguage = async (language: string): Promise<RadioStation[]> => {
    const stations = await fetchFromApi<ExternalRadioStation[]>(
        `/stations/bylanguage/${encodeURIComponent(language)}`
    );
    return stations.map(mapExternalToInternalStation);
};

export const searchStationsByTag = async (tag: string): Promise<RadioStation[]> => {
    const stations = await fetchFromApi<ExternalRadioStation[]>(
        `/stations/bytag/${encodeURIComponent(tag)}`
    );
    return stations.map(mapExternalToInternalStation);
};

export const getTopStations = async (limit: number = 100): Promise<RadioStation[]> => {
    const stations = await fetchFromApi<ExternalRadioStation[]>(
        `/stations/topvote/${limit}`
    );
    return stations.map(mapExternalToInternalStation);
};

export const getStationsByClickTrend = async (limit: number = 100): Promise<RadioStation[]> => {
    const stations = await fetchFromApi<ExternalRadioStation[]>(
        `/stations/topclick/${limit}`
    );
    return stations.map(mapExternalToInternalStation);
};

export const getRandomStations = async (limit: number = 100): Promise<RadioStation[]> => {
    const params = new URLSearchParams({
        limit: limit.toString(),
        hidebroken: 'true',
    });

    const stations = await fetchFromApi<ExternalRadioStation[]>(
        `/stations/random?${params}`
    );
    return stations.map(mapExternalToInternalStation);
};

// Function to check if a station's stream is available
export const checkStationAvailability = async (station: RadioStation): Promise<boolean> => {
    try {
        const response = await fetch(station.stream_url, { method: 'HEAD' });
        return response.ok;
    } catch (error) {
        throw new RadioBrowserException({
            code: 'STATION_UNAVAILABLE',
            message: error instanceof Error ? error.message : 'Station is unavailable'
        });
    }
};

// Test stations for development
export const getTestStations = async (): Promise<RadioStation[]> => {
    return [
        {
            id: 1,
            name: "Sud FM",
            stream_url: "https://stream.zeno.fm/d970hwkm1f8uv",
            country: "Senegal",
            language: "French/Wolof",
            is_active: 1,
            last_checked: new Date().toISOString(),
            total_play_time: '00:00:00',
            favicon: "https://sudfm.sn/wp-content/uploads/2020/03/cropped-logo-sudfm-192x192.png",
            tags: ["senegal", "dakar", "news", "african"],
            codec: "MP3",
            bitrate: 128,
            homepage: "https://sudfm.sn"
        }
    ];
};

// Get all stations with optional filtering
export const getStations = async (filters?: {
    country?: string;
    language?: string;
    tag?: string;
}): Promise<RadioStation[]> => {
    try {
        if (filters?.country) {
            return await searchStationsByCountry(filters.country);
        } else if (filters?.language) {
            return await searchStationsByLanguage(filters.language);
        } else if (filters?.tag) {
            return await searchStationsByTag(filters.tag);
        }

        // Default to getting top stations if no filters are provided
        return await getTopStations(100);
    } catch (error) {
        console.error('Error fetching stations:', error);
        throw error;
    }
};

// Start music detection for a station
export const startDetection = async (stationId: number): Promise<{ track?: { title: string; artist: string } }> => {
    try {
        // This would typically make a call to your backend API
        // For now, we'll simulate a response
        await new Promise(resolve => setTimeout(resolve, 1000));

        return {
            track: {
                title: "Sample Track",
                artist: "Sample Artist"
            }
        };
    } catch (error) {
        console.error('Error starting detection:', error);
        throw error;
    }
};
