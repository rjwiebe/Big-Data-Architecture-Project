import { StyleSheet, View, Text, ScrollView, TouchableOpacity } from 'react-native';
import { useState, useEffect } from 'react';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { fetchRouteDetails } from '@/lib/api';
import MapScreen from '@/components/MapView';


//page when clicking bus card, shows more details about the route and arrival times, walking time, and a scrollable list of past arrivals at that stop
export default function RouteDetail() {
  const router = useRouter();
  const { route, destination, stop, color, minutes, nextArrivals, routeId, stopId } = useLocalSearchParams();
  const arrivals = nextArrivals ? JSON.parse(nextArrivals) : [];
  const [stops, setStops] = useState([]);
  const [mapExpanded, setMapExpanded] = useState(false);

  useEffect(() => {
    async function loadStops() {
      if (!routeId) return;
      try {
        const data = await fetchRouteDetails(routeId);
        setStops(data.stops || []);
      } catch {
        setStops([]);
      }
    }
    loadStops();
  }, [routeId]);

  return (
   
      <View style={{ flex: 1 }}>
    <ScrollView style={[styles.container, { backgroundColor: color }]}>
      
      <Text style={styles.backBtn} onPress={() => router.back()}>←</Text>

      <View style={styles.header}>
        <Text style={styles.routeName}>{route}</Text>
        <Text style={styles.destination}>→ {destination}</Text>
        <Text style={styles.headerStop}>{stop}</Text>
      </View>

      <View style={styles.chipsRow}>
        {arrivals.length > 0 ? (
          arrivals.map((arrival, index) => (
            <View key={index} style={styles.chip}>
              {index === 0 && <Text style={styles.chipLabel}>Next</Text>}
              <Text style={styles.chipTime}>
                {arrival.minutes_until_arrival
                  ? `${arrival.minutes_until_arrival} min` : '--'}
              </Text>
            </View>
          ))
        ) : (
          <View style = {styles.chip}>
          <Text style={styles.chipLabel}>Next</Text>
          <Text style={styles.chipTime}>{minutes}</Text>
          </View>
        )}
      </View>

      {/* stop timeline, past stops, nearest stop, future stops  */}
      <View style={styles.timeline}>
         <View style={styles.timelineLine}/>
         {stops.map((s, index) => (
  <View key={index} style={styles.timelineItem}>
    <View style={[styles.stopDot, s.stop_name === stop && styles.stopDotActive]} />
    <Text style={[
      styles.stopName,
      s.stop_name === stop && styles.stopNameBold,
      s.stop_name !== stop && styles.stopNameDim,
    ]}>
      {s.stop_name}
    </Text>
  </View>
))}

      </View>
       </ScrollView>


  <View style={{ height: mapExpanded ? 400 : 150 }}>
  <MapScreen
  onAddressChange={() => {}}
  onLocationChange={() => {}}
/>
    {
      !mapExpanded && (<TouchableOpacity style = {styles.expandBtn}
      onPress = {() => setMapExpanded(true)}
    >
      <Text style = {styles.expandBtnText}>^ Expand</Text>
      </TouchableOpacity>
      )}
      {
        mapExpanded && (<TouchableOpacity style = {styles.collapseBtn}
          onPress = {() => setMapExpanded(false)}
        >
          <Text style = {styles.expandBtnText}>Close</Text>
          </TouchableOpacity>
          )}
      
  </View>
      </View>
     

  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  backBtn: {
    color: 'white',
    fontSize: 24,
    padding: 20,
    paddingTop: 60,
  },
  header: {
    padding: 20,
    alignItems: 'center',
  },
  routeName: {
    fontSize: 72,
    fontWeight: '900',
    color: 'white',
  },
  destination: {
    fontSize: 16,
    color: 'white',
    marginTop: 4,
  },
  headerStop: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.7)',
    marginTop: 4,
  },
  chipsRow: {
    flexDirection: 'row',
    gap: 8,
    padding: 16,
  },
  chip: {
    backgroundColor: 'rgba(255,255,255,0.2)',
    borderRadius: 10,
    padding: 10,
    alignItems: 'center',
    flex: 1,
  },
  chipLabel: {
    fontSize: 9,
    color: 'rgba(255,255,255,0.6)',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  chipTime: {
    fontSize: 14,
    fontWeight: '700',
    color: 'white',
    marginTop: 2,
  },
  timeline: {
    marginHorizontal: 20,
    marginTop: 16,
    position: 'relative',
    minHeight: 200,
  },
  timelineLine: {
    position: 'absolute',
    left: 8,
    top: 0,
    bottom: 0,
    width: 3,
    backgroundColor: 'rgba(0,0,0,0.3)',
    borderRadius: 2,
  },
  timelineItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 14,
    paddingLeft: 30,
    gap: 10,
  },
  stopDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: 'rgba(255,255,255,0.4)',
    position: 'absolute',
    left: 3,
  },
  stopDotActive: {
    backgroundColor: 'white',
    width: 14,
    height: 14,
    borderRadius: 7,
    left: 2,
  },
  stopName: {
    color: 'white',
    fontSize: 14,
    fontWeight: '500',
    flex: 1,
  },
  stopNameBold: {
    fontWeight: '700',
    fontSize: 15,
  },
  stopNameDim: {
    color: 'rgba(255,255,255,0.5)',
    fontSize: 14,
  },
  stopTime: {
    color: 'rgba(255,255,255,0.7)',
    fontSize: 12,
  },
  expandBtn: {
    position: 'absolute',
    top: 8,
    left: 8,
    backgroundColor: 'rgba(0,0,0,0.5)',
    borderRadius: 8,
    padding: 6,
  },
  collapseBtn: {
    position: 'absolute',
    top: 8,
    left: 8,
    backgroundColor: 'rgba(0,0,0,0.5)',
    borderRadius: 8,
    padding: 6,
  },
  expandBtnText: {
    color: 'white',
    fontSize: 12,
    fontWeight: '600',
  },
});