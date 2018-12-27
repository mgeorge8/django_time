from mrp_system.models import Type, Field

def create_type(typeName, suffix, fields):
    partType = Type.objects.create(name=typeName, prefix=suffix)
    for name, field in fields.items():
        Field.objects.create(name=name, fields=field, typePart=partType)

##f = {
##    'Series': 'char1',
##    'Type': 'char2',
##    'Unidirectional Channels': 'char3',
##    'Bidirectional Channels': 'char4',
##    'Voltage - Reverse Standoff (Typ)': 'char5',
##    'Voltage - Breakdown (Min)': 'char6',
##    'Voltage - Clamping (Max) @ Ipp': 'char7',
##    'Current - Peak Pulse (10/1000µs)': 'char8',
##    'Power - Peak Pulse': 'char9',
##    'Power Line Protection': 'char10',
##    'Applications': 'char11',
##    'Capacitance @ Frequency': 'char12',
##    'Operating Temperature': 'char13',
##    'Mounting Type': 'char14',
##    'Package / Case': 'char15'
##    }
##data = """Series
##Type
##Material - Core
##Inductance
##Tolerance
##Current Rating
##Current - Saturation
##Shielding
##DC Resistance (DCR)
##Q @ Freq
##Frequency - Self Resonant
##Ratings
##Operating Temperature
##Inductance Frequency - Test
##Features
##Mounting Type
##Package / Case"""
##data = data.splitlines()
##f = {}
##number = 1
##for d in data:
##    f[d] = "char"+str(number)
##    number += 1
