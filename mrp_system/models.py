from django.db import models
#from django.contrib.sites.models import Site

class Manufacturer(models.Model):
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.name

class Location(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Type(models.Model):
    name = models.CharField(max_length=100)
    prefix = models.CharField(max_length=5)
    #field = models.ForeignKey(Field, on_delete=models.CASCADE,
     #                         related_name="type", null=True)

    def __str__(self):
        return self.name


class Field(models.Model):
    FIELD_CHOICES = (
        ('char1', 'Character 1'),
        ('char2', 'Character 2'),
        ('char3', 'Character 3'),
        ('char4', 'Character 4'),
        ('char5', 'Character 5'),
        ('char6', 'Character 6'),
        ('char7', 'Character 7'),
        ('char8', 'Character 8'),
        ('char9', 'Character 9'),
        ('char10', 'Character 10'),
        ('char11', 'Character 11'),
        ('char12', 'Character 12'),
        ('char13', 'Character 13'),
        ('char14', 'Character 14'),
        ('char15', 'Character 15'),
        ('char16', 'Character 16'),
        ('char17', 'Character 17'),
        ('char18', 'Character 18'),
        ('char19', 'Character 19'),
        ('char20', 'Character 20'),
        ('integer1', 'Integer 1'),
        ('integer2', 'Integer 2'),
    )
    name = models.CharField(max_length=50)
    fields = models.CharField(max_length=50, choices=FIELD_CHOICES)
    mouser_name = models.CharField(max_length=100, blank=True)
    typePart = models.ForeignKey(Type, on_delete=models.CASCADE, related_name="field", null=True)

class Part(models.Model):
    partType = models.ForeignKey(Type, on_delete=models.CASCADE, related_name="part")
    partNumber = models.IntegerField(blank=True, null=True, editable=False)
    engimusingPartNumber = models.CharField(max_length=30, editable=False)
    description = models.CharField(max_length=300, blank=True)
    location = models.ManyToManyField(Location, through='LocationRelationship')
    manufacturer = models.ManyToManyField(Manufacturer,
                                          through='ManufacturerRelationship')
    char1 = models.CharField(max_length=100, blank=True)
    char2 = models.CharField(max_length=100, blank=True)
    char3 = models.CharField(max_length=100, blank=True)
    char4 = models.CharField(max_length=100, blank=True)
    char5 = models.CharField(max_length=100, blank=True)
    char6 = models.CharField(max_length=100, blank=True)
    char7 = models.CharField(max_length=100, blank=True)
    char8 = models.CharField(max_length=100, blank=True)
    char9 = models.CharField(max_length=100, blank=True)
    char10 = models.CharField(max_length=100, blank=True)
    char11 = models.CharField(max_length=100, blank=True)
    char12 = models.CharField(max_length=100, blank=True)
    char13 = models.CharField(max_length=100, blank=True)
    char14 = models.CharField(max_length=100, blank=True)
    char15 = models.CharField(max_length=100, blank=True)
    char16 = models.CharField(max_length=100, blank=True)
    char17 = models.CharField(max_length=100, blank=True)
    char18 = models.CharField(max_length=100, blank=True)
    char19 = models.CharField(max_length=100, blank=True)
    char20 = models.CharField(max_length=100, blank=True)
    integer1 = models.IntegerField(blank=True, null=True)
    integer2 = models.IntegerField(blank=True, null=True)
    datasheet = models.FileField(upload_to='documents/', blank=True)

    class Meta:
        unique_together = ('description', 'char1', 'char2',)


    def __str__(self):
        return str(self.description)

    def get_location(self):
        if self.location:
            #return self.location.all()
            #return '%s' % "-" % '%s' % " / ".join([location.name for location in self.location.all()])
            return [LocationRelationship.location.name for LocationRelationship
                                     in self.locationrelationship_set.order_by('id')]

    def get_stock(self):
        if self.location:
            #return '\n'.join([str(LocationRelationship.stock) for LocationRelationship
             #                            in self.locationrelationship_set.all()])
            return [LocationRelationship for LocationRelationship in
                    self.locationrelationship_set.order_by('id')]

    def get_manufacturers(self):
        if self.manufacturer:
            return [manufacturer.name for manufacturer in self.manufacturer.all()]

    def get_related(self):
        if self.manufacturer:
            return [str(ManufacturerRelationship.partNumber) for ManufacturerRelationship
                                      in self.manufacturerrelationship_set.all()] #.objects.get(part=self)])

    def save(self, *args, **kwargs):
        if not self.id:
            partType = self.partType
            self.engimusingPartNumber = increment_engi_partnumber(partType)
            self.partNumber = int(self.engimusingPartNumber[3:9])
            print(self.partNumber)
        super().save(*args, **kwargs)

def increment_engi_partnumber(partType):
    last_id = Part.objects.filter(partType=partType).order_by('partNumber').last()
    prefix = partType.prefix
    if not last_id:
        return prefix + '000001'
    partNumber = last_id.partNumber
    new_partNumber = partNumber + 1
    new_engi_partNumber = prefix + str(new_partNumber).zfill(6)
    return new_engi_partNumber

class ManufacturerRelationship(models.Model):
    part = models.ForeignKey(Part, on_delete=models.CASCADE)
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE)
    partNumber = models.CharField(max_length=40, blank=True, unique=True)

class LocationRelationship(models.Model):
    part = models.ForeignKey(Part, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    stock = models.IntegerField(blank=True, null=True)

class Product(models.Model):
    description = models.CharField(max_length=100, blank=True)
    url = models.CharField(max_length=500, blank=True)
    location = models.ManyToManyField(Location, through='ProductLocation')
    part = models.ManyToManyField(Part, through='PartAmount')
    component_product = models.ManyToManyField('self', symmetrical=False,
                                               through='ProductAmount',
                                               through_fields=('from_product', 'to_product'),)

    def __str__(self):
        return str(self.description)

class PartAmount(models.Model):
    part = models.ForeignKey(Part, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    amount = models.IntegerField(blank=True, null=True, default=1)

class ProductAmount(models.Model):
    from_product = models.ForeignKey(Product, related_name='from_product', on_delete=models.CASCADE)
    to_product = models.ForeignKey(Product, related_name='to_product', on_delete=models.CASCADE)
    amount = models.IntegerField(blank=True, null=True, default=1)

class ProductLocation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    stock = models.IntegerField(blank=True, null=True)

class ManufacturingOrder(models.Model):
    name = models.CharField(max_length=50, blank=True)
    product = models.ManyToManyField(Product, through='MOProduct')

    def __str__(self):
        return self.name
    
class MOProduct(models.Model):
    manufacturing_order = models.ForeignKey(ManufacturingOrder, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    amount = models.IntegerField(blank=True, null=True)
    
class DigiKeyAPI(models.Model):
    name = models.CharField(max_length=100)
    refresh_token = models.CharField(max_length=150)
    access_token = models.CharField(max_length=150)
    
