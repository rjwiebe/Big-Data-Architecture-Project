import { StyleSheet, View } from 'react-native';
import MapScreen from '@/components/MapView';
import BusCard from '@/components/BusCard';
import Header from '@/components/Header';
import { useEffect, useRef, useState } from 'react';
import {GestureHandlerRootView} from 'react-native-gesture-handler';
import BottomSheet, {BottomSheetScrollView} from '@gorhom/bottom-sheet';
import {
  adaptStationToBusCard,
  fetchNearestStations,
  getFallbackBusCards,
  hasConfiguredApi,
} from '@/lib/api';
export default function Index() {
 const bottomSheetRef = useRef(null);
 const [street, setStreet] = useState(null);
 const [city, setCity] = useState(null);
 const [coords, setCoords] = useState(null);
 const [cards, setCards] = useState(
  hasConfiguredApi() ? getFallbackBusCards('loading') : getFallbackBusCards('unconfigured')
 );

 useEffect(() => {
  let isActive = true;

  async function loadNearbyStations() {
    if (!coords) {
      return;
    }

    if (!hasConfiguredApi()) {
      if (isActive) {
        setCards(getFallbackBusCards('unconfigured'));
      }
      return;
    }

    if (isActive) {
      setCards(getFallbackBusCards('loading'));
    }

    try {
      const stations = await fetchNearestStations({
        latitude: coords.latitude,
        longitude: coords.longitude,
        limit: 4,
      });

      if (!isActive) {
        return;
      }

      if (stations.length) {
        setCards(stations.map(adaptStationToBusCard));
      } else {
        setCards(getFallbackBusCards('empty'));
      }
    } catch (_error) {
      if (!isActive) {
        return;
      }

      setCards(getFallbackBusCards('error'));
    }
  }

  loadNearbyStations();

  return () => {
    isActive = false;
  };
 }, [coords]);

    return (    
    <GestureHandlerRootView style = {styles.container}>
     {/* map view  */} 
     <MapScreen
      onAddressChange={(s,c) => {setStreet(s); setCity(c);}}
      onLocationChange={(location) => setCoords(location)}
     />
     <View style={{position: 'absolute', top: 0, left: 0, right: 0}}>
      <Header street={street} city={city} />
      </View>
     {/* card view with no text for now */} 
   <BottomSheet
        ref={bottomSheetRef}
        index={0}
        snapPoints={['25%', '50%']}
      >
   <BottomSheetScrollView>
      {cards.map((card) => (
        <BusCard
          key={card.id}
          route={card.route}
          destination={card.destination}
          stop={card.stop}
          minutes={card.minutes}
          delay={card.delay}
          color={card.color}
        />
      ))}
      </BottomSheetScrollView>
       </BottomSheet>
     </GestureHandlerRootView>
      );
}
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: 'transparent',
  },
  
});
