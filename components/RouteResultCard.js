import { StyleSheet, View, Text, TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';

function estimateWalkMinutes(meters) {
  if (!Number.isFinite(meters)) return '--';
  return `${Math.max(1, Math.round(meters / 80))} min walk`;
}

export default function RouteResultCard({ route }) {
  const router = useRouter();

  const {
    route_id,
    route_short_name,
    route_long_name,
    origin_distance_meters,
    boarding_stop_name,
    alighting_stop_name,
  } = route;

  function handlePress() {
    router.push({
      pathname: '/route-detail',
      params: {
        route: route_short_name || route_id,
        destination: route_long_name || '',
        stop: boarding_stop_name,
        minutes: estimateWalkMinutes(origin_distance_meters),
        color: '#F08C21',
        nextArrivals: JSON.stringify([]),
      },
    });
  }

  return (
    <TouchableOpacity onPress={handlePress} style={styles.card}>
      {/* Route badge */}
      <View style={styles.badge}>
        <Text style={styles.badgeText} numberOfLines={1} adjustsFontSizeToFit>
          {route_short_name || route_id}
        </Text>
      </View>

      {/* Middle: route name + stop info */}
      <View style={styles.middle}>
        <Text style={styles.routeName} numberOfLines={1}>
          {route_long_name || route_short_name || route_id}
        </Text>
        <View style={styles.stopRow}>
          <View style={styles.stopDotGreen} />
          <Text style={styles.stopText} numberOfLines={1}>
            Board at {boarding_stop_name}
          </Text>
        </View>
        <View style={styles.stopConnector} />
        <View style={styles.stopRow}>
          <View style={styles.stopDotRed} />
          <Text style={styles.stopText} numberOfLines={1}>
            Exit at {alighting_stop_name}
          </Text>
        </View>
      </View>

      {/* Walk time to boarding stop */}
      <Text style={styles.walkTime}>
        {estimateWalkMinutes(origin_distance_meters)}
      </Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 14,
    marginBottom: 10,
    gap: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 2,
  },
  badge: {
    backgroundColor: '#F08C21',
    borderRadius: 10,
    width: 52,
    height: 52,
    justifyContent: 'center',
    alignItems: 'center',
    flexShrink: 0,
  },
  badgeText: {
    color: 'white',
    fontSize: 18,
    fontWeight: '900',
    textAlign: 'center',
  },
  middle: {
    flex: 1,
    gap: 3,
  },
  routeName: {
    fontSize: 13,
    fontWeight: '700',
    color: '#1a1a1a',
    marginBottom: 4,
  },
  stopRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  stopConnector: {
    width: 2,
    height: 8,
    backgroundColor: '#ccc',
    marginLeft: 5,
    marginVertical: 1,
  },
  stopDotGreen: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#22c55e',
  },
  stopDotRed: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#ef4444',
  },
  stopText: {
    fontSize: 11,
    color: '#555',
    flex: 1,
  },
  walkTime: {
    fontSize: 12,
    fontWeight: '700',
    color: '#F08C21',
    textAlign: 'right',
    flexShrink: 0,
  },
});
