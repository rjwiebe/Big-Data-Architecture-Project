const DEFAULT_TIMEOUT_MS = 8000;

function trimTrailingSlash(value) {
  return value.replace(/\/+$/, '');
}

export function getApiBaseUrl() {
  const rawValue = process.env.EXPO_PUBLIC_API_BASE_URL;
  if (!rawValue) {
    return '';
  }

  return trimTrailingSlash(rawValue);
}

export function hasConfiguredApi() {
  return Boolean(getApiBaseUrl());
}

export function buildApiUrl(path, query = {}) {
  const baseUrl = getApiBaseUrl();
  if (!baseUrl) {
    const error = new Error('EXPO_PUBLIC_API_BASE_URL is not configured.');
    error.code = 'API_BASE_URL_NOT_CONFIGURED';
    throw error;
  }

  const url = new URL(`${baseUrl}${path}`);
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, String(value));
    }
  });

  return url.toString();
}

async function requestJson(path, query = {}, options = {}) {
  const controller = new AbortController();
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(buildApiUrl(path, query), {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      signal: controller.signal,
    });

    if (!response.ok) {
      let detail = `Request failed with status ${response.status}`;

      try {
        const errorPayload = await response.json();
        detail = errorPayload.detail || detail;
      } catch {
        // Keep the HTTP status fallback if the body is not JSON.
      }

      const error = new Error(detail);
      error.code = 'API_REQUEST_FAILED';
      error.status = response.status;
      throw error;
    }

    return await response.json();
  } catch (error) {
    if (error.name === 'AbortError') {
      const timeoutError = new Error('Request timed out.');
      timeoutError.code = 'API_TIMEOUT';
      throw timeoutError;
    }

    if (!error.code) {
      error.code = 'API_NETWORK_ERROR';
    }

    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function fetchNearestStations({ latitude, longitude, limit = 4 }) {
  return requestJson('/api/nearest-stations', {
    lat: latitude,
    lon: longitude,
    limit,
  });
}

export async function fetchNearestLines({ latitude, longitude, limit = 10 }) {
  return requestJson('/api/nearest-lines', {
    lat: latitude,
    lon: longitude,
    limit,
  });
}

export async function fetchRouteSearch({ origLat, origLon, destLat, destLon, limit = 10 }) {
  return requestJson('/api/route-search', {
    orig_lat: origLat,
    orig_lon: origLon,
    dest_lat: destLat,
    dest_lon: destLon,
    limit,
  });
}

function estimateWalkingMinutes(distanceMeters) {
  if (!Number.isFinite(distanceMeters)) {
    return '--';
  }

  return `${Math.max(1, Math.round(distanceMeters / 80))} min walk`;
}

export function adaptStationToBusCard(station) {
  const nextArrival = station?.next_arrivals?.[0];

  return {
    id: station.stop_id,
    route: nextArrival?.route_short_name || 'RTD',
    destination: nextArrival?.headsign || 'No realtime arrivals yet',
    stop: station.stop_name,
    minutes: nextArrival?.minutes_until_arrival
      ? `${nextArrival.minutes_until_arrival} min`
      : estimateWalkingMinutes(station.distance_meters),
    color: nextArrival ? '#F08C21' : '#808080',
    nextArrivals: station.next_arrivals || [],
  };
}

export function getFallbackBusCards(mode) {
  if (mode === 'loading') {
    return [
      {
        id: 'loading-card',
        route: '...',
        destination: 'Looking up nearby stops',
        stop: 'Using your current location',
        minutes: '...',
        color: '#9BA1A6',
      },
    ];
  }

  if (mode === 'unconfigured') {
    return [
      {
        id: 'config-card',
        route: 'API',
        destination: 'Backend not configured yet',
        stop: 'Set EXPO_PUBLIC_API_BASE_URL to your Cloud Run URL',
        minutes: '--',
        color: '#6B7280',
      },
    ];
  }

  if (mode === 'error') {
    return [
      {
        id: 'error-card',
        route: 'API',
        destination: 'Could not reach the backend',
        stop: 'The app will keep rendering while the API is offline',
        minutes: '--',
        color: '#A16207',
      },
    ];
  }

  return [
    {
      id: 'empty-card',
      route: 'RTD',
      destination: 'No nearby stops returned',
      stop: 'Try again once GTFS data is loaded',
      minutes: '--',
      color: '#6B7280',
    },
  ];
}
