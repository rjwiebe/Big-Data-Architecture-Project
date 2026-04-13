import { StyleSheet, View, Text, TouchableOpacity } from 'react-native';
import {useRouter} from 'expo-router';

export default function BusCard({
  route = 'RTD',
  destination = 'Waiting for transit data',
  stop = 'No stop information available yet',
  minutes = '--',
  color = '#808080',
  nextArrivals = [],
  routeId = null,
  stopId = null,
}) {
    const router = useRouter();
    return (
      <TouchableOpacity onPress={() => router.push({
        pathname: '/route-detail',
        params: { route, destination, stop, minutes, color, nextArrivals: JSON.stringify(nextArrivals), routeId, stopId },
      })}>

        <View style={[styles.card, { backgroundColor: color }]}>
          <Text style={styles.routeName}>{route}</Text>
          <View style={styles.cardMid}>
            <Text style={styles.destination}>{destination}</Text>
            <Text style={styles.stop}>{stop}</Text>
          </View>
          <Text style={styles.minutes}>{minutes}</Text>
        </View>
      </TouchableOpacity>
      );
    }
    const styles = StyleSheet.create({
      card: {
        borderRadius: 30,
        padding: 30,
        marginBottom: 3,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
      },
      routeName: {
        color: 'white',
        fontSize: 28,
        fontWeight: '900',
        minWidth: 52,
      },
      cardMid: {
        flex: 1,
        gap: 4,
      },
      destination: {
        color: 'white',
        fontSize: 12,
        fontWeight: '500',
      },
      stop: {
        color: 'rgba(255,255,255,0.6)',
        fontSize: 10,
      },
      minutes: {
        color: 'white',
        fontSize: 16,
        fontWeight: '700',
      },
    });
