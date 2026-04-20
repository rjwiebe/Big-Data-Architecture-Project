import { StyleSheet, View, Text, TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';

export default function Header({
  street,
  city,
  showSearch = true,
  showBackButton = false
}) {
  const router = useRouter();

  return (
    <View style={styles.header}>

      {showBackButton && (
        <TouchableOpacity
          style={styles.closeBtn}
          onPress={() => router.back()}
        >
          <Text style={styles.closeText}>←</Text>
        </TouchableOpacity>
      )}

      <View
        style={[
          styles.location,
          showBackButton && styles.locationShifted
        ]}
      >
        <Text style={styles.street}>Near {street || ''}</Text>
        <Text style={styles.city}>{city || ''}</Text>
      </View>

      {showSearch && (
        <TouchableOpacity
          style={styles.searchBar}
          onPress={() => router.push('/trips')}
        >
          <Text style={styles.searchText}>Where to?</Text>
          <Text style={styles.searchArrow}>→</Text>
        </TouchableOpacity>
      )}

    </View>
  );
}

const styles = StyleSheet.create({
    header: {
        paddingBottom: 30,
        paddingLeft: 20,
        paddingTop: 70,
        borderBottomLeftRadius: 30,
        borderBottomRightRadius: 30,
        backgroundColor: '#F08C21',
        borderBottomWidth: 1,
        flexDirection: 'column',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
    },
    location: {
      backgroundColor: '#ED9D46',
      borderRadius: 10,
      paddingTop: 10,
      paddingBottom: 10,
      paddingLeft: 15,
      paddingRight: 15,
        flexDirection: 'column',
          marginBottom: 30,
          
    },
    street: {
        fontSize: 16,
        fontWeight: 'bold',
        color: 'white',
    },
    city:{
        fontSize: 12,
        color: 'white',
    },
    searchBar: {
        backgroundColor: '#F2D88F',
        borderRadius: 10,
        padding: 10,
        width: '40%',
        
      },
      searchText: {
        color: 'white',
        fontSize: 15,
        fontWeight: 'bold',
      },
      searchArrow: {
        color: 'white',
        fontSize: 15,
        fontWeight: 'bold',
        position: 'absolute',
        right: 10,
        top: 10,
      },
      locationShifted: {
        marginLeft: 50,
      },
      closeBtn: {
        position: 'absolute',
        left: 15,
        top: 70,
        backgroundColor: '#6698CC',
        width: 40,
        height: 40,
        borderRadius: 30,
        alignItems: 'center',
      },
      closeText: {
        color: 'white',
        fontSize: 33,
        fontWeight: 'bold',
      },
  
});
