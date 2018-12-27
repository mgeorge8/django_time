from mrp_system.models import Type, Field

def create_type(typeName, suffix, fields):
    partType = Type.objects.create(name=typeName, prefix=suffix)
    for name, field in fields.items():
        Field.objects.create(name=name, fields=field, typePart=partType)

f = {
    'Series': 'char1',
    'Output Configuration': 'char2',
    'Output Type': 'char3',
    'Number of Regulators': 'char4',
    'Voltage - Input (Max)': 'char5',
    'Voltage - Output (Min/Fixed)': 'char6',
    'Voltage - Output (Max)': 'char7',
    'Voltage Dropout': 'char8',
    'Current - Output': 'char9',
    'Current - Quiescent (lq)': 'char10',
    'Current - Supply (Max)': 'char11',
    'PSRR': 'char12',
    'Control Features': 'char13',
    'Protetion Features': 'char14',
    'Operating Temperature': 'char15',
    'Mounting Type': 'char16',
    'Package / Case': 'char17',
    }
