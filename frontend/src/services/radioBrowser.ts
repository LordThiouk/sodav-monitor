import { ExternalRadioStation, RadioStation as InternalRadioStation, RadioBrowserError, RadioBrowserException } from '../types';

const BASE_URL = 'https://de1.api.radio-browser.info/json';

// Helper function to map external station data to internal format
const mapExternalToInternalStation = (external: ExternalRadioStation): InternalRadioStation => ({
    id: parseInt(external.stationuuid),
    name: external.name,
    stream_url: external.url,
    url_resolved: external.url_resolved,
    country: external.country,
    language: external.language,
    is_active: external.lastcheckok,
    last_checked: external.lastchecktime,
    favicon: external.favicon || undefined,
    tags: external.tags ? external.tags.split(',').map(tag => tag.trim()) : [],
    codec: external.codec,
    bitrate: external.bitrate,
    homepage: external.homepage || undefined
});

// Helper function for API calls
const fetchFromApi = async <T>(endpoint: string, errorType: RadioBrowserError): Promise<T> => {
    try {
        const response = await fetch(`${BASE_URL}${endpoint}`);
        if (!response.ok) {
            throw new RadioBrowserException(errorType, {
                status: response.status,
                statusText: response.statusText
            });
        }
        return await response.json();
    } catch (error) {
        if (error instanceof RadioBrowserException) {
            throw error;
        }
        throw new RadioBrowserException('NETWORK_ERROR', error);
    }
};

export const searchStationsByName = async (name: string): Promise<InternalRadioStation[]> => {
    const stations = await fetchFromApi<ExternalRadioStation[]>(
        `/stations/byname/${encodeURIComponent(name)}`,
        'INVALID_RESPONSE'
    );
    return stations.map(mapExternalToInternalStation);
};

export const searchStationsByCountry = async (country: string): Promise<InternalRadioStation[]> => {
    const stations = await fetchFromApi<ExternalRadioStation[]>(
        `/stations/bycountry/${encodeURIComponent(country)}`,
        'INVALID_RESPONSE'
    );
    return stations.map(mapExternalToInternalStation);
};

export const searchStationsByLanguage = async (language: string): Promise<InternalRadioStation[]> => {
    const stations = await fetchFromApi<ExternalRadioStation[]>(
        `/stations/bylanguage/${encodeURIComponent(language)}`,
        'INVALID_RESPONSE'
    );
    return stations.map(mapExternalToInternalStation);
};

export const searchStationsByTag = async (tag: string): Promise<InternalRadioStation[]> => {
    const stations = await fetchFromApi<ExternalRadioStation[]>(
        `/stations/bytag/${encodeURIComponent(tag)}`,
        'INVALID_RESPONSE'
    );
    return stations.map(mapExternalToInternalStation);
};

export const getTopStations = async (limit: number = 100): Promise<InternalRadioStation[]> => {
    const stations = await fetchFromApi<ExternalRadioStation[]>(
        `/stations/topvote/${limit}`,
        'INVALID_RESPONSE'
    );
    return stations.map(mapExternalToInternalStation);
};

export const getStationsByClickTrend = async (limit: number = 100): Promise<InternalRadioStation[]> => {
    const stations = await fetchFromApi<ExternalRadioStation[]>(
        `/stations/topclick/${limit}`,
        'INVALID_RESPONSE'
    );
    return stations.map(mapExternalToInternalStation);
};

export const getRandomStations = async (limit: number = 100): Promise<InternalRadioStation[]> => {
    const params = new URLSearchParams({
        limit: limit.toString(),
        hidebroken: 'true',
    });
    
    const stations = await fetchFromApi<ExternalRadioStation[]>(
        `/stations/random?${params}`,
        'INVALID_RESPONSE'
    );
    return stations.map(mapExternalToInternalStation);
};

// Function to check if a station's stream is available
export const checkStationAvailability = async (station: InternalRadioStation): Promise<boolean> => {
    try {
        const response = await fetch(station.stream_url, { method: 'HEAD' });
        return response.ok;
    } catch (error) {
        throw new RadioBrowserException('STATION_UNAVAILABLE', error);
    }
};

// Test stations for development
export const getTestStations = async (): Promise<InternalRadioStation[]> => {
    return [
        {
            id: 1,
            name: "Sud FM",
            stream_url: "https://stream.zeno.fm/d970hwkm1f8uv",
            url_resolved: "https://stream.zeno.fm/d970hwkm1f8uv",
            country: "Senegal",
            language: "French/Wolof",
            is_active: true,
            last_checked: new Date().toISOString(),
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
}): Promise<InternalRadioStation[]> => {
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