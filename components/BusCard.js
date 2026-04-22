import { StyleSheet, View, Text, TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';
import { useFonts, Bungee_400Regular } from '@expo-google-fonts/bungee';

export default function BusCard({
  route = 'RTD',
  destination = 'Waiting for transit data',
  stop = 'No stop information available yet',
  minutes = '--',
  delay = null,
  color = '#808080',
  nextArrivals = [],
  routeId = null,
  stopId = null,
}) {
    const router = useRouter();
    const [fontsLoaded] = useFonts({ Bungee_400Regular });
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
            {delay ? (
              <View style={[styles.delayBadge, delay.includes('late') ? styles.delayBadgeLate : styles.delayBadgeEarly]}>
                <Text style={styles.delayBadgeText}>⚠ {delay}</Text>
              </View>
            ) : null}
          </View>
          <View style={styles.arrivalInfo}>
            <Text style={styles.minutes}>{minutes}</Text>
          </View>
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
        fontFamily: 'Bungee_400Regular',
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
      arrivalInfo: {
        alignItems: 'flex-end',
      },
      minutes: {
        color: 'white',
        fontSize: 16,
        fontWeight: '700',
      },
      delayBadge: {
        alignSelf: 'flex-start',
        paddingHorizontal: 8,
        paddingVertical: 3,
        borderRadius: 6,
        marginTop: 4,
      },
      delayBadgeLate: {
        backgroundColor: '#C0392B',
      },
      delayBadgeEarly: {
        backgroundColor: '#1E7E34',
      },
      delayBadgeText: {
        color: 'white',
        fontSize: 10,
        fontWeight: '700',
      },
    });
