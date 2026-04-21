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
  Keyboard,
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

// Module-level vars persist FROM/TO across tab navigation
let _persistedFrom = '';
let _persistedDest = '';
let _fromIsGps = true;

export default function Trips() {
  const [street, setStreet] = useState(null);
  const [city, setCity] = useState(null);
  const [coords, setCoords] = useState(null);
  const [fromText, setFromText] = useState(_persistedFrom);
  const [destText, setDestText] = useState(_persistedDest);
  const [results, setResults] = useState([]);
  const [searchState, setSearchState] = useState(STATE_IDLE);
  const [errorMsg, setErrorMsg] = useState('');

  const handleAddressChange = useCallback((s, c) => {
    setStreet(s);
    setCity(c);
    // Only auto-fill FROM if user hasn't manually typed something
    if (_fromIsGps && s) {
      setFromText(s);
      _persistedFrom = s;
    }
  }, []);

  const handleFromChange = useCallback((text) => {
    setFromText(text);
    _persistedFrom = text;
    _fromIsGps = false;
  }, []);

  const handleDestChange = useCallback((text) => {
    setDestText(text);
    _persistedDest = text;
  }, []);

  const handleSearch = useCallback(async () => {
    Keyboard.dismiss();

    if (!fromText.trim() && !coords) {
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
      // Resolve origin — use GPS coords when FROM is still the auto-filled GPS address
      let originCoords;
      if (_fromIsGps && coords) {
        originCoords = coords;
      } else {
        if (!fromText.trim()) {
          setErrorMsg('Please enter an origin address.');
          setSearchState(STATE_ERROR);
          return;
        }
        const geocodedFrom = await Location.geocodeAsync(fromText.trim());
        if (!geocodedFrom || geocodedFrom.length === 0) {
          setErrorMsg("Couldn't find that origin address. Try something more specific.");
          setSearchState(STATE_ERROR);
          return;
        }
        originCoords = geocodedFrom[0];
      }

      const geocodedDest = await Location.geocodeAsync(destText.trim());
      if (!geocodedDest || geocodedDest.length === 0) {
        setErrorMsg("Couldn't find that destination. Try something more specific.");
        setSearchState(STATE_ERROR);
        return;
      }

      const destCoords = geocodedDest[0];
      const routes = await fetchRouteSearch({
        origLat: originCoords.latitude,
        origLon: originCoords.longitude,
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
  }, [coords, fromText, destText]);

  return (
    <GestureHandlerRootView style={styles.root}>
      <KeyboardAvoidingView
        style={styles.root}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        {/* Map preview at top */}
        <View style={styles.mapContainer}>
          <MapScreen
            onAddressChange={handleAddressChange}
            onLocationChange={setCoords}
          />
          <View style={styles.headerOverlay}>
            <Header street={street} city={city} showBackButton={true}
  showSearch={false}  />
          </View>
        </View>

        {/* Search + results panel */}
        <View style={styles.panel}>
          {/* Origin row */}
          <View style={styles.inputRow}>
            <View style={[styles.locationDot, styles.dotOrigin]} />
            <View style={[styles.inputWrap, styles.inputWrapOrigin]}>
              <Text style={styles.inputLabel}>FROM</Text>
              <TextInput
                style={styles.fromInput}
                placeholder="My Location"
                placeholderTextColor="rgba(0,0,0,0.35)"
                value={fromText}
                onChangeText={handleFromChange}
                onSubmitEditing={handleSearch}
                returnKeyType="next"
                autoCorrect={false}
              />
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
                onChangeText={handleDestChange}
                onSubmitEditing={handleSearch}
                returnKeyType="search"
                autoCorrect={false}
              />
            </View>
          </View>

          <TouchableOpacity
            style={styles.searchBtn}
            onPress={handleSearch}
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
    height: 300,
  },
  headerOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
  },
  panel: {
    flex: 1,
    backgroundColor: '#F08C21',
    paddingHorizontal: 16,
    paddingTop: 16,
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  locationDot: {
    backgroundColor: '#FFFFFF',
    width: 14,
    height: 14,
    flexShrink: 0,
  },
  dotOrigin: {
    borderRadius:7,
  },
  dotDest: {
    borderRadius: 5,
  },
  routeConnector: {
    width: 2,
    height: 20,
    backgroundColor: '#FFFFFF',
    marginLeft: 6,
    marginVertical: 3,
  },
  inputWrap: {
    flex: 1,
    backgroundColor: '#FFFFFF',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  inputWrapOrigin: {
    borderWidth: 1.5,
    borderColor: '#F08C21',
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
  fromInput: {
    fontSize: 14,
    color: '#1a1a1a',
    padding: 0,
    margin: 0,
  },
  destInput: {
    fontSize: 14,
    color: '#1a1a1a',
    padding: 0,
    margin: 0,
  },
  searchBtn: {
    backgroundColor: '#6698CC',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 12,
    marginBottom: 16,
  },
  searchBtnDisabled: {
    backgroundColor: '#A7BFD8',
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
    color: 'black',
    textAlign: 'center',
  },
  hintText: {
    fontSize: 13,
    color: '#FFFFFF',
    textAlign: 'center',
    lineHeight: 20,
    paddingTop: 8,
  },
  errorText: {
    fontSize: 16,
    color: '#b91c1c',
    textAlign: 'center',
    paddingHorizontal: 16,
    fontWeight: '500',
  },
});
