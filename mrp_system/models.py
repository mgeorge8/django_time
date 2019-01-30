from django.db import models
import datetime
#from django.contrib.sites.models import Site

class Vendor(models.Model):
    TYPE_CHOICES = (
        ('manufacturer', 'manufacturer'),
        ('distributor', 'distrbutor'),
        )
    name = models.CharField(max_length=128)
    vendor_type = models.CharField(max_length=12, choices=TYPE_CHOICES,
                                   default='manufacturer')
    address = models.CharField(max_length=300, blank=True)
    phone = models.CharField(max_length=10, blank=True)
    web_address = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return self.name

class Location(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

#used to track different part types
class Type(models.Model):
    name = models.CharField(max_length=100, unique=True)
    prefix = models.CharField(max_length=4)

    def __str__(self):
        return self.name

#names of fields for each part type tracked with field model
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
        ('char21', 'Character 21'),
        ('char22', 'Character 22'),
        ('char23', 'Character 23'),
        ('char24', 'Character 24'),
        ('char25', 'Character 25'),
        ('char26', 'Character 26'),
        ('char27', 'Character 27'),
        ('char28', 'Character 28'),
        ('char29', 'Character 29'),
        ('char30', 'Character 30'),
        ('char31', 'Character 31'),
        ('char32', 'Character 32'),
        ('char33', 'Character 33'),
        ('char34', 'Character 34'),
        ('char35', 'Character 35'),
    )
    name = models.CharField(max_length=50)
    fields = models.CharField(max_length=50, choices=FIELD_CHOICES)
    typePart = models.ForeignKey(Type, on_delete=models.CASCADE, related_name="field", null=True)

class Part(models.Model):
    #used to keep track of part type and fields
    partType = models.ForeignKey(Type, on_delete=models.CASCADE, related_name="part")
    engimusingPartNumber = models.CharField(max_length=30, editable=False)
    description = models.CharField(max_length=300, blank=True)
    location = models.ManyToManyField(Location, through='LocationRelationship')
    manufacturer = models.ManyToManyField(Vendor,
                                          through='ManufacturerRelationship')
    #all of the fields that could be tracked for a part type
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
    char21 = models.CharField(max_length=100, blank=True)
    char22 = models.CharField(max_length=100, blank=True)
    char23 = models.CharField(max_length=100, blank=True)
    char24 = models.CharField(max_length=100, blank=True)
    char25 = models.CharField(max_length=100, blank=True)
    char26 = models.CharField(max_length=100, blank=True)
    char27 = models.CharField(max_length=100, blank=True)
    char28 = models.CharField(max_length=100, blank=True)
    char29 = models.CharField(max_length=100, blank=True)
    char30 = models.CharField(max_length=100, blank=True)
    char31 = models.CharField(max_length=100, blank=True)
    char32 = models.CharField(max_length=100, blank=True)
    char33 = models.CharField(max_length=100, blank=True)
    char34 = models.CharField(max_length=100, blank=True)
    char35 = models.CharField(max_length=100, blank=True)
    datasheet = models.FileField(upload_to='documents/', blank=True)

    def __str__(self):
        return '%s - %s' % (self.engimusingPartNumber, self.description)

    #can call these 4 functions from template to get related fields
    def get_location(self):
        if self.location:
            return [LocationRelationship.location.name for LocationRelationship
                                     in self.locationrelationship_set.order_by('id')]

    def get_stock(self):
        if self.location:
            return [LocationRelationship for LocationRelationship in
                    self.locationrelationship_set.order_by('id')]

    def get_manufacturers(self):
        if self.manufacturer:
            return [manufacturer.name for manufacturer in self.manufacturer.all()]

    def get_related(self):
        if self.manufacturer:
            return [str(ManufacturerRelationship.partNumber) for ManufacturerRelationship
                                      in self.manufacturerrelationship_set.all()] #.objects.get(part=self)])

    #auto assign engimusingPartNumber with prefix and auto incremented number
    def save(self, *args, **kwargs):
        if not self.id:
            partType = self.partType
            self.engimusingPartNumber = increment_engi_partnumber(partType)
        super().save(*args, **kwargs)

def increment_engi_partnumber(partType):
    #get greatest part number
    last_id = Part.objects.filter(partType=partType).order_by('engimusingPartNumber').last()
    prefix = partType.prefix
    #if no parts yet
    if not last_id:
        return prefix + '000001'
    length = len(prefix)
    partNumber = int(last_id.engimusingPartNumber[length:10])
    new_partNumber = partNumber + 1
    new_engi_partNumber = prefix + str(new_partNumber).zfill(6)
    return new_engi_partNumber

class ManufacturerRelationship(models.Model):
    part = models.ForeignKey(Part, on_delete=models.CASCADE)
    manufacturer = models.ForeignKey(Vendor, on_delete=models.CASCADE,
                                     limit_choices_to={'vendor_type': 'manufacturer'},)
    partNumber = models.CharField(max_length=40, blank=True)

class LocationRelationship(models.Model):
    part = models.ForeignKey(Part, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    stock = models.IntegerField(blank=True, null=True)

class Product(models.Model):
    engimusing_product_number = models.CharField(max_length=50, blank=True)
    description = models.CharField(max_length=100, blank=True)
    url = models.CharField(max_length=500, blank=True)
    location = models.ManyToManyField(Location, through='ProductLocation')
    part = models.ManyToManyField(Part, through='PartAmount')
    #sub products, must not be symmetrical for relationship to be onesided
    component_product = models.ManyToManyField('self', symmetrical=False,
                                               through='ProductAmount',
                                               through_fields=('from_product', 'to_product'),)

    def __str__(self):
        return str(self.description)

    def get_stock(self):
        if self.location:
            return [ProductLocation for ProductLocation in
                    self.productlocation_set.order_by('id')]

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
    product = models.ManyToManyField(Product, through='MOProduct')
    number = models.CharField(max_length=50)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.number
    
class MOProduct(models.Model):
    manufacturing_order = models.ForeignKey(ManufacturingOrder, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    amount = models.IntegerField(blank=True, null=True)

class PurchaseOrder(models.Model):
    number = models.CharField(max_length=20, editable=False)
    
    def save(self, *args, **kwargs):
        if not self.id:
            last_id = PurchaseOrder.objects.order_by('number').last()
            today = str(datetime.datetime.now().date())
            new_number = "PO" + today
            if last_id:
                str_number = str(last_id.number)
                last_date = str_number[2:12]
                if last_date == today:
                    nn = int(str_number[13:16]) + 1
                else:
                    nn = 1
            else:
                nn = 1
            new_number += "_" + str(nn).zfill(2)
            self.number = new_number
        super().save(*args, **kwargs)

"""used to keep track of tokens, only one instance of this model named "DigiKey",
don't create another instance of this as it can mess up the tokens"""
class DigiKeyAPI(models.Model):
    name = models.CharField(max_length=100)
    refresh_token = models.CharField(max_length=150)
    access_token = models.CharField(max_length=150)
    
