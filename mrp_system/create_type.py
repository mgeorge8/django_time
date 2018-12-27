from mrp_system.models import Type, Field

def create_type(typeName, suffix, data):
    data = data.splitlines()
    fields = {}
    number = 1
    for d in data:
        fields[d] = "char"+str(number)
        number += 1
    partType = Type.objects.create(name=typeName, prefix=suffix)
    for name, field in fields.items():
        Field.objects.create(name=name, fields=field, typePart=partType)



