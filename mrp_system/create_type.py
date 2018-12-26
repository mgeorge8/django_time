from mrp_system.models import Type, Field

def create_type(typeName, suffix, fields):
    partType = Type.objects.create(name=typeName, prefix=suffix)
    for name, field in fields.items():
        Field.objects.create(name=name, fields=field, typePart=partType)

f = {
    'Series': 'char1',
    'Core Processor': 'char2',
    'Core Size': 'char3',
    'Speed': 'char4',
    'Connectivity': 'char5',
    'Peripherals': 'char6',
    'Number of I/O': 'char7',
    'Program Memory Size': 'char8',
    'Program Memory Type': 'char9',
    'EEPROM Size': 'char10',
    'RAM Size': 'char11',
    'Voltage - Supply (Vcc/Vdd)': 'char12',
    'Data Converters': 'char13',
    'Oscillator Type': 'char14',
    'Operating Temperature': 'char15',
    'Package / Case': 'char16',
    }
