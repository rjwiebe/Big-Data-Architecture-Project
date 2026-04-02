import {
  StyleSheet,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useState, useCallback } from 'react';
import * as Location from 'expo-location';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import MapScreen from '@/components/MapView';
import Header from '@/components/Header';
import RouteResultCard from '@/components/RouteResultCard';
import { fetchRouteSearch, hasConfiguredApi } from '@/lib/api';

const STATE_IDLE = 'idle';
const STATE_LOADING = 'loading';
const STATE_RESULTS = 'results';
const STATE_EMPTY = 'empty';
const STATE_ERROR = 'error';

export default function Trips() {
  const [street, setStreet] = useState(null);
  const [city, setCity] = useState(null);
  const [coords, setCoords] = useState(null);
  const [destText, setDestText] = useState('');
  const [results, setResults] = useState([]);
  const [searchState, setSearchState] = useState(STATE_IDLE);
  const [errorMsg, setErrorMsg] = useState('');

  const handleSearch = useCallback(async () => {
    if (!coords) {
      setErrorMsg('Still waiting for your location. Try again in a moment.');
      setSearchState(STATE_ERROR);
      return;
    }
    if (!destText.trim()) {
      setErrorMsg('Please enter a destination address.');
      setSearchState(STATE_ERROR);
      return;
    }
    if (!hasConfiguredApi()) {
      setErrorMsg('API not configured. Set EXPO_PUBLIC_API_BASE_URL first.');
      setSearchState(STATE_ERROR);
      return;
    }

    setSearchState(STATE_LOADING);
    setErrorMsg('');
    setResults([]);

    try {
      const geocoded = await Location.geocodeAsync(destText.trim());
      if (!geocoded || geocoded.length === 0) {
        setErrorMsg("Couldn't find that address. Try something more specific.");
        setSearchState(STATE_ERROR);
        return;
      }

      const destCoords = geocoded[0];
      const routes = await fetchRouteSearch({
        origLat: coords.latitude,
        origLon: coords.longitude,
        destLat: destCoords.latitude,
        destLon: destCoords.longitude,
        limit: 10,
      });

      if (routes.length === 0) {
        setSearchState(STATE_EMPTY);
      } else {
        setResults(routes);
        setSearchState(STATE_RESULTS);
      }
    } catch (_err) {
      setErrorMsg('Search failed. Check your connection and try again.');
      setSearchState(STATE_ERROR);
    }
  }, [coords, destText]);

  return (
    <GestureHandlerRootView style={styles.root}>
      <KeyboardAvoidingView
        style={styles.root}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        {/* Map preview at top */}
        <View style={styles.mapContainer}>
          <MapScreen
            onAddressChange={(s, c) => { setStreet(s); setCity(c); }}
            onLocationChange={setCoords}
          />
          <View style={styles.headerOverlay}>
            <Header street={street} city={city} />
          </View>
        </View>

        {/* Search + results panel */}
        <View style={styles.panel}>
          {/* Origin row */}
          <View style={styles.inputRow}>
            <View style={[styles.locationDot, styles.dotOrigin]} />
            <View style={styles.inputWrap}>
              <Text style={styles.inputLabel}>FROM</Text>
              <Text style={styles.inputValueStatic} numberOfLines={1}>
                {street || 'My Location'}
              </Text>
            </View>
          </View>

          <View style={styles.routeConnector} />

          {/* Destination row */}
          <View style={styles.inputRow}>
            <View style={[styles.locationDot, styles.dotDest]} />
            <View style={[styles.inputWrap, styles.inputWrapDest]}>
              <Text style={styles.inputLabel}>TO</Text>
              <TextInput
                style={styles.destInput}
                placeholder="Enter destination address..."
                placeholderTextColor="rgba(0,0,0,0.35)"
                value={destText}
                onChangeText={setDestText}
                onSubmitEditing={handleSearch}
                returnKeyType="search"
                autoCorrect={false}
              />
            </View>
          </View>

          <TouchableOpacity
            style={[styles.searchBtn, !destText.trim() && styles.searchBtnDisabled]}
            onPress={handleSearch}
            disabled={!destText.trim()}
          >
            <Text style={styles.searchBtnText}>Find Routes</Text>
          </TouchableOpacity>

          {/* Results area */}
          <ScrollView
            style={styles.results}
            contentContainerStyle={styles.resultsContent}
            keyboardShouldPersistTaps="handled"
          >
            {searchState === STATE_IDLE && (
              <Text style={styles.hintText}>
                Enter a destination above to find transit routes from your current location.
              </Text>
            )}
            {searchState === STATE_LOADING && (
              <View style={styles.centerMsg}>
                <ActivityIndicator size="large" color="#F08C21" />
                <Text style={styles.centerMsgText}>Finding routes...</Text>
              </View>
            )}
            {searchState === STATE_ERROR && (
              <View style={styles.centerMsg}>
                <Text style={styles.errorText}>{errorMsg}</Text>
              </View>
            )}
            {searchState === STATE_EMPTY && (
              <View style={styles.centerMsg}>
                <Text style={styles.centerMsgText}>
                  No direct routes found between those two locations.
                </Text>
                <Text style={styles.hintText}>
                  Try a nearby intersection or landmark instead.
                </Text>
              </View>
            )}
            {searchState === STATE_RESULTS &&
              results.map((route) => (
                <RouteResultCard key={route.route_id} route={route} />
              ))}
          </ScrollView>
        </View>
      </KeyboardAvoidingView>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  mapContainer: {
    height: 200,
    overflow: 'hidden',
  },
  headerOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
  },
  panel: {
    flex: 1,
    backgroundColor: '#f5f5f5',
    paddingHorizontal: 16,
    paddingTop: 16,
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  locationDot: {
    width: 14,
    height: 14,
    borderRadius: 7,
    flexShrink: 0,
  },
  dotOrigin: {
    backgroundColor: '#22c55e',
  },
  dotDest: {
    backgroundColor: '#ef4444',
  },
  routeConnector: {
    width: 2,
    height: 10,
    backgroundColor: '#ccc',
    marginLeft: 6,
    marginVertical: 3,
  },
  inputWrap: {
    flex: 1,
    backgroundColor: '#fff',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  inputWrapDest: {
    borderWidth: 1.5,
    borderColor: '#F08C21',
  },
  inputLabel: {
    fontSize: 9,
    fontWeight: '700',
    letterSpacing: 1.2,
    color: '#999',
    marginBottom: 2,
  },
  inputValueStatic: {
    fontSize: 14,
    color: '#1a1a1a',
    fontWeight: '500',
  },
  destInput: {
    fontSize: 14,
    color: '#1a1a1a',
    padding: 0,
    margin: 0,
  },
  searchBtn: {
    backgroundColor: '#F08C21',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 12,
    marginBottom: 16,
  },
  searchBtnDisabled: {
    backgroundColor: '#ccc',
  },
  searchBtnText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },
  results: {
    flex: 1,
  },
  resultsContent: {
    paddingBottom: 24,
  },
  centerMsg: {
    alignItems: 'center',
    paddingTop: 32,
    gap: 8,
  },
  centerMsgText: {
    fontSize: 15,
    color: '#555',
    textAlign: 'center',
  },
  hintText: {
    fontSize: 13,
    color: '#999',
    textAlign: 'center',
    lineHeight: 20,
    paddingTop: 8,
  },
  errorText: {
    fontSize: 14,
    color: '#b91c1c',
    textAlign: 'center',
    paddingHorizontal: 16,
  },
});
